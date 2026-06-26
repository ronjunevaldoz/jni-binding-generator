"""Tests for C++ JNI code generation."""

import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gen = importlib.import_module("jni-binding-generator")


SOURCE = """
package com.example.sample

class SampleEngine {
    external fun nativeLoad(modelPath: String, threads: Int): Long
    external fun nativeProcess(handle: Long, input: String, timeout: Int): ByteArray?
    external fun nativeTokenizeBatch(handle: Long, prompts: Array<String>, addBos: Boolean): IntArray
    external fun nativeRelease(handle: Long)
}
"""


class TestGeneration(unittest.TestCase):
    def setUp(self):
        self.parsed = gen.parse_kotlin_source(SOURCE)
        self.by_name = {f.name: f for f in self.parsed.functions}

    def gen_fn(self, name):
        return gen.generate_function(self.parsed, self.by_name[name])

    def test_signature_and_marshalling(self):
        out = self.gen_fn("nativeLoad")
        self.assertIn("Java_com_example_sample_SampleEngine_nativeLoad(", out)
        self.assertIn("JNIEnv* env", out)
        self.assertIn("jobject thiz", out)  # instance method
        self.assertIn("std::string modelPath_val = jstring2string(env, modelPath);", out)
        self.assertIn("int32_t threads_val = static_cast<int32_t>(threads);", out)
        self.assertTrue(out.startswith('extern "C" JNIEXPORT jlong JNICALL'))

    def test_handle_and_string_error_checks(self):
        out = self.gen_fn("nativeProcess")
        self.assertIn("void* handle_ptr = reinterpret_cast<void*>(handle);", out)
        self.assertIn("if (!handle_ptr) {", out)
        self.assertIn("nativeProcess: handle not initialized", out)
        self.assertIn("if (input_val.empty()) {", out)
        self.assertIn("nativeProcess: input is required", out)
        # nullable ByteArray? return -> jbyteArray, error returns nullptr
        self.assertIn("JNIEXPORT jbyteArray JNICALL", out)
        self.assertIn("return nullptr;", out)

    def test_array_and_boolean_marshalling(self):
        out = self.gen_fn("nativeTokenizeBatch")
        self.assertIn(
            "std::vector<std::string> prompts_val = extract_string_array(env, prompts);",
            out,
        )
        self.assertIn("bool addBos_val = (addBos == JNI_TRUE);", out)
        self.assertIn("JNIEXPORT jintArray JNICALL", out)

    def test_void_return(self):
        out = self.gen_fn("nativeRelease")
        self.assertIn("JNIEXPORT void JNICALL", out)
        # void error path is a bare "return;"
        self.assertIn("return;", out)
        self.assertNotIn("return ;", out)

    def test_static_object_receiver(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nobject N { external fun nativeRelease(handle: Long) }"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("jclass clazz", out)
        self.assertNotIn("jobject thiz", out)

    def test_unknown_type_is_actionable(self):
        # lowercase-start type: not treated as enum, must raise UnknownTypeError
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N { external fun f(x: weird_type): Long }"
        )
        with self.assertRaises(gen.UnknownTypeError) as ctx:
            gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("weird_type", str(ctx.exception))
        self.assertIn("TYPE_MAP", str(ctx.exception))

    def test_enum_type_maps_to_ordinal(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N { external fun f(x: Direction): Long }"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("enum_ordinal", out)
        self.assertIn("int32_t", out)

    def test_nullable_params_skip_required_guards(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N {\n    external fun f(handle: Long?, name: String?): Long\n}"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        # Nullable params are still marshalled...
        self.assertIn("void* handle_ptr = reinterpret_cast<void*>(handle);", out)
        self.assertIn("std::string name_val = jstring2string(env, name);", out)
        # ...but get no required-value guard.
        self.assertNotIn("not initialized", out)
        self.assertNotIn("is required", out)

    def test_non_nullable_still_guarded(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N {\n    external fun f(handle: Long, name: String): Long\n}"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("not initialized", out)
        self.assertIn("is required", out)

    def test_double_array_and_bool_array(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N {\n"
            "    external fun f(data: DoubleArray, flags: BooleanArray): ShortArray\n}"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("jdoubleArray data", out)
        self.assertIn("extract_double_array(env, data)", out)
        self.assertIn("jbooleanArray flags", out)
        self.assertIn("extract_bool_array(env, flags)", out)
        self.assertIn("JNIEXPORT jshortArray JNICALL", out)

    def test_short_array(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N { external fun f(samples: ShortArray): ShortArray }"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("jshortArray samples", out)
        self.assertIn("extract_short_array(env, samples)", out)
        self.assertIn("JNIEXPORT jshortArray JNICALL", out)

    def test_list_bool_return_hints_make_helper(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N { external fun f(h: Long): List<Boolean> }"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("make_list_bool", out)

    def test_list_byte_return_hints_make_helper(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N { external fun f(h: Long): List<Byte> }"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("make_list_byte", out)

    def test_map_int_string_return_hints_make_helper(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N { external fun f(h: Long): Map<Int, String> }"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("make_map_int_string", out)

    def test_generate_test_file_structure(self):
        content = gen.generate_test_file(self.parsed, "SampleEngine.kt")
        self.assertIn("AUTO-GENERATED", content)
        self.assertIn("#include <jni.h>", content)
        self.assertIn('#include "jni-utils.h"', content)
        self.assertIn("if (false)", content)
        self.assertIn("int main()", content)
        self.assertIn("_compile_check_SampleEngine", content)

    def test_generate_test_file_covers_param_helpers(self):
        content = gen.generate_test_file(self.parsed, "SampleEngine.kt")
        # nativeLoad has String + Int params
        self.assertIn("jstring2string(env, modelPath)", content)
        self.assertIn("static_cast<int32_t>(threads)", content)

    def test_generate_test_file_covers_make_helpers(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N {\n"
            "    external fun f(h: Long): List<String>\n"
            "    external fun g(h: Long): Map<String, Int>\n"
            "    external fun s(h: Long): Set<String>\n"
            "}"
        )
        content = gen.generate_test_file(parsed, "N.kt")
        self.assertIn("make_list_string(env", content)
        self.assertIn("make_map_string_int(env", content)
        self.assertIn("make_set_string(env", content)

    def test_generate_test_file_skips_void(self):
        parsed = gen.parse_kotlin_source("package a.b\nclass N { external fun release(h: Long) }")
        content = gen.generate_test_file(parsed, "N.kt")
        # void functions: param still has Long, no make_* needed
        self.assertIn("if (false)", content)
        self.assertNotIn("make_", content)

    def test_full_file_has_header_and_includes(self):
        content = gen.generate_file(self.parsed, "SampleEngine.kt")
        self.assertIn("AUTO-GENERATED", content)
        self.assertIn("#include <jni.h>", content)
        self.assertIn('#include "jni-utils.h"', content)
        self.assertEqual(content.count('extern "C"'), 4)


class TestNewTypeFamily(unittest.TestCase):
    def _gen(self, kotlin_type: str) -> str:
        parsed = gen.parse_kotlin_source(
            f"package a\nclass N {{ external fun f(x: {kotlin_type}): {kotlin_type} }}"
        )
        return gen.generate_function(parsed, parsed.functions[0])

    def test_list_short_param_and_return(self):
        out = self._gen("List<Short>")
        self.assertIn("extract_list_short(env, x)", out)
        self.assertIn("make_list_short", out)

    def test_set_long_param_and_return(self):
        out = self._gen("Set<Long>")
        self.assertIn("extract_set_long(env, x)", out)
        self.assertIn("make_set_long", out)

    def test_set_float_param_and_return(self):
        out = self._gen("Set<Float>")
        self.assertIn("extract_set_float(env, x)", out)
        self.assertIn("make_set_float", out)

    def test_map_string_long_param_and_return(self):
        out = self._gen("Map<String, Long>")
        self.assertIn("extract_map_string_long(env, x)", out)
        self.assertIn("make_map_string_long", out)

    def test_map_string_float_param_and_return(self):
        out = self._gen("Map<String, Float>")
        self.assertIn("extract_map_string_float(env, x)", out)
        self.assertIn("make_map_string_float", out)

    def test_map_string_bool_param_and_return(self):
        out = self._gen("Map<String, Boolean>")
        self.assertIn("extract_map_string_bool(env, x)", out)
        self.assertIn("make_map_string_bool", out)


class TestNestedListLongDoubleBoolean(unittest.TestCase):
    def _gen(self, kt_type: str) -> str:
        parsed = gen.parse_kotlin_source(
            f"package a\nclass N {{\n    external fun f(x: {kt_type}): {kt_type}\n}}"
        )
        return gen.generate_file(parsed, "N.kt")

    def test_list_list_long_param(self):
        out = self._gen("List<List<Long>>")
        self.assertIn("extract_list_list_long(env, x)", out)

    def test_list_list_long_return(self):
        out = self._gen("List<List<Long>>")
        self.assertIn("make_list_list_long", out)

    def test_list_list_double_param(self):
        out = self._gen("List<List<Double>>")
        self.assertIn("extract_list_list_double(env, x)", out)

    def test_list_list_double_return(self):
        out = self._gen("List<List<Double>>")
        self.assertIn("make_list_list_double", out)

    def test_list_list_bool_param(self):
        out = self._gen("List<List<Boolean>>")
        self.assertIn("extract_list_list_bool(env, x)", out)

    def test_list_list_bool_return(self):
        out = self._gen("List<List<Boolean>>")
        self.assertIn("make_list_list_bool", out)


if __name__ == "__main__":
    unittest.main()
