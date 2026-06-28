"""Tests for the C-header → Kotlin stub reverse generator."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib

gen = importlib.import_module("jni-binding-generator")

# ─── helpers ──────────────────────────────────────────────────────────────────


def parse(source: str):
    return gen.parse_c_header(source)


def stub(source: str, pkg: str = "com.example", obj: str = "MyLib") -> str:
    return gen.generate_kotlin_stubs(source, "test.h", package=pkg, object_name=obj)


# ─── Type mapping ─────────────────────────────────────────────────────────────


class TestReturnTypeMapping(unittest.TestCase):
    def _ret(self, c_decl: str) -> str:
        funs = parse(c_decl)
        self.assertEqual(len(funs), 1)
        return funs[0].return_type

    def test_void_returns_unit(self):
        self.assertEqual(self._ret("void engine_release(void* h);"), "Unit")

    def test_int32_returns_int(self):
        self.assertEqual(self._ret("int32_t engine_init(void);"), "Int")

    def test_int_returns_int(self):
        self.assertEqual(self._ret("int engine_count(void);"), "Int")

    def test_void_ptr_returns_long(self):
        self.assertEqual(self._ret("void* engine_create(int32_t n);"), "Long")

    def test_space_before_pointer_return_name(self):
        self.assertEqual(self._ret("void *engine_create(int32_t n);"), "Long")

    def test_char_ptr_returns_string(self):
        self.assertEqual(self._ret("const char* engine_version(void);"), "String")

    def test_char_pointer_return_name_with_space(self):
        self.assertEqual(self._ret("const char *engine_version(void);"), "String")

    def test_float_ptr_return_is_long_handle(self):
        # Returned pointer is an opaque handle, not FloatArray
        self.assertEqual(self._ret("float* engine_get_buffer(void* h);"), "Long")

    def test_int_ptr_return_is_long_handle(self):
        self.assertEqual(self._ret("int32_t* engine_get_ids(void* h);"), "Long")

    def test_bool_return(self):
        self.assertEqual(self._ret("bool engine_is_ready(void* h);"), "Boolean")

    def test_float_return(self):
        self.assertEqual(self._ret("float engine_score(void* h);"), "Float")

    def test_double_return(self):
        self.assertEqual(self._ret("double engine_ratio(void* h);"), "Double")

    def test_int64_return(self):
        self.assertEqual(self._ret("int64_t engine_timestamp(void);"), "Long")

    def test_unknown_struct_ptr_gets_todo(self):
        ret = self._ret("MyStruct* engine_get_config(void* h);")
        self.assertIn("TODO", ret)
        self.assertIn("Long", ret)


class TestParamTypeMapping(unittest.TestCase):
    def _params(self, c_decl: str) -> list:
        funs = parse(c_decl)
        self.assertEqual(len(funs), 1)
        return funs[0].params

    def test_void_ptr_param_is_long(self):
        params = self._params("void engine_process(void* handle);")
        self.assertEqual(params[0].kotlin_type, "Long")

    def test_const_char_ptr_is_string(self):
        params = self._params("void engine_load(const char* path);")
        self.assertEqual(params[0].kotlin_type, "String")

    def test_mutable_char_ptr_is_byte_array(self):
        # char* without const = output buffer, not an input string
        params = self._params("int f(void* ctx, char* buf, int len);")
        self.assertEqual(params[1].kotlin_type, "ByteArray")

    def test_const_char_ptr_stays_string_not_byte_array(self):
        # const char* = input string — must not be confused with output buffer
        params = self._params("void f(const char* msg, char* out, int out_len);")
        self.assertEqual(params[0].kotlin_type, "String")
        self.assertEqual(params[1].kotlin_type, "ByteArray")

    def test_int32_param_is_int(self):
        params = self._params("void engine_set_threads(int32_t n);")
        self.assertEqual(params[0].kotlin_type, "Int")

    def test_float_ptr_param_is_float_array(self):
        params = self._params("void engine_feed(const float* data, int32_t len);")
        self.assertEqual(params[0].kotlin_type, "FloatArray")
        self.assertEqual(params[1].kotlin_type, "Int")

    def test_uint8_ptr_param_is_byte_array(self):
        params = self._params("void engine_write(const uint8_t* buf, int32_t n);")
        self.assertEqual(params[0].kotlin_type, "ByteArray")

    def test_bool_param(self):
        params = self._params("void engine_enable(bool flag);")
        self.assertEqual(params[0].kotlin_type, "Boolean")

    def test_unknown_type_gets_todo(self):
        params = self._params("void engine_config(MyConfig* cfg);")
        self.assertIn("TODO", params[0].kotlin_type)
        self.assertIn("Long", params[0].kotlin_type)

    def test_void_param_list_gives_no_params(self):
        params = self._params("int32_t engine_init(void);")
        self.assertEqual(params, [])

    def test_empty_param_list_gives_no_params(self):
        params = self._params("int32_t engine_count();")
        self.assertEqual(params, [])


# ─── Name conversion ──────────────────────────────────────────────────────────


class TestNameConversion(unittest.TestCase):
    def _name(self, c_decl: str) -> str:
        funs = parse(c_decl)
        self.assertEqual(len(funs), 1)
        return funs[0].name

    def test_snake_to_camel(self):
        self.assertEqual(self._name("void engine_process_batch(void* h);"), "engineProcessBatch")

    def test_already_camel(self):
        self.assertEqual(self._name("void engineProcess(void* h);"), "engineProcess")

    def test_single_word(self):
        self.assertEqual(self._name("void release(void* h);"), "release")

    def _pname(self, c_decl: str, idx: int = 0) -> str:
        funs = parse(c_decl)
        return funs[0].params[idx].name

    def test_param_snake_to_camel(self):
        self.assertEqual(self._pname("void f(int32_t config_path);"), "configPath")

    def test_param_no_name_gets_generated(self):
        # C allows omitting param names in declarations
        name = self._pname("void f(int32_t, const char*);", 0)
        self.assertTrue(name.startswith("param"))

    def test_object_name_from_header(self):
        from _kotlin_gen import _header_to_object_name

        self.assertEqual(_header_to_object_name(Path("my_engine.h")), "MyEngine")
        self.assertEqual(_header_to_object_name(Path("jni-utils.h")), "JniUtils")
        self.assertEqual(_header_to_object_name(Path("libfoo.h")), "Libfoo")
        self.assertEqual(_header_to_object_name(Path("engine.h")), "Engine")


# ─── Source stripping ─────────────────────────────────────────────────────────


class TestSourceStripping(unittest.TestCase):
    def test_line_comments_stripped(self):
        source = "// not a function\nint32_t foo(void);"
        funs = parse(source)
        self.assertEqual(len(funs), 1)
        self.assertEqual(funs[0].name, "foo")

    def test_block_comments_stripped(self):
        source = "/* int32_t fake(void); */\nint32_t real(void);"
        funs = parse(source)
        self.assertEqual(len(funs), 1)
        self.assertEqual(funs[0].name, "real")

    def test_preprocessor_stripped(self):
        source = "#pragma once\n#include <stdint.h>\nint32_t foo(void);"
        funs = parse(source)
        self.assertEqual(len(funs), 1)

    def test_struct_definition_skipped(self):
        source = "struct Config { int x; int y; };\nint32_t init(struct Config* cfg);"
        funs = parse(source)
        self.assertEqual(len(funs), 1)
        self.assertEqual(funs[0].name, "init")

    def test_typedef_function_pointer_skipped(self):
        source = "typedef int (*callback_t)(int);\nint32_t foo(void* h);"
        funs = parse(source)
        # callback_t typedef should not produce a function entry
        names = {f.name for f in funs}
        self.assertIn("foo", names)
        self.assertNotIn("callbackT", names)

    def test_extern_c_block_handled(self):
        source = 'extern "C" {\n    int32_t foo(void* h);\n    void bar(void);\n}'
        funs = parse(source)
        names = {f.name for f in funs}
        self.assertIn("foo", names)
        self.assertIn("bar", names)

    def test_const_qualifier_stripped_from_type(self):
        funs = parse("void engine_load(const char* path);")
        self.assertEqual(funs[0].params[0].kotlin_type, "String")


# ─── Parser edge cases ────────────────────────────────────────────────────────


class TestParserEdgeCases(unittest.TestCase):
    def test_multiple_functions(self):
        source = """
int32_t engine_init(const char* config);
void*   engine_create(int32_t threads);
int32_t engine_process(void* handle, const float* input, int32_t len);
void    engine_destroy(void* handle);
"""
        funs = parse(source)
        self.assertEqual(len(funs), 4)
        names = [f.name for f in funs]
        self.assertEqual(names, ["engineInit", "engineCreate", "engineProcess", "engineDestroy"])

    def test_duplicate_names_deduplicated(self):
        source = "int32_t foo(void);\nint32_t foo(int32_t x);"
        funs = parse(source)
        self.assertEqual(len(funs), 1)

    def test_no_functions_returns_empty(self):
        source = "#pragma once\n#include <stdint.h>\n"
        funs = parse(source)
        self.assertEqual(funs, [])

    def test_multi_param_function(self):
        source = "int32_t foo(void* h, const char* name, int32_t n, float ratio);"
        funs = parse(source)
        self.assertEqual(len(funs[0].params), 4)

    def test_pointer_in_param_name_position(self):
        # "int32_t *out" — * attached to name
        funs = parse("void foo(int32_t *out);")
        self.assertEqual(funs[0].params[0].kotlin_type, "IntArray")


# ─── Full stub generation ─────────────────────────────────────────────────────


class TestGenerateKotlinStubs(unittest.TestCase):
    SOURCE = """
int32_t engine_init(const char* config_path);
void*   engine_create(int32_t threads, bool use_gpu);
void    engine_destroy(void* handle);
"""

    def test_output_has_package(self):
        out = stub(self.SOURCE, pkg="com.example.sdk")
        self.assertIn("package com.example.sdk", out)

    def test_output_has_object(self):
        out = stub(self.SOURCE, obj="NativeEngine")
        self.assertIn("object NativeEngine {", out)

    def test_output_has_external_funs(self):
        out = stub(self.SOURCE)
        self.assertIn("external fun engineInit(", out)
        self.assertIn("external fun engineCreate(", out)
        self.assertIn("external fun engineDestroy(", out)

    def test_void_return_omits_return_type(self):
        out = stub("void engine_destroy(void* handle);")
        self.assertNotIn("): Unit", out)
        self.assertIn("external fun engineDestroy(handle: Long)", out)

    def test_non_unit_return_includes_type(self):
        out = stub("int32_t engine_init(void);")
        self.assertIn("): Int", out)

    def test_empty_source_returns_empty_string(self):
        out = stub("#pragma once\n")
        self.assertEqual(out, "")

    def test_todo_package_when_none_given(self):
        out = gen.generate_kotlin_stubs("int32_t foo(void);", "t.h", package="", object_name="T")
        self.assertIn("TODO", out)

    def test_load_library_hint_present(self):
        out = stub(self.SOURCE, obj="Engine")
        self.assertIn("System.loadLibrary", out)

    def test_file_ends_with_closing_brace(self):
        out = stub(self.SOURCE)
        self.assertTrue(out.rstrip("\n").endswith("}"))


# ─── CLI integration ──────────────────────────────────────────────────────────


class TestKotlinFromHeaderCLI(unittest.TestCase):
    HEADER = "int32_t engine_init(const char* cfg);\nvoid engine_destroy(void* h);\n"

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.header = self.tmp / "engine.h"
        self.header.write_text(self.HEADER, encoding="utf-8")
        self.out = self.tmp / "kotlin"

    def tearDown(self):
        self._td.cleanup()

    def run_gen(self, *extra_args):
        return gen.main(
            ["--kotlin-from-header", str(self.header), "--output", str(self.out)] + list(extra_args)
        )

    def test_generates_kt_file(self):
        rc = self.run_gen()
        self.assertEqual(rc, gen.EXIT_OK)
        out_file = self.out / "Engine.kt"
        self.assertTrue(out_file.exists())
        content = out_file.read_text()
        self.assertIn("external fun engineInit", content)
        self.assertIn("external fun engineDestroy", content)

    def test_dry_run_does_not_write(self):
        rc = self.run_gen("--dry-run")
        self.assertEqual(rc, gen.EXIT_OK)
        self.assertFalse((self.out / "Engine.kt").exists())

    def test_check_detects_missing(self):
        rc = self.run_gen("--check")
        self.assertEqual(rc, gen.EXIT_DRIFT)

    def test_check_passes_when_up_to_date(self):
        self.run_gen()  # write first
        rc = self.run_gen("--check")
        self.assertEqual(rc, gen.EXIT_OK)

    def test_package_flag(self):
        rc = self.run_gen("--kotlin-package", "com.sdk.native")
        self.assertEqual(rc, gen.EXIT_OK)
        content = (self.out / "Engine.kt").read_text()
        self.assertIn("package com.sdk.native", content)

    def test_missing_header_is_usage_error(self):
        rc = gen.main(
            ["--kotlin-from-header", str(self.tmp / "nonexistent.h"), "--output", str(self.out)]
        )
        self.assertEqual(rc, gen.EXIT_USAGE)

    def test_kotlin_source_not_required_in_this_mode(self):
        # Should not crash asking for --kotlin-source
        rc = self.run_gen()
        self.assertEqual(rc, gen.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
