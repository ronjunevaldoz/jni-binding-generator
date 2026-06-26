from __future__ import annotations

import re
from pathlib import Path

from _models import ExternalFunction, Param, ParsedFile
from _types import UnknownTypeError

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

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


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
        # Use the *last* @JvmName match in the window — earlier ones belong to prior
        # functions.  Discard even the last match if another "external fun" sits between
        # the annotation and the current position (meaning the annotation is for a prior
        # function that has no @JvmName of its own).
        lookahead = source[max(0, m.start() - 300) : m.start()]
        jvm_name_match = None
        for candidate in _JVM_NAME_RE.finditer(lookahead):
            if not re.search(r"\bexternal\s+fun\b", lookahead[candidate.end() :]):
                jvm_name_match = candidate
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
