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
    python3 jni-binding-generator.py --kotlin-source <path> --output <path> --check

``--kotlin-source`` may point at a single ``.kt`` file or a directory (it is
scanned recursively for ``.kt`` files).

Writes are incremental: a generated file is only rewritten when its content
changes, so unchanged outputs keep their mtime and don't trigger rebuilds.
``--check`` verifies the committed output is up to date without writing and
exits non-zero on drift (for CI / pre-commit).

Exit codes: 0 ok, 1 usage/no input, 2 parse or type error, 3 drift (--check).

Known limitations (by design — the generator assumes one declaration style per
class and the conventional ``external fun nativeXxx`` shape):
  * Static-ness is determined per file (``object`` / ``companion object``), not
    per function. Mixing companion-object and instance ``external fun`` in one
    class is not supported — split them into separate declarations.
  * Overloaded ``external fun`` names emit the short ``Java_*`` symbol and would
    collide; give native methods unique names (the usual JNI convention).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Type mapping
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TypeInfo:
    """How a Kotlin type maps onto the JNI and C++ worlds."""

    jni_type: str  # type used in the JNI signature, e.g. "jstring"
    cpp_type: str  # local C++ variable type, e.g. "std::string"
    # marshalling expression; ``{env}`` and ``{var}`` are substituted.
    convert: str | None  # None means "no local var needed" (e.g. void)
    is_handle: bool = False  # Long handles get a null-check by default
    is_string: bool = False  # strings get an empty-check helper available


# Kotlin (nullability stripped) -> TypeInfo.
#
# ``Long`` is treated as an opaque native handle (the dominant JNI convention
# for passing a ``void*`` across the boundary). A plain numeric long is rare in
# these signatures; callers who need one can post-process the int64_t value.
TYPE_MAP = {
    "Int": TypeInfo("jint", "int32_t", "static_cast<int32_t>({var})"),
    "Long": TypeInfo("jlong", "void*", "reinterpret_cast<void*>({var})", is_handle=True),
    "Float": TypeInfo("jfloat", "float", "static_cast<float>({var})"),
    "Double": TypeInfo("jdouble", "double", "static_cast<double>({var})"),
    "Boolean": TypeInfo("jboolean", "bool", "({var} == JNI_TRUE)"),
    "Short": TypeInfo("jshort", "int16_t", "static_cast<int16_t>({var})"),
    "Byte": TypeInfo("jbyte", "int8_t", "static_cast<int8_t>({var})"),
    "String": TypeInfo("jstring", "std::string", "jstring2string({env}, {var})", is_string=True),
    "ByteArray": TypeInfo("jbyteArray", "std::vector<uint8_t>", "extract_byte_array({env}, {var})"),
    "FloatArray": TypeInfo(
        "jfloatArray", "std::vector<float>", "extract_float_array({env}, {var})"
    ),
    "IntArray": TypeInfo("jintArray", "std::vector<int32_t>", "extract_int_array({env}, {var})"),
    "LongArray": TypeInfo("jlongArray", "std::vector<int64_t>", "extract_long_array({env}, {var})"),
    "ShortArray": TypeInfo(
        "jshortArray", "std::vector<int16_t>", "extract_short_array({env}, {var})"
    ),
    "DoubleArray": TypeInfo(
        "jdoubleArray", "std::vector<double>", "extract_double_array({env}, {var})"
    ),
    "BooleanArray": TypeInfo(
        "jbooleanArray", "std::vector<bool>", "extract_bool_array({env}, {var})"
    ),
    "Array<String>": TypeInfo(
        "jobjectArray", "std::vector<std::string>", "extract_string_array({env}, {var})"
    ),
    # java.util.List variants — arrive as jobject, unboxed to std::vector
    "List<String>": TypeInfo(
        "jobject", "std::vector<std::string>", "extract_list_string({env}, {var})"
    ),
    "List<Int>": TypeInfo("jobject", "std::vector<int32_t>", "extract_list_int({env}, {var})"),
    "List<Long>": TypeInfo("jobject", "std::vector<int64_t>", "extract_list_long({env}, {var})"),
    "List<Float>": TypeInfo("jobject", "std::vector<float>", "extract_list_float({env}, {var})"),
    "List<Double>": TypeInfo("jobject", "std::vector<double>", "extract_list_double({env}, {var})"),
    "List<Boolean>": TypeInfo("jobject", "std::vector<bool>", "extract_list_bool({env}, {var})"),
    "List<Byte>": TypeInfo("jobject", "std::vector<int8_t>", "extract_list_byte({env}, {var})"),
    # Kotlin Array<T> of boxed types — jobjectArray, unboxed to std::vector
    "Array<Int>": TypeInfo(
        "jobjectArray", "std::vector<int32_t>", "extract_boxed_int_array({env}, {var})"
    ),
    "Array<Long>": TypeInfo(
        "jobjectArray", "std::vector<int64_t>", "extract_boxed_long_array({env}, {var})"
    ),
    "Array<Float>": TypeInfo(
        "jobjectArray", "std::vector<float>", "extract_boxed_float_array({env}, {var})"
    ),
    "Array<Double>": TypeInfo(
        "jobjectArray", "std::vector<double>", "extract_boxed_double_array({env}, {var})"
    ),
    # Nested collections
    "List<List<String>>": TypeInfo(
        "jobject", "std::vector<std::vector<std::string>>", "extract_list_list_string({env}, {var})"
    ),
    # java.util.Set variants
    "Set<String>": TypeInfo(
        "jobject", "std::unordered_set<std::string>", "extract_set_string({env}, {var})"
    ),
    "Set<Int>": TypeInfo("jobject", "std::unordered_set<int32_t>", "extract_set_int({env}, {var})"),
    "Set<Long>": TypeInfo(
        "jobject", "std::unordered_set<int64_t>", "extract_set_long({env}, {var})"
    ),
    "Set<Float>": TypeInfo(
        "jobject", "std::unordered_set<float>", "extract_set_float({env}, {var})"
    ),
    "Set<Boolean>": TypeInfo(
        "jobject", "std::unordered_set<bool>", "extract_set_bool({env}, {var})"
    ),
    "Set<Double>": TypeInfo(
        "jobject", "std::unordered_set<double>", "extract_set_double({env}, {var})"
    ),
    # java.util.List — Short variant (completes the primitive family)
    "List<Short>": TypeInfo("jobject", "std::vector<int16_t>", "extract_list_short({env}, {var})"),
    # Nested List<List<T>> variants
    "List<List<Int>>": TypeInfo(
        "jobject",
        "std::vector<std::vector<int32_t>>",
        "extract_list_list_int({env}, {var})",
    ),
    "List<List<Float>>": TypeInfo(
        "jobject",
        "std::vector<std::vector<float>>",
        "extract_list_list_float({env}, {var})",
    ),
    "List<List<Long>>": TypeInfo(
        "jobject",
        "std::vector<std::vector<int64_t>>",
        "extract_list_list_long({env}, {var})",
    ),
    "List<List<Double>>": TypeInfo(
        "jobject",
        "std::vector<std::vector<double>>",
        "extract_list_list_double({env}, {var})",
    ),
    "List<List<Boolean>>": TypeInfo(
        "jobject",
        "std::vector<std::vector<bool>>",
        "extract_list_list_bool({env}, {var})",
    ),
    "List<List<Short>>": TypeInfo(
        "jobject",
        "std::vector<std::vector<int16_t>>",
        "extract_list_list_short({env}, {var})",
    ),
    "List<List<Byte>>": TypeInfo(
        "jobject",
        "std::vector<std::vector<int8_t>>",
        "extract_list_list_byte({env}, {var})",
    ),
    "Set<Byte>": TypeInfo(
        "jobject", "std::unordered_set<int8_t>", "extract_set_byte({env}, {var})"
    ),
    "Set<Short>": TypeInfo(
        "jobject", "std::unordered_set<int16_t>", "extract_set_short({env}, {var})"
    ),
    # Boxed Array<T> for remaining scalar types
    "Array<Byte>": TypeInfo(
        "jobjectArray", "std::vector<int8_t>", "extract_boxed_byte_array({env}, {var})"
    ),
    "Array<Boolean>": TypeInfo(
        "jobjectArray", "std::vector<bool>", "extract_boxed_bool_array({env}, {var})"
    ),
    "Array<Short>": TypeInfo(
        "jobjectArray", "std::vector<int16_t>", "extract_boxed_short_array({env}, {var})"
    ),
    # java.util.Map variants
    "Map<String, String>": TypeInfo(
        "jobject",
        "std::unordered_map<std::string, std::string>",
        "extract_map_string_string({env}, {var})",
    ),
    "Map<String, Int>": TypeInfo(
        "jobject",
        "std::unordered_map<std::string, int32_t>",
        "extract_map_string_int({env}, {var})",
    ),
    "Map<String, Long>": TypeInfo(
        "jobject",
        "std::unordered_map<std::string, int64_t>",
        "extract_map_string_long({env}, {var})",
    ),
    "Map<String, Float>": TypeInfo(
        "jobject",
        "std::unordered_map<std::string, float>",
        "extract_map_string_float({env}, {var})",
    ),
    "Map<String, Boolean>": TypeInfo(
        "jobject",
        "std::unordered_map<std::string, bool>",
        "extract_map_string_bool({env}, {var})",
    ),
    "Map<Int, String>": TypeInfo(
        "jobject",
        "std::unordered_map<int32_t, std::string>",
        "extract_map_int_string({env}, {var})",
    ),
    "Map<Int, Int>": TypeInfo(
        "jobject",
        "std::unordered_map<int32_t, int32_t>",
        "extract_map_int_int({env}, {var})",
    ),
    "Map<Int, Long>": TypeInfo(
        "jobject",
        "std::unordered_map<int32_t, int64_t>",
        "extract_map_int_long({env}, {var})",
    ),
    "Map<Int, Float>": TypeInfo(
        "jobject",
        "std::unordered_map<int32_t, float>",
        "extract_map_int_float({env}, {var})",
    ),
    "Map<Int, Boolean>": TypeInfo(
        "jobject",
        "std::unordered_map<int32_t, bool>",
        "extract_map_int_bool({env}, {var})",
    ),
    "Map<String, Double>": TypeInfo(
        "jobject",
        "std::unordered_map<std::string, double>",
        "extract_map_string_double({env}, {var})",
    ),
    "Map<Int, Double>": TypeInfo(
        "jobject",
        "std::unordered_map<int32_t, double>",
        "extract_map_int_double({env}, {var})",
    ),
    "Map<Long, Int>": TypeInfo(
        "jobject",
        "std::unordered_map<int64_t, int32_t>",
        "extract_map_long_int({env}, {var})",
    ),
    "Map<Long, Long>": TypeInfo(
        "jobject",
        "std::unordered_map<int64_t, int64_t>",
        "extract_map_long_long({env}, {var})",
    ),
    "Map<Long, String>": TypeInfo(
        "jobject",
        "std::unordered_map<int64_t, std::string>",
        "extract_map_long_string({env}, {var})",
    ),
    "Map<Long, Float>": TypeInfo(
        "jobject",
        "std::unordered_map<int64_t, float>",
        "extract_map_long_float({env}, {var})",
    ),
    "Map<Long, Double>": TypeInfo(
        "jobject",
        "std::unordered_map<int64_t, double>",
        "extract_map_long_double({env}, {var})",
    ),
    "Map<Long, Boolean>": TypeInfo(
        "jobject",
        "std::unordered_map<int64_t, bool>",
        "extract_map_long_bool({env}, {var})",
    ),
    "Unit": TypeInfo("void", "void", None),
}

# Return-type JNI mapping plus the "empty" value to return on an error path.
RETURN_MAP = {
    "Int": ("jint", "0"),
    "Long": ("jlong", "0"),
    "Float": ("jfloat", "0.0f"),
    "Double": ("jdouble", "0.0"),
    "Boolean": ("jboolean", "JNI_FALSE"),
    "Short": ("jshort", "0"),
    "Byte": ("jbyte", "0"),
    "String": ("jstring", "nullptr"),
    "ByteArray": ("jbyteArray", "nullptr"),
    "FloatArray": ("jfloatArray", "nullptr"),
    "IntArray": ("jintArray", "nullptr"),
    "LongArray": ("jlongArray", "nullptr"),
    "ShortArray": ("jshortArray", "nullptr"),
    "DoubleArray": ("jdoubleArray", "nullptr"),
    "BooleanArray": ("jbooleanArray", "nullptr"),
    "Array<String>": ("jobjectArray", "nullptr"),
    "List<String>": ("jobject", "nullptr"),
    "List<Int>": ("jobject", "nullptr"),
    "List<Long>": ("jobject", "nullptr"),
    "List<Float>": ("jobject", "nullptr"),
    "List<Double>": ("jobject", "nullptr"),
    "List<Boolean>": ("jobject", "nullptr"),
    "List<Byte>": ("jobject", "nullptr"),
    "Array<Int>": ("jobjectArray", "nullptr"),
    "Array<Long>": ("jobjectArray", "nullptr"),
    "Array<Float>": ("jobjectArray", "nullptr"),
    "Array<Double>": ("jobjectArray", "nullptr"),
    "List<Short>": ("jobject", "nullptr"),
    "List<List<String>>": ("jobject", "nullptr"),
    "List<List<Int>>": ("jobject", "nullptr"),
    "List<List<Float>>": ("jobject", "nullptr"),
    "List<List<Long>>": ("jobject", "nullptr"),
    "List<List<Double>>": ("jobject", "nullptr"),
    "List<List<Boolean>>": ("jobject", "nullptr"),
    "List<List<Short>>": ("jobject", "nullptr"),
    "List<List<Byte>>": ("jobject", "nullptr"),
    "Set<Byte>": ("jobject", "nullptr"),
    "Set<Short>": ("jobject", "nullptr"),
    "Set<String>": ("jobject", "nullptr"),
    "Set<Int>": ("jobject", "nullptr"),
    "Set<Long>": ("jobject", "nullptr"),
    "Set<Float>": ("jobject", "nullptr"),
    "Set<Boolean>": ("jobject", "nullptr"),
    "Set<Double>": ("jobject", "nullptr"),
    "Array<Byte>": ("jobjectArray", "nullptr"),
    "Array<Boolean>": ("jobjectArray", "nullptr"),
    "Array<Short>": ("jobjectArray", "nullptr"),
    "Map<String, String>": ("jobject", "nullptr"),
    "Map<String, Int>": ("jobject", "nullptr"),
    "Map<String, Long>": ("jobject", "nullptr"),
    "Map<String, Float>": ("jobject", "nullptr"),
    "Map<String, Boolean>": ("jobject", "nullptr"),
    "Map<Int, String>": ("jobject", "nullptr"),
    "Map<Int, Int>": ("jobject", "nullptr"),
    "Map<Int, Long>": ("jobject", "nullptr"),
    "Map<Int, Float>": ("jobject", "nullptr"),
    "Map<Int, Boolean>": ("jobject", "nullptr"),
    "Map<String, Double>": ("jobject", "nullptr"),
    "Map<Int, Double>": ("jobject", "nullptr"),
    "Map<Long, Double>": ("jobject", "nullptr"),
    "Map<Long, Int>": ("jobject", "nullptr"),
    "Map<Long, Long>": ("jobject", "nullptr"),
    "Map<Long, String>": ("jobject", "nullptr"),
    "Map<Long, Float>": ("jobject", "nullptr"),
    "Map<Long, Boolean>": ("jobject", "nullptr"),
    "Unit": ("void", ""),
    None: ("void", ""),
}


class UnknownTypeError(ValueError):
    """Raised when a Kotlin type has no mapping. The message is actionable."""


_ENUM_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")


def _looks_like_enum(base: str) -> bool:
    """Heuristic: simple capitalized identifier with no generics → likely a Kotlin enum."""
    return bool(_ENUM_RE.match(base))


def _is_nullable(kotlin_type: str) -> bool:
    return kotlin_type.strip().endswith("?")


def _needs_exception_check(info: TypeInfo) -> bool:
    """True for TypeInfos whose conversion calls a JNI API that can pend an exception.

    Strings call GetStringUTFChars; arrays call Get*ArrayRegion / GetObjectArrayElement.
    Primitive casts are pure C and never pend exceptions.
    """
    return (
        info.is_string
        or info.cpp_type.startswith(("std::vector", "std::unordered_map", "std::unordered_set"))
        or info is _ENUM_TYPE
    )


_ENUM_TYPE = TypeInfo("jobject", "int32_t", "enum_ordinal({env}, {var})")


def map_param_type(kotlin_type: str) -> TypeInfo:
    base = kotlin_type.rstrip("?").strip()
    if base in TYPE_MAP:
        return TYPE_MAP[base]
    if _looks_like_enum(base):
        return _ENUM_TYPE
    raise UnknownTypeError(
        f"unrecognized parameter type '{kotlin_type}'. "
        f"Add a mapping for '{base}' to TYPE_MAP in jni-binding-generator.py."
    )


def map_return_type(kotlin_type: str | None) -> tuple[str, str]:
    base = kotlin_type.rstrip("?").strip() if kotlin_type else None
    if base in RETURN_MAP:
        return RETURN_MAP[base]
    if base and _looks_like_enum(base):
        return ("jint", "0")  # return the ordinal as jint
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
    params: list[Param]
    return_type: str | None
    line: int = 0  # 1-based line of the declaration in the source file


@dataclass
class ParsedFile:
    package: str
    class_name: str
    is_static: bool  # object / companion -> static (jclass)
    functions: list[ExternalFunction] = field(default_factory=list)


_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)", re.MULTILINE)
# First top-level class or object declaration (captures nesting: "class Outer { class Inner").
_DECL_RE = re.compile(r"\b(class|object)\s+(\w+)")
# Kotlin file name for top-level funs: "foo/Bar.kt" → "BarKt"
_FILENAME_KT_RE = re.compile(r"([A-Za-z0-9_]+)\.kt$")
# @JvmName("altName") immediately before an external fun.
_JVM_NAME_RE = re.compile(r'@JvmName\s*\(\s*"(\w+)"\s*\)')
# Detect unsupported constructs that must be rejected before code-gen.
# Both "suspend external fun" and "external suspend fun" are valid Kotlin.
_SUSPEND_RE = re.compile(r"\b(?:suspend\s+external|external\s+suspend)\s+fun\b")
_EXTENSION_FUN_RE = re.compile(r"\bexternal\s+fun\s+\w+\.")
_VARARG_RE = re.compile(r"\bvararg\s+\w+\s*:")
_FN_TYPE_RE = re.compile(r":\s*\(")  # function-type param: "cb: (Int) -> String"
# external fun name(params): Return   — params captured non-greedily across lines.
_EXTERNAL_FUN_RE = re.compile(
    r"external\s+fun\s+(\w+)\s*\((.*?)\)\s*"
    r"(?::\s*([\w.]+(?:<(?:[^<>]|<[^<>]*>)*>)?\??))?",
    re.DOTALL,
)


def _split_params(raw: str) -> list[Param]:
    """Split a parameter list, tolerating generics like Array<String> and trailing commas."""
    params: list[Param] = []
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
    chunk = chunk.strip()
    if chunk.startswith("vararg "):
        raise UnknownTypeError(
            f"'vararg' parameters are not supported by the generator: '{chunk}'. "
            "Collect the items on the Kotlin side and pass an Array or List instead."
        )
    name, _, ktype = chunk.partition(":")
    name = name.strip()
    ktype = ktype.strip()
    # Drop a default value if present: "timeout: Int = 30"
    ktype = ktype.split("=")[0].strip()
    if not name or not ktype:
        raise ValueError(f"could not parse parameter '{chunk.strip()}'")
    if ktype.startswith("("):
        raise UnknownTypeError(
            f"function-type parameters are not supported: '{name}: {ktype}'. "
            "Use a plain interface or pass a callback handle (Long) instead."
        )
    return Param(name=name, kotlin_type=ktype)


_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_comments(source: str) -> str:
    """Blank out block and line comments so they can't be mistaken for code.

    Without this, prose like "the class itself" would be picked up by the
    class-declaration regex. Comments are replaced with whitespace that
    preserves the original newline count, so reported line numbers stay
    accurate.
    """

    def blank(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    source = _BLOCK_COMMENT_RE.sub(blank, source)
    source = _LINE_COMMENT_RE.sub("", source)
    return source


def parse_kotlin_source(source: str, filename: str = "") -> ParsedFile:
    """Parse a single Kotlin source string into a ParsedFile."""
    source = _strip_comments(source)

    # MVP 1: reject suspend funs and extension funs up front with clear messages.
    if _SUSPEND_RE.search(source):
        raise UnknownTypeError(
            "'suspend external fun' is not supported. "
            "Expose a plain 'external fun' wrapper and call it from a coroutine dispatcher."
        )
    if _EXTENSION_FUN_RE.search(source):
        raise UnknownTypeError(
            "Extension 'external fun' (e.g. 'fun String.foo()') is not supported. "
            "Move the function into a class or object instead."
        )

    pkg_match = _PACKAGE_RE.search(source)
    package = pkg_match.group(1) if pkg_match else ""

    # MVP 2: nested class — collect all class/object declarations in order;
    # the JNI name for Outer.Inner is "Outer_00024Inner" ($ = _00024).
    decl_matches = list(_DECL_RE.finditer(source))
    if decl_matches:
        # The outermost declaration is the first match; subsequent ones inside
        # its body are nested. Walk all of them to build the full qualified name.
        kinds_names = [(m.group(1), m.group(2)) for m in decl_matches]
        # Only include class/object names, stop at the first companion object
        # (it doesn't appear in the JNI class name).
        parts = []
        is_static = False
        for kind, name in kinds_names:
            if kind == "object" and name == "Companion":
                is_static = True
                break
            if kind == "object":
                is_static = True
            parts.append(name)
        class_name = "$".join(parts) if len(parts) > 1 else (parts[0] if parts else "Native")
    else:
        # MVP 4: top-level external fun — use "<Filename>Kt" as class name,
        # matching what the Kotlin compiler emits for top-level declarations.
        fn_match = _FILENAME_KT_RE.search(filename)
        class_name = (fn_match.group(1) + "Kt") if fn_match else "Native"
        is_static = True  # top-level funs are static in the generated class

    # A companion object also makes the externals static even inside a class.
    if not is_static and re.search(r"companion\s+object", source):
        is_static = True

    functions: list[ExternalFunction] = []
    for m in _EXTERNAL_FUN_RE.finditer(source):
        # MVP 3: honour @JvmName if it appears in the 300 chars before "external fun".
        lookahead = source[max(0, m.start() - 300) : m.start()]
        jvm_name_match = _JVM_NAME_RE.search(lookahead)
        name = jvm_name_match.group(1) if jvm_name_match else m.group(1)
        line = source.count("\n", 0, m.start()) + 1
        params = _split_params(m.group(2))
        ret = m.group(3).strip() if m.group(3) else None
        functions.append(ExternalFunction(name=name, params=params, return_type=ret, line=line))

    return ParsedFile(
        package=package,
        class_name=class_name,
        is_static=is_static,
        functions=functions,
    )


def _find_top_level_class_ranges(stripped: str) -> list[tuple[int, int]]:
    """Return (start, end) character offsets of each top-level class/object block.

    'Top-level' means the class/object keyword appears at brace depth 0 in the
    stripped source (comments already removed).  Each range spans from the
    keyword to the character after the matching closing brace.
    """
    _kw_re = re.compile(r"\b(class|object)\b")
    ranges: list[tuple[int, int]] = []
    for m in _kw_re.finditer(stripped):
        prefix = stripped[: m.start()]
        depth = prefix.count("{") - prefix.count("}")
        if depth != 0:
            continue  # nested class — belongs to its parent
        after = stripped[m.end() :]
        brace_pos = after.find("{")
        if brace_pos == -1:
            continue  # no body (interface / abstract without body)
        body_start = m.end() + brace_pos + 1
        d = 1
        pos = body_start
        while pos < len(stripped) and d > 0:
            c = stripped[pos]
            if c == "{":
                d += 1
            elif c == "}":
                d -= 1
            pos += 1
        ranges.append((m.start(), pos))
    return ranges


def parse_kotlin_source_multi(source: str, filename: str = "") -> list[ParsedFile]:
    """Parse a Kotlin source file that may contain multiple top-level classes.

    Returns one ParsedFile per top-level class/object that contains at least one
    external fun.  If the file has only one class (the common case) this is
    equivalent to [parse_kotlin_source(source, filename)].
    """
    stripped = _strip_comments(source)
    ranges = _find_top_level_class_ranges(stripped)

    if len(ranges) <= 1:
        # Single class or top-level funs — fast path.
        return [parse_kotlin_source(source, filename)]

    pkg_match = _PACKAGE_RE.search(stripped)
    pkg_prefix = f"package {pkg_match.group(1)}\n\n" if pkg_match else ""

    results: list[ParsedFile] = []
    for start, end in ranges:
        segment = pkg_prefix + stripped[start:end]
        parsed = parse_kotlin_source(segment, filename)
        if parsed.functions:
            results.append(parsed)

    return results if results else [parse_kotlin_source(source, filename)]


def parse_kotlin_file(path: Path) -> list[ParsedFile]:
    return parse_kotlin_source_multi(path.read_text(encoding="utf-8"), filename=path.name)


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
        elif ch == "$":
            out.append("_00024")
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

    lines: list[str] = []
    lines.append(f'extern "C" JNIEXPORT {ret_jni} JNICALL')
    lines.append(f"{jni_name}(")
    lines.append(f"        {signature}) {{")

    # Marshalling
    marshalled: list[tuple[Param, TypeInfo, str]] = []
    real_params = [p for p in func.params if map_param_type(p.kotlin_type).convert is not None]
    if real_params:
        lines.append("    // --- Marshalling ---")
    for p in real_params:
        info = map_param_type(p.kotlin_type)
        var = _cpp_var_name(p, info)
        expr = info.convert.format(env="env", var=p.name)
        lines.append(f"    {info.cpp_type} {var} = {expr};")
        # GEN-1: emit ExceptionCheck after JNI calls that can pend an exception
        # (string and array conversions). Pure C casts need no check.
        if _needs_exception_check(info):
            lines.append(f"    if (env->ExceptionCheck()) {ret_stmt}")
        marshalled.append((p, info, var))

    # Error handling. Nullable parameters (e.g. `String?`, `Long?`) are allowed
    # to be null/empty, so they get no required-value guard — null flows to the
    # hand-written body.
    checks: list[str] = []
    for p, info, var in marshalled:
        if _is_nullable(p.kotlin_type):
            continue
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
    base_rt = func.return_type.rstrip("?").strip() if func.return_type else None
    make_fn = _MAKE_HELPER_MAP.get(base_rt or "", (None, None))[0]
    if make_fn:
        lines.append(f"    // Return: use {make_fn}(env, yourResult) to build the jobject.")
    elif base_rt and _looks_like_enum(base_rt) and base_rt not in RETURN_MAP:
        lines.append(
            f"    // Return: jint ordinal — call {base_rt}.values()[result] on the Kotlin side."
        )
    lines.append(f"    {ret_stmt}")
    lines.append("}")

    return "\n".join(lines)


# Module-level so both generate_function() and generate_test_file() share it.
_MAKE_HELPER_MAP: dict[str, tuple[str, str]] = {
    "List<String>": ("make_list_string", "std::vector<std::string>"),
    "List<Int>": ("make_list_int", "std::vector<int32_t>"),
    "List<Long>": ("make_list_long", "std::vector<int64_t>"),
    "List<Float>": ("make_list_float", "std::vector<float>"),
    "List<Double>": ("make_list_double", "std::vector<double>"),
    "List<Boolean>": ("make_list_bool", "std::vector<bool>"),
    "List<Byte>": ("make_list_byte", "std::vector<int8_t>"),
    "List<Short>": ("make_list_short", "std::vector<int16_t>"),
    "List<List<String>>": ("make_list_list_string", "std::vector<std::vector<std::string>>"),
    "Set<String>": ("make_set_string", "std::unordered_set<std::string>"),
    "Set<Int>": ("make_set_int", "std::unordered_set<int32_t>"),
    "Set<Long>": ("make_set_long", "std::unordered_set<int64_t>"),
    "Set<Float>": ("make_set_float", "std::unordered_set<float>"),
    "Set<Boolean>": ("make_set_bool", "std::unordered_set<bool>"),
    "Set<Double>": ("make_set_double", "std::unordered_set<double>"),
    "List<List<Int>>": ("make_list_list_int", "std::vector<std::vector<int32_t>>"),
    "List<List<Float>>": ("make_list_list_float", "std::vector<std::vector<float>>"),
    "List<List<Long>>": ("make_list_list_long", "std::vector<std::vector<int64_t>>"),
    "List<List<Double>>": ("make_list_list_double", "std::vector<std::vector<double>>"),
    "List<List<Boolean>>": ("make_list_list_bool", "std::vector<std::vector<bool>>"),
    "List<List<Short>>": ("make_list_list_short", "std::vector<std::vector<int16_t>>"),
    "List<List<Byte>>": ("make_list_list_byte", "std::vector<std::vector<int8_t>>"),
    "Set<Byte>": ("make_set_byte", "std::unordered_set<int8_t>"),
    "Set<Short>": ("make_set_short", "std::unordered_set<int16_t>"),
    "Map<Int, Int>": ("make_map_int_int", "std::unordered_map<int32_t, int32_t>"),
    "Map<Int, Long>": ("make_map_int_long", "std::unordered_map<int32_t, int64_t>"),
    "Map<Int, Float>": ("make_map_int_float", "std::unordered_map<int32_t, float>"),
    "Map<Int, Boolean>": ("make_map_int_bool", "std::unordered_map<int32_t, bool>"),
    "Map<String, String>": (
        "make_map_string_string",
        "std::unordered_map<std::string, std::string>",
    ),
    "Map<String, Int>": ("make_map_string_int", "std::unordered_map<std::string, int32_t>"),
    "Map<String, Long>": ("make_map_string_long", "std::unordered_map<std::string, int64_t>"),
    "Map<String, Float>": ("make_map_string_float", "std::unordered_map<std::string, float>"),
    "Map<String, Boolean>": ("make_map_string_bool", "std::unordered_map<std::string, bool>"),
    "Map<Int, String>": ("make_map_int_string", "std::unordered_map<int32_t, std::string>"),
    "Map<String, Double>": ("make_map_string_double", "std::unordered_map<std::string, double>"),
    "Map<Int, Double>": ("make_map_int_double", "std::unordered_map<int32_t, double>"),
    "Map<Long, Int>": ("make_map_long_int", "std::unordered_map<int64_t, int32_t>"),
    "Map<Long, Long>": ("make_map_long_long", "std::unordered_map<int64_t, int64_t>"),
    "Map<Long, String>": ("make_map_long_string", "std::unordered_map<int64_t, std::string>"),
    "Map<Long, Float>": ("make_map_long_float", "std::unordered_map<int64_t, float>"),
    "Map<Long, Double>": ("make_map_long_double", "std::unordered_map<int64_t, double>"),
    "Map<Long, Boolean>": ("make_map_long_bool", "std::unordered_map<int64_t, bool>"),
}


# Zero / null value for each JNI type, used in compile-check stubs.
_JNI_ZERO: dict[str, str] = {
    "jstring": "nullptr",
    "jobject": "nullptr",
    "jobjectArray": "nullptr",
    "jbyteArray": "nullptr",
    "jshortArray": "nullptr",
    "jintArray": "nullptr",
    "jlongArray": "nullptr",
    "jfloatArray": "nullptr",
    "jdoubleArray": "nullptr",
    "jbooleanArray": "nullptr",
}


_FILE_HEADER = """// AUTO-GENERATED by jni-binding-generator.py — DO NOT EDIT.
// Source: {source}
//
// Regenerate with:  ./gradlew generateJniBindings   (or run the script directly)
// Hand-written logic belongs in the corresponding *-jni.cpp, not here.

#include <jni.h>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <cstdint>

#include "jni-utils.h"
"""


def generate_file(parsed: ParsedFile, source_name: str) -> str:
    parts = [_FILE_HEADER.format(source=source_name)]
    for func in parsed.functions:
        try:
            body = generate_function(parsed, func)
        except UnknownTypeError as exc:
            # Re-raise with the source location so the caller can point at it.
            raise UnknownTypeError(f"line {func.line}, {func.name}(): {exc}") from exc
        parts.append("")
        parts.append(body)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


_TEST_FILE_HEADER = """\
// AUTO-GENERATED by jni-binding-generator.py — DO NOT EDIT.
// Source: {source}
//
// Compile-time type check for jni-utils.h helpers used by {source}.
// Every helper call lives inside ``if (false)`` so the compiler type-checks
// the call without executing it — any signature mismatch is a compile error.
//
// Compile (syntax check only):
//   clang++ -std=c++17 -fsyntax-only \\
//       -I$JAVA_HOME/include -I$JAVA_HOME/include/$(uname -s | tr '[:upper:]' '[:lower:]') \\
//       -I<dir-containing-jni-utils.h> {basename}

#include <jni.h>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "jni-utils.h"

#if defined(__GNUC__) || defined(__clang__)
#  pragma GCC diagnostic ignored "-Wunused-variable"
#endif
"""


def generate_test_file(parsed: ParsedFile, source_name: str) -> str:
    """Generate a compile-time type-check file for helpers used by *source_name*.

    Each function's extract_* and make_* calls are emitted inside ``if (false)``
    blocks so the compiler verifies every call's types without executing anything.
    """
    basename = source_name.replace(".kt", "_jni_test.gen.cpp")
    lines: list[str] = [_TEST_FILE_HEADER.format(source=source_name, basename=basename)]

    fn_name = f"_compile_check_{parsed.class_name}"
    lines.append(f"static void {fn_name}(JNIEnv* env) {{")

    for func in parsed.functions:
        lines.append(f"    // {func.name}")
        lines.append("    if (false) {")

        for p in func.params:
            info = map_param_type(p.kotlin_type)
            if info.convert is None:
                continue
            zero = _JNI_ZERO.get(info.jni_type, "0")
            var = _cpp_var_name(p, info)
            expr = info.convert.format(env="env", var=p.name)
            lines.append(f"        {info.jni_type} {p.name} = {zero};")
            lines.append(f"        {info.cpp_type} {var} = {expr};")

        base_rt = func.return_type.rstrip("?").strip() if func.return_type else None
        entry = _MAKE_HELPER_MAP.get(base_rt or "")
        if entry:
            make_fn, cpp_type = entry
            lines.append(f"        {cpp_type} _ret_val{{}};")
            lines.append(f"        jobject _ret = {make_fn}(env, _ret_val);")

        lines.append("    }")

    lines.append("}")
    lines.append("")
    lines.append("int main() { return 0; }")
    lines.append("")
    return "\n".join(lines)


def test_output_basename(parsed: ParsedFile, qualified: bool) -> str:
    if qualified and parsed.package:
        prefix = parsed.package.replace(".", "_") + "_"
        return f"{prefix}{parsed.class_name}_jni_test.gen.cpp"
    return f"{parsed.class_name}_jni_test.gen.cpp"


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def collect_kotlin_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source] if source.suffix == ".kt" else []
    return sorted(source.rglob("*.kt"))


def output_basename(parsed: ParsedFile, qualified: bool) -> str:
    """Output file name for a parsed source.

    When two classes share a simple name (e.g. ``com.a.Foo`` and ``com.b.Foo``)
    the name is package-qualified to avoid silently overwriting one with the
    other; otherwise the short ``<Class>_jni.gen.cpp`` form is used.
    """
    if qualified and parsed.package:
        prefix = parsed.package.replace(".", "_") + "_"
        return f"{prefix}{parsed.class_name}_jni.gen.cpp"
    return f"{parsed.class_name}_jni.gen.cpp"


# Exit codes
EXIT_OK = 0
EXIT_USAGE = 1  # no files / nothing to generate / bad path
EXIT_PARSE = 2  # unrecognized type or parse failure
EXIT_DRIFT = 3  # --check found out-of-date / missing output


def load_type_map(path: Path) -> None:
    """Merge custom Kotlin→JNI type mappings from a JSON file into the module-level maps.

    JSON schema (all sections optional):
    {
      "types": {
        "MyHandle": {
          "jni_type": "jlong",
          "cpp_type": "void*",
          "convert": "reinterpret_cast<void*>({var})",
          "is_handle": true
        }
      },
      "returns": {
        "MyHandle": ["jlong", "0"]
      },
      "make_helpers": {
        "MyList": ["make_my_list", "std::vector<MyItem>"]
      }
    }

    Custom types override built-ins if the same key is present in both.
    """
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load type map '{path}': {exc}") from exc

    for kotlin_type, info in data.get("types", {}).items():
        TYPE_MAP[kotlin_type] = TypeInfo(
            jni_type=info["jni_type"],
            cpp_type=info["cpp_type"],
            convert=info.get("convert"),
            is_handle=bool(info.get("is_handle", False)),
            is_string=bool(info.get("is_string", False)),
        )

    for kotlin_type, pair in data.get("returns", {}).items():
        RETURN_MAP[kotlin_type] = (pair[0], pair[1])

    for kotlin_type, pair in data.get("make_helpers", {}).items():
        _MAKE_HELPER_MAP[kotlin_type] = (pair[0], pair[1])


# --------------------------------------------------------------------------- #
# iOS / Kotlin-Native cinterop skeleton generator
# --------------------------------------------------------------------------- #

_RE_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _camel_to_snake(name: str) -> str:
    return _RE_CAMEL.sub("_", name).lower()


def _kotlin_to_c_param(kotlin_type: str, param_name: str) -> str:
    """Return a C parameter declaration for a Kotlin type."""
    base = kotlin_type.rstrip("?").strip()
    simple = {
        "Int": f"int32_t {param_name}",
        "Long": f"int64_t {param_name}",
        "Float": f"float {param_name}",
        "Double": f"double {param_name}",
        "Boolean": f"bool {param_name}",
        "Short": f"int16_t {param_name}",
        "Byte": f"int8_t {param_name}",
        "String": f"const char* {param_name}",
    }
    if base in simple:
        return simple[base]
    array_elem = {
        "ByteArray": "const uint8_t*",
        "IntArray": "const int32_t*",
        "FloatArray": "const float*",
        "LongArray": "const int64_t*",
        "DoubleArray": "const double*",
        "BooleanArray": "const bool*",
        "ShortArray": "const int16_t*",
    }
    if base in array_elem:
        return f"{array_elem[base]} {param_name}, int32_t {param_name}_len"
    return f"void* {param_name} /* TODO: {base} — define a C struct */"


def _kotlin_return_to_c(kotlin_type: str | None) -> str:
    """Return the C return type for a Kotlin return type."""
    if kotlin_type is None:
        return "void"
    base = kotlin_type.rstrip("?").strip()
    simple = {
        "Int": "int32_t",
        "Long": "int64_t",
        "Float": "float",
        "Double": "double",
        "Boolean": "bool",
        "Short": "int16_t",
        "Byte": "int8_t",
        "String": "const char*",
    }
    if base in simple:
        return simple[base]
    return f"void* /* TODO: {base} — return via out-param or opaque handle */"


def generate_ios_cinterop_files(
    parsed_files: list[tuple[Path, ParsedFile]], output_dir: Path
) -> None:
    """Write a Kotlin/Native .def file + C header skeleton for each parsed file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    include_dir = output_dir / "include"
    include_dir.mkdir(exist_ok=True)

    for kt, parsed in parsed_files:
        cls = parsed.class_name
        prefix = _camel_to_snake(cls)

        # --- C header ---
        header_lines = [
            "// cinterop header skeleton — generated by jni-binding-generator.py",
            f"// Source: {kt.name}  |  class {cls}",
            "// Replace placeholder function names with your actual C API.",
            "#pragma once",
            "#include <stdint.h>",
            "#include <stdbool.h>",
            "",
        ]
        for func in parsed.functions:
            fn_c = f"{prefix}_{_camel_to_snake(func.name)}"
            ret_c = _kotlin_return_to_c(func.return_type)
            params = [
                _kotlin_to_c_param(p.kotlin_type, _camel_to_snake(p.name)) for p in func.params
            ]
            params_str = ", ".join(params) if params else "void"
            header_lines.append(f"{ret_c} {fn_c}({params_str});")

        header_content = "\n".join(header_lines) + "\n"
        header_path = include_dir / f"{cls}.h"
        header_existing = header_path.read_text(encoding="utf-8") if header_path.exists() else None
        if header_existing != header_content:
            header_path.write_text(header_content, encoding="utf-8")

        # --- .def file ---
        def_lines = [
            "# Kotlin/Native cinterop definition — generated by jni-binding-generator.py",
            f"# Source class: {parsed.package}.{cls}",
            "#",
            "# Steps:",
            f"#  1. Rename functions in include/{cls}.h to match your actual C API.",
            "#  2. Point staticLibraries/libraryPaths at your compiled native library.",
            "#  3. In shared/build.gradle.kts (iosMain):",
            f"#       cinterops {{ val {prefix} by creating {{",
            f'#         defFile("src/nativeInterop/cinterop/{cls}.def")',
            "#       } }",
            "",
            f"headers = include/{cls}.h",
            "headerFilter = include/**",
            "",
            f"# staticLibraries = lib{prefix}.a",
            "# libraryPaths = /path/to/your/lib",
        ]
        def_content = "\n".join(def_lines) + "\n"
        def_path = output_dir / f"{cls}.def"
        def_existing = def_path.read_text(encoding="utf-8") if def_path.exists() else None
        if def_existing != def_content:
            def_path.write_text(def_content, encoding="utf-8")

        print(
            f"[cinterop] {kt.name}  ->  {def_path.name}  +  include/{cls}.h"
            f"  ({len(parsed.functions)} fn)"
        )


def run(
    kotlin_source: Path,
    output_dir: Path,
    dry_run: bool,
    check: bool,
    generate_tests: bool = False,
    diff: bool = False,
    verbose: bool = False,
    package_filter: str = "",
) -> int:
    files = collect_kotlin_files(kotlin_source)
    if not files:
        print(f"No .kt files found under {kotlin_source}", file=sys.stderr)
        return EXIT_USAGE

    # Pre-pass: parse every file so we can detect class-name collisions before
    # choosing output names.  A single .kt may yield multiple ParsedFiles when
    # it contains more than one top-level class/object.
    parsed_files: list[tuple[Path, ParsedFile]] = []
    for kt in files:
        try:
            for parsed in parse_kotlin_file(kt):
                if not parsed.functions:
                    continue
                if package_filter and not parsed.package.startswith(package_filter):
                    if verbose:
                        print(f"[skip] {kt} (package {parsed.package!r} filtered)")
                    continue
                parsed_files.append((kt, parsed))
        except ValueError as exc:
            print(f"Error in {kt}: {exc}", file=sys.stderr)
            return EXIT_PARSE

    name_counts: dict = {}
    for _, parsed in parsed_files:
        name_counts[parsed.class_name] = name_counts.get(parsed.class_name, 0) + 1

    generated = 0  # files with external funs (work items)
    written = 0  # files actually written this run
    drifted: list[Path] = []

    for kt, parsed in parsed_files:
        if verbose:
            print(f"[gen] {parsed.class_name} ({len(parsed.functions)} fn)")
            for fn in parsed.functions:
                print(f"      {fn.name}()")
        try:
            content = generate_file(parsed, kt.name)
        except (UnknownTypeError, ValueError) as exc:
            print(f"Error in {kt}: {exc}", file=sys.stderr)
            return EXIT_PARSE

        qualified = name_counts[parsed.class_name] > 1
        out_path = output_dir / output_basename(parsed, qualified)
        existing = out_path.read_text(encoding="utf-8") if out_path.exists() else None
        up_to_date = existing == content
        generated += 1

        if check:
            status = "ok" if up_to_date else ("missing" if existing is None else "DRIFT")
            print(f"[check] {out_path}: {status}")
            if not up_to_date:
                drifted.append(out_path)
        elif diff:
            import difflib

            old_lines = existing.splitlines(keepends=True) if existing else []
            new_lines = content.splitlines(keepends=True)
            delta = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=str(out_path),
                    tofile=str(out_path) + " (new)",
                )
            )
            if delta:
                print(f"--- {out_path}")
                print("".join(delta))
            else:
                print(f"{out_path}: unchanged")
        elif dry_run:
            print(f"{kt}  ->  {out_path}  ({len(parsed.functions)} fn) [dry-run]")
            print(content)
        elif up_to_date:
            print(f"{kt}  ->  {out_path}  (unchanged)")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            written += 1
            print(f"{kt}  ->  {out_path}  ({len(parsed.functions)} fn) [written]")

        if generate_tests and not check and not dry_run:
            test_content = generate_test_file(parsed, kt.name)
            test_path = output_dir / test_output_basename(parsed, qualified)
            test_existing = test_path.read_text(encoding="utf-8") if test_path.exists() else None
            if test_existing != test_content:
                output_dir.mkdir(parents=True, exist_ok=True)
                test_path.write_text(test_content, encoding="utf-8")
                print(f"{kt}  ->  {test_path}  [test written]")
            else:
                print(f"{kt}  ->  {test_path}  (test unchanged)")

    if generated == 0:
        print("No external functions found; nothing generated.", file=sys.stderr)
        return EXIT_USAGE

    if check:
        if drifted:
            print(
                f"\n{len(drifted)} generated file(s) are out of date. "
                f"Run the generator and commit the result.",
                file=sys.stderr,
            )
            return EXIT_DRIFT
        print(f"\nAll {generated} generated file(s) are up to date.")
        return EXIT_OK

    if dry_run:
        return EXIT_OK
    print(f"Done. {written} written, {generated - written} unchanged.")
    return EXIT_OK


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
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify generated files are up to date without writing; "
        "exit 3 on drift (for CI / pre-commit)",
    )
    parser.add_argument(
        "--generate-tests",
        action="store_true",
        help="Also emit a *_jni_test.gen.cpp compile-time type-check file alongside each binding",
    )
    parser.add_argument(
        "--type-map",
        metavar="FILE",
        help="JSON file with custom Kotlin→JNI type mappings to merge before generation",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Print a unified diff of what would change without writing files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-class and per-function progress",
    )
    parser.add_argument(
        "--package-filter",
        metavar="PKG",
        default="",
        help="Only process source files whose package starts with PKG",
    )
    parser.add_argument(
        "--ios-cinterop",
        metavar="DIR",
        help="Also generate a Kotlin/Native cinterop .def + C header skeleton in DIR",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.type_map:
        type_map_path = Path(args.type_map)
        if not type_map_path.exists():
            print(f"Error: --type-map file not found: {type_map_path}", file=sys.stderr)
            return EXIT_USAGE
        try:
            load_type_map(type_map_path)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return EXIT_USAGE
    kotlin_source = Path(args.kotlin_source)
    if not kotlin_source.exists():
        print(f"Error: Kotlin source path does not exist: {kotlin_source}", file=sys.stderr)
        return EXIT_USAGE
    rc = run(
        kotlin_source,
        Path(args.output),
        args.dry_run,
        args.check,
        args.generate_tests,
        args.diff,
        args.verbose,
        args.package_filter,
    )
    if rc != EXIT_OK:
        return rc

    if args.ios_cinterop:
        # Re-collect parsed files (respecting the same package filter) for cinterop output.
        cinterop_files: list[tuple[Path, ParsedFile]] = []
        for kt in collect_kotlin_files(kotlin_source):
            try:
                for parsed in parse_kotlin_file(kt):
                    if not parsed.functions:
                        continue
                    if args.package_filter and not parsed.package.startswith(args.package_filter):
                        continue
                    cinterop_files.append((kt, parsed))
            except ValueError:
                pass
        if cinterop_files:
            generate_ios_cinterop_files(cinterop_files, Path(args.ios_cinterop))

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
