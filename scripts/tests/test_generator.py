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
        self.assertIn(
            "Java_com_example_sample_SampleEngine_nativeLoad(", out
        )
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
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N { external fun f(x: WeirdType): Long }"
        )
        with self.assertRaises(gen.UnknownTypeError) as ctx:
            gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("WeirdType", str(ctx.exception))
        self.assertIn("TYPE_MAP", str(ctx.exception))

    def test_nullable_params_skip_required_guards(self):
        parsed = gen.parse_kotlin_source(
            "package a.b\nclass N {\n"
            "    external fun f(handle: Long?, name: String?): Long\n}"
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
            "package a.b\nclass N {\n"
            "    external fun f(handle: Long, name: String): Long\n}"
        )
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("not initialized", out)
        self.assertIn("is required", out)

    def test_full_file_has_header_and_includes(self):
        content = gen.generate_file(self.parsed, "SampleEngine.kt")
        self.assertIn("AUTO-GENERATED", content)
        self.assertIn('#include <jni.h>', content)
        self.assertIn('#include "jni-utils.h"', content)
        self.assertEqual(content.count('extern "C"'), 4)


if __name__ == "__main__":
    unittest.main()
