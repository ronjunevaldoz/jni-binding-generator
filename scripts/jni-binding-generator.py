#!/usr/bin/env python3
"""
JNI Binding Generator

Generates C++ JNI boilerplate from Kotlin ``external fun`` declarations.

The generator reads Kotlin source files, extracts the enclosing package /
class / object and every ``external fun`` signature, then emits, for each
source file, a ``<Class>_jni.gen.cpp`` containing fully-formed JNI entry
points with:

  * argument marshalling (jstring -> std::string, arrays -> std::vector, ...)
  * null / empty error checks for handles and strings
  * a clearly marked TODO body for the hand-written native logic

Generated marshalling relies on the small helper header ``jni-utils.h`` that
ships alongside this script (jstring2string, extract_*_array, throw_* ...).

Usage:
    python3 jni-binding-generator.py --kotlin-source <path> --output <path>
    python3 jni-binding-generator.py --kotlin-source <path> --output <path> --dry-run

``--kotlin-source`` may point at a single ``.kt`` file or a directory (it is
scanned recursively for ``.kt`` files).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Type mapping
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class TypeInfo:
    """How a Kotlin type maps onto the JNI and C++ worlds."""

    jni_type: str            # type used in the JNI signature, e.g. "jstring"
    cpp_type: str            # local C++ variable type, e.g. "std::string"
    # marshalling expression; ``{env}`` and ``{var}`` are substituted.
    convert: Optional[str]   # None means "no local var needed" (e.g. void)
    is_handle: bool = False  # Long handles get a null-check by default
    is_string: bool = False  # strings get an empty-check helper available


# Kotlin (nullability stripped) -> TypeInfo.
#
# ``Long`` is treated as an opaque native handle (the dominant JNI convention
# for passing a ``void*`` across the boundary). A plain numeric long is rare in
# these signatures; callers who need one can post-process the int64_t value.
TYPE_MAP = {
    "Int":         TypeInfo("jint",     "int32_t",                  "static_cast<int32_t>({var})"),
    "Long":        TypeInfo("jlong",    "void*",                    "reinterpret_cast<void*>({var})", is_handle=True),
    "Float":       TypeInfo("jfloat",   "float",                    "static_cast<float>({var})"),
    "Double":      TypeInfo("jdouble",  "double",                   "static_cast<double>({var})"),
    "Boolean":     TypeInfo("jboolean", "bool",                     "({var} == JNI_TRUE)"),
    "Short":       TypeInfo("jshort",   "int16_t",                  "static_cast<int16_t>({var})"),
    "Byte":        TypeInfo("jbyte",    "int8_t",                   "static_cast<int8_t>({var})"),
    "String":      TypeInfo("jstring",  "std::string",              "jstring2string({env}, {var})", is_string=True),
    "ByteArray":   TypeInfo("jbyteArray",   "std::vector<uint8_t>", "extract_byte_array({env}, {var})"),
    "FloatArray":  TypeInfo("jfloatArray",  "std::vector<float>",   "extract_float_array({env}, {var})"),
    "IntArray":    TypeInfo("jintArray",    "std::vector<int32_t>", "extract_int_array({env}, {var})"),
    "LongArray":   TypeInfo("jlongArray",    "std::vector<int64_t>", "extract_long_array({env}, {var})"),
    "Array<String>": TypeInfo("jobjectArray", "std::vector<std::string>", "extract_string_array({env}, {var})"),
    "Unit":        TypeInfo("void",     "void",                     None),
}

# Return-type JNI mapping plus the "empty" value to return on an error path.
RETURN_MAP = {
    "Int":        ("jint",        "0"),
    "Long":       ("jlong",       "0"),
    "Float":      ("jfloat",      "0.0f"),
    "Double":     ("jdouble",     "0.0"),
    "Boolean":    ("jboolean",    "JNI_FALSE"),
    "Short":      ("jshort",      "0"),
    "Byte":       ("jbyte",       "0"),
    "String":     ("jstring",     "nullptr"),
    "ByteArray":  ("jbyteArray",  "nullptr"),
    "FloatArray": ("jfloatArray", "nullptr"),
    "IntArray":   ("jintArray",   "nullptr"),
    "LongArray":  ("jlongArray",  "nullptr"),
    "Unit":       ("void",        ""),
    None:         ("void",        ""),
}


class UnknownTypeError(ValueError):
    """Raised when a Kotlin type has no mapping. The message is actionable."""


def map_param_type(kotlin_type: str) -> TypeInfo:
    base = kotlin_type.rstrip("?").strip()
    if base in TYPE_MAP:
        return TYPE_MAP[base]
    raise UnknownTypeError(
        f"unrecognized parameter type '{kotlin_type}'. "
        f"Add a mapping for '{base}' to TYPE_MAP in jni-binding-generator.py."
    )


def map_return_type(kotlin_type: Optional[str]) -> Tuple[str, str]:
    base = kotlin_type.rstrip("?").strip() if kotlin_type else None
    if base in RETURN_MAP:
        return RETURN_MAP[base]
    raise UnknownTypeError(
        f"unrecognized return type '{kotlin_type}'. "
        f"Add a mapping for '{base}' to RETURN_MAP in jni-binding-generator.py."
    )


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

@dataclass
class Param:
    name: str
    kotlin_type: str


@dataclass
class ExternalFunction:
    name: str
    params: List[Param]
    return_type: Optional[str]


@dataclass
class ParsedFile:
    package: str
    class_name: str
    is_static: bool                       # object / companion -> static (jclass)
    functions: List[ExternalFunction] = field(default_factory=list)


_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)", re.MULTILINE)
# First top-level class or object declaration.
_DECL_RE = re.compile(r"\b(class|object)\s+(\w+)")
# external fun name(params): Return   — params captured non-greedily across lines.
_EXTERNAL_FUN_RE = re.compile(
    r"external\s+fun\s+(\w+)\s*\((.*?)\)\s*(?::\s*([\w.]+(?:<[\w.,\s]+>)?\??))?",
    re.DOTALL,
)


def _split_params(raw: str) -> List[Param]:
    """Split a parameter list, tolerating generics like Array<String> and trailing commas."""
    params: List[Param] = []
    depth = 0
    current = ""
    for ch in raw:
        if ch == "<":
            depth += 1
            current += ch
        elif ch == ">":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            if current.strip():
                params.append(_parse_one_param(current))
            current = ""
        else:
            current += ch
    if current.strip():
        params.append(_parse_one_param(current))
    return params


def _parse_one_param(chunk: str) -> Param:
    name, _, ktype = chunk.partition(":")
    name = name.strip()
    ktype = ktype.strip()
    # Drop a default value if present: "timeout: Int = 30"
    ktype = ktype.split("=")[0].strip()
    if not name or not ktype:
        raise ValueError(f"could not parse parameter '{chunk.strip()}'")
    return Param(name=name, kotlin_type=ktype)


_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_comments(source: str) -> str:
    """Remove block and line comments so they can't be mistaken for code.

    Without this, prose like "the class itself" would be picked up by the
    class-declaration regex.
    """
    source = _BLOCK_COMMENT_RE.sub("", source)
    source = _LINE_COMMENT_RE.sub("", source)
    return source


def parse_kotlin_source(source: str) -> ParsedFile:
    """Parse a single Kotlin source string into a ParsedFile."""
    source = _strip_comments(source)
    pkg_match = _PACKAGE_RE.search(source)
    package = pkg_match.group(1) if pkg_match else ""

    decl_match = _DECL_RE.search(source)
    if decl_match:
        kind, class_name = decl_match.group(1), decl_match.group(2)
        is_static = kind == "object"
    else:
        class_name = "Native"
        is_static = False

    # A companion object also makes the externals static even inside a class.
    if not is_static and re.search(r"companion\s+object", source):
        is_static = True

    functions: List[ExternalFunction] = []
    for m in _EXTERNAL_FUN_RE.finditer(source):
        name = m.group(1)
        params = _split_params(m.group(2))
        ret = m.group(3).strip() if m.group(3) else None
        functions.append(ExternalFunction(name=name, params=params, return_type=ret))

    return ParsedFile(
        package=package,
        class_name=class_name,
        is_static=is_static,
        functions=functions,
    )


def parse_kotlin_file(path: Path) -> ParsedFile:
    return parse_kotlin_source(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# JNI name mangling
# --------------------------------------------------------------------------- #

def mangle(segment: str) -> str:
    """Apply JNI short-name mangling to a single identifier segment."""
    out = []
    for ch in segment:
        if ch == "_":
            out.append("_1")
        elif ch == ".":
            out.append("_")
        else:
            out.append(ch)
    return "".join(out)


def jni_function_name(package: str, class_name: str, method: str) -> str:
    pkg = mangle(package) if package else ""
    parts = ["Java", pkg, mangle(class_name), mangle(method)]
    return "_".join(p for p in parts if p)


# --------------------------------------------------------------------------- #
# C++ generation
# --------------------------------------------------------------------------- #

def _cpp_var_name(param: Param, info: TypeInfo) -> str:
    if info.is_handle:
        return f"{param.name}_ptr"
    return f"{param.name}_val"


def generate_function(parsed: ParsedFile, func: ExternalFunction) -> str:
    ret_jni, ret_empty = map_return_type(func.return_type)
    jni_name = jni_function_name(parsed.package, parsed.class_name, func.name)
    receiver = "jclass clazz" if parsed.is_static else "jobject thiz"
    ret_stmt = f"return {ret_empty};" if ret_empty else "return;"

    # Signature
    sig_params = ["JNIEnv* env", receiver]
    for p in func.params:
        info = map_param_type(p.kotlin_type)
        sig_params.append(f"{info.jni_type} {p.name}")
    signature = ",\n        ".join(sig_params)

    lines: List[str] = []
    lines.append(f'extern "C" JNIEXPORT {ret_jni} JNICALL')
    lines.append(f"{jni_name}(")
    lines.append(f"        {signature}) {{")

    # Marshalling
    marshalled: List[Tuple[Param, TypeInfo, str]] = []
    real_params = [p for p in func.params if map_param_type(p.kotlin_type).convert is not None]
    if real_params:
        lines.append("    // --- Marshalling ---")
    for p in real_params:
        info = map_param_type(p.kotlin_type)
        var = _cpp_var_name(p, info)
        expr = info.convert.format(env="env", var=p.name)
        lines.append(f"    {info.cpp_type} {var} = {expr};")
        marshalled.append((p, info, var))

    # Error handling
    checks: List[str] = []
    for p, info, var in marshalled:
        if info.is_handle:
            checks.append(
                f"    if (!{var}) {{\n"
                f'        throw_illegal_state(env, "{func.name}: {p.name} not initialized");\n'
                f"        {ret_stmt}\n"
                f"    }}"
            )
        elif info.is_string:
            checks.append(
                f"    if ({var}.empty()) {{\n"
                f'        throw_illegal_argument(env, "{func.name}: {p.name} is required");\n'
                f"        {ret_stmt}\n"
                f"    }}"
            )
    if checks:
        lines.append("")
        lines.append("    // --- Error handling ---")
        lines.extend(checks)

    # Body stub
    lines.append("")
    lines.append("    // --- TODO: hand-written native logic ---")
    lines.append("    // Call into your native library using the marshalled values above.")
    lines.append(f"    {ret_stmt}")
    lines.append("}")

    return "\n".join(lines)


_FILE_HEADER = """// AUTO-GENERATED by jni-binding-generator.py — DO NOT EDIT.
// Source: {source}
//
// Regenerate with:  ./gradlew generateJniBindings   (or run the script directly)
// Hand-written logic belongs in the corresponding *-jni.cpp, not here.

#include <jni.h>
#include <string>
#include <vector>
#include <cstdint>

#include "jni-utils.h"
"""


def generate_file(parsed: ParsedFile, source_name: str) -> str:
    parts = [_FILE_HEADER.format(source=source_name)]
    for func in parsed.functions:
        parts.append("")
        parts.append(generate_function(parsed, func))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def collect_kotlin_files(source: Path) -> List[Path]:
    if source.is_file():
        return [source] if source.suffix == ".kt" else []
    return sorted(source.rglob("*.kt"))


def run(kotlin_source: Path, output_dir: Path, dry_run: bool) -> int:
    files = collect_kotlin_files(kotlin_source)
    if not files:
        print(f"No .kt files found under {kotlin_source}", file=sys.stderr)
        return 1

    generated = 0
    for kt in files:
        parsed = parse_kotlin_file(kt)
        if not parsed.functions:
            continue
        try:
            content = generate_file(parsed, kt.name)
        except UnknownTypeError as exc:
            print(f"Error in {kt}: {exc}", file=sys.stderr)
            return 2

        out_path = output_dir / f"{parsed.class_name}_jni.gen.cpp"
        print(f"{kt}  ->  {out_path}  ({len(parsed.functions)} fn)")
        if dry_run:
            print(content)
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        generated += 1

    if generated == 0:
        print("No external functions found; nothing generated.", file=sys.stderr)
        return 1
    print(f"Done. Generated {generated} file(s).")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate C++ JNI bindings from Kotlin external functions"
    )
    parser.add_argument(
        "--kotlin-source",
        required=True,
        help="Path to a Kotlin file or source directory (scanned recursively)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for generated C++ files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated code without writing files",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    kotlin_source = Path(args.kotlin_source)
    if not kotlin_source.exists():
        print(f"Error: Kotlin source path does not exist: {kotlin_source}", file=sys.stderr)
        return 1
    return run(kotlin_source, Path(args.output), args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
