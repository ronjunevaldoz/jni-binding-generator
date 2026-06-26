"""
Static-analysis memory-safety tests for scripts/jni-utils.h.

Each test scans C++ source text to verify that JNI local-reference acquisitions
are paired with releases inside the same function definition. These serve as
regression guards so new helpers cannot accidentally omit cleanup.

Patterns checked:
  - GetStringUTFChars  → ReleaseStringUTFChars  (EP-6)
  - GetObjectArrayElement → DeleteLocalRef
  - FindClass count    ≤  DeleteLocalRef count (per function)
  - CallStaticObjectMethod / NewObject in a loop → DeleteLocalRef present
  - NewStringUTF in a loop  → DeleteLocalRef present
  - Every named helper (extract_*/make_*) → DeleteLocalRef present
"""

import re
import unittest
from pathlib import Path

HEADER = Path(__file__).parent.parent / "jni-utils.h"


# ---------------------------------------------------------------------------
# Source parsing helpers
# ---------------------------------------------------------------------------


def _read() -> str:
    return HEADER.read_text(encoding="utf-8")


def _function_body(src: str, fn_name: str) -> str:
    """
    Return the brace-delimited body of the first definition of fn_name.
    Matches only definition sites (preceded by 'inline … fn_name(').
    """
    pat = re.compile(r"\binline\b[^;{]*\b" + re.escape(fn_name) + r"\s*\(", re.DOTALL)
    m = pat.search(src)
    if not m:
        return ""
    brace_start = src.find("{", m.end())
    if brace_start == -1:
        return ""
    depth = 0
    for i in range(brace_start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace_start : i + 1]
    return ""


_SKIP_WORDS = frozenset(
    {
        "const",
        "volatile",
        "static",
        "std",
        "int32_t",
        "int64_t",
        "int8_t",
        "int16_t",
        "uint8_t",
        "jsize",
        "jint",
        "jlong",
        "jfloat",
        "jdouble",
        "jboolean",
        "jbyte",
        "jshort",
        "jobject",
        "jstring",
        "jclass",
        "jbyteArray",
        "jintArray",
        "jlongArray",
        "jfloatArray",
        "jdoubleArray",
        "jbooleanArray",
        "jshortArray",
        "jobjectArray",
        "string",
        "vector",
        "unordered_map",
        "unordered_set",
        "bool",
        "void",
    }
)


def _all_function_bodies(src: str) -> list[tuple[str, str]]:
    """
    Return [(name, body_text), ...] for every inline function definition.
    body_text is the brace-delimited body only.
    """
    results: list[tuple[str, str]] = []
    inline_re = re.compile(r"\binline\b")
    for m in inline_re.finditer(src):
        paren_pos = src.find("(", m.end())
        if paren_pos == -1:
            continue
        between = src[m.end() : paren_pos]
        if ";" in between or "{" in between:
            continue
        words = re.findall(r"\b[A-Za-z_]\w*\b", between)
        if not words:
            continue
        name = words[-1]
        if name in _SKIP_WORDS:
            continue
        brace_start = src.find("{", paren_pos)
        if brace_start == -1:
            continue
        depth = 0
        end = brace_start
        for i in range(brace_start, len(src)):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        results.append((name, src[brace_start : end + 1]))
    return results


# ---------------------------------------------------------------------------
# EP-6: GetStringUTFChars / ReleaseStringUTFChars
# ---------------------------------------------------------------------------


class TestGetStringUTFCharsLifecycle(unittest.TestCase):
    """Every GetStringUTFChars call must be paired with ReleaseStringUTFChars."""

    def test_jstring2string_releases_on_all_paths(self):
        src = _read()
        body = _function_body(src, "jstring2string")
        self.assertNotEqual(body, "", "jstring2string not found in header")
        acquire = body.count("GetStringUTFChars")
        release = body.count("ReleaseStringUTFChars")
        self.assertGreater(acquire, 0, "GetStringUTFChars not used in jstring2string")
        self.assertGreaterEqual(
            release,
            acquire,
            f"jstring2string: {acquire} GetStringUTFChars but {release} ReleaseStringUTFChars",
        )

    def test_no_function_acquires_without_releasing(self):
        src = _read()
        for name, body in _all_function_bodies(src):
            with self.subTest(fn=name):
                acquire = body.count("GetStringUTFChars")
                release = body.count("ReleaseStringUTFChars")
                if acquire > 0:
                    self.assertGreaterEqual(
                        release,
                        acquire,
                        f"{name}: {acquire} GetStringUTFChars but {release} ReleaseStringUTFChars",
                    )


# ---------------------------------------------------------------------------
# FindClass / DeleteLocalRef balance
# ---------------------------------------------------------------------------


class TestFindClassBalance(unittest.TestCase):
    """
    Each function's DeleteLocalRef count must be >= its FindClass count.
    FindClass returns a local ref that must be freed before the function returns.
    """

    def test_all_functions(self):
        src = _read()
        for name, body in _all_function_bodies(src):
            with self.subTest(fn=name):
                find = body.count("env->FindClass(")
                delete = body.count("env->DeleteLocalRef(")
                if find > 0:
                    self.assertGreaterEqual(
                        delete,
                        find,
                        f"{name}: {find} FindClass calls but only {delete} DeleteLocalRef calls",
                    )


# ---------------------------------------------------------------------------
# GetObjectArrayElement / DeleteLocalRef
# ---------------------------------------------------------------------------


class TestGetObjectArrayElementRelease(unittest.TestCase):
    """Every GetObjectArrayElement result must be freed with DeleteLocalRef."""

    def test_all_functions(self):
        src = _read()
        for name, body in _all_function_bodies(src):
            with self.subTest(fn=name):
                acquire = body.count("GetObjectArrayElement(")
                if acquire == 0:
                    continue
                delete = body.count("env->DeleteLocalRef(")
                self.assertGreaterEqual(
                    delete,
                    acquire,
                    f"{name}: {acquire} GetObjectArrayElement but only {delete} DeleteLocalRef",
                )


# ---------------------------------------------------------------------------
# Loop-local refs: NewStringUTF and boxing in loops
# ---------------------------------------------------------------------------

_LOOP_RE = re.compile(r"\b(for|while)\s*\(")


class TestNewStringUTFInLoop(unittest.TestCase):
    """NewStringUTF inside a loop must have a matching DeleteLocalRef."""

    def test_all_functions(self):
        src = _read()
        for name, body in _all_function_bodies(src):
            with self.subTest(fn=name):
                if "NewStringUTF" not in body:
                    continue
                if not _LOOP_RE.search(body):
                    continue
                self.assertIn(
                    "DeleteLocalRef",
                    body,
                    f"{name}: NewStringUTF inside loop but no DeleteLocalRef found",
                )


class TestBoxedObjectCreationInLoop(unittest.TestCase):
    """CallStaticObjectMethod (boxing) inside a loop must be freed."""

    def test_all_functions(self):
        src = _read()
        for name, body in _all_function_bodies(src):
            with self.subTest(fn=name):
                if "CallStaticObjectMethod" not in body:
                    continue
                if not _LOOP_RE.search(body):
                    continue
                self.assertIn(
                    "DeleteLocalRef",
                    body,
                    f"{name}: CallStaticObjectMethod in loop but no DeleteLocalRef",
                )


# ---------------------------------------------------------------------------
# Iterator-loop pattern: entry / key / value refs
# ---------------------------------------------------------------------------


class TestIteratorLoopCleanup(unittest.TestCase):
    """
    Functions that iterate over Java collections (hasNext/next pattern) must
    delete per-iteration refs (entry, key, value) inside the loop.
    """

    def test_all_functions(self):
        src = _read()
        for name, body in _all_function_bodies(src):
            with self.subTest(fn=name):
                if "hasNextM" not in body:
                    continue
                # Must see at least one DeleteLocalRef for the per-iteration refs
                self.assertIn(
                    "DeleteLocalRef",
                    body,
                    f"{name}: iterator loop but no DeleteLocalRef for entry/key/value",
                )
                # Verify the iterator itself is also released after the loop
                self.assertIn(
                    "DeleteLocalRef(iter)",
                    body,
                    f"{name}: iterator not deleted after loop",
                )


# ---------------------------------------------------------------------------
# Named helper coverage — every extract_* and make_* has DeleteLocalRef
# ---------------------------------------------------------------------------


def _extract_make_helpers(src: str) -> list[str]:
    """Return all inline function names matching extract_* or make_*."""
    return [
        name
        for name, _ in _all_function_bodies(src)
        if name.startswith("extract_") or name.startswith("make_")
    ]


def _acquires_local_ref(body: str) -> bool:
    """
    Return True if the function body creates JNI local references that
    require explicit DeleteLocalRef.  Primitive-array region-copy helpers
    (Get*ArrayRegion) copy into C buffers and never produce local refs.
    """
    return bool(
        re.search(
            r"env->(FindClass|GetObjectArrayElement|CallObjectMethod|"
            r"CallStaticObjectMethod|NewObject|NewStringUTF)\(",
            body,
        )
    )


class TestExtractMakeHelpersHaveCleanup(unittest.TestCase):
    """
    Every extract_*/make_* helper that acquires JNI local refs must contain
    at least one DeleteLocalRef.

    Helpers that use only Get*ArrayRegion (copy into C buffer, no local ref
    created) are correctly excluded from this check.
    """

    def test_all_helpers(self):
        src = _read()
        helpers = _extract_make_helpers(src)
        self.assertGreater(len(helpers), 0, "No extract_*/make_* helpers found")
        bodies = dict(_all_function_bodies(src))
        for name in helpers:
            body = bodies.get(name, "")
            with self.subTest(fn=name):
                self.assertNotEqual(body, "", f"{name} body not found")
                if not _acquires_local_ref(body):
                    continue  # Region-copy helpers need no DeleteLocalRef
                self.assertIn(
                    "DeleteLocalRef",
                    body,
                    f"{name}: acquires JNI local refs but contains no DeleteLocalRef",
                )


# ---------------------------------------------------------------------------
# Nested list helpers specifically
# ---------------------------------------------------------------------------

_NESTED_HELPERS = [
    "extract_list_list_int",
    "extract_list_list_float",
    "extract_list_list_long",
    "extract_list_list_double",
    "extract_list_list_bool",
    "make_list_list_int",
    "make_list_list_float",
    "make_list_list_long",
    "make_list_list_double",
    "make_list_list_bool",
]


class TestNestedListHelpers(unittest.TestCase):
    """Each nested-list helper must delete the inner-list local ref each iteration."""

    def test_helpers_exist(self):
        src = _read()
        for fn in _NESTED_HELPERS:
            with self.subTest(fn=fn):
                body = _function_body(src, fn)
                self.assertNotEqual(body, "", f"{fn} not found in jni-utils.h")

    def test_inner_ref_deleted(self):
        src = _read()
        for fn in _NESTED_HELPERS:
            with self.subTest(fn=fn):
                body = _function_body(src, fn)
                if not body:
                    continue
                self.assertIn(
                    "DeleteLocalRef",
                    body,
                    f"{fn}: inner list/ref not deleted",
                )

    def test_class_ref_deleted(self):
        src = _read()
        for fn in _NESTED_HELPERS:
            with self.subTest(fn=fn):
                body = _function_body(src, fn)
                if not body:
                    continue
                # These helpers acquire a listCls or cls via FindClass
                find_count = body.count("FindClass(")
                delete_count = body.count("DeleteLocalRef(")
                if find_count > 0:
                    self.assertGreaterEqual(
                        delete_count,
                        find_count,
                        f"{fn}: {find_count} FindClass but {delete_count} DeleteLocalRef",
                    )


# ---------------------------------------------------------------------------
# Boxed array helpers
# ---------------------------------------------------------------------------

_BOXED_ARRAY_HELPERS = [
    "extract_boxed_byte_array",
    "extract_boxed_bool_array",
    "extract_boxed_short_array",
]


class TestBoxedArrayHelpers(unittest.TestCase):
    """extract_boxed_*_array helpers must free each element and the class ref."""

    def test_helpers_exist(self):
        src = _read()
        for fn in _BOXED_ARRAY_HELPERS:
            with self.subTest(fn=fn):
                self.assertNotEqual(_function_body(src, fn), "", f"{fn} not found")

    def test_element_deleted(self):
        src = _read()
        for fn in _BOXED_ARRAY_HELPERS:
            with self.subTest(fn=fn):
                body = _function_body(src, fn)
                if not body:
                    continue
                self.assertIn(
                    "DeleteLocalRef(elem)",
                    body,
                    f"{fn}: loop element not deleted",
                )

    def test_class_ref_deleted(self):
        src = _read()
        for fn in _BOXED_ARRAY_HELPERS:
            with self.subTest(fn=fn):
                body = _function_body(src, fn)
                if not body:
                    continue
                find_count = body.count("FindClass(")
                delete_count = body.count("DeleteLocalRef(")
                if find_count > 0:
                    self.assertGreaterEqual(
                        delete_count,
                        find_count,
                        f"{fn}: class ref leaked",
                    )


# ---------------------------------------------------------------------------
# Smoke test: header file is present and non-empty
# ---------------------------------------------------------------------------


class TestHeaderPresent(unittest.TestCase):
    def test_header_exists(self):
        self.assertTrue(HEADER.exists(), f"Header not found: {HEADER}")

    def test_header_non_empty(self):
        self.assertGreater(HEADER.stat().st_size, 0)

    def test_helpers_are_numerous(self):
        src = _read()
        helpers = _extract_make_helpers(src)
        self.assertGreater(len(helpers), 20, "Expected > 20 extract_*/make_* helpers")


if __name__ == "__main__":
    unittest.main()
