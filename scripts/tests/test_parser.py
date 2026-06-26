"""Tests for the Kotlin parser and JNI name mangling."""

import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gen = importlib.import_module("jni-binding-generator")


SIMPLE = """
package com.example.sample

class SampleEngine {
    external fun nativeLoad(modelPath: String, threads: Int): Long
    external fun nativeRelease(handle: Long)
}
"""

MULTILINE = """
package com.example.demo

object NativeBridge {
    external fun nativeProcess(
        handle: Long,
        input: String,
        timeout: Int = 30,
        temperature: Float,
    ): ByteArray?

    external fun nativeTokenizeBatch(
        handle: Long,
        prompts: Array<String>,
        addBos: Boolean,
    ): IntArray
}
"""


class TestKotlinFunctionParser(unittest.TestCase):
    def test_package_and_class(self):
        parsed = gen.parse_kotlin_source(SIMPLE)
        self.assertEqual(parsed.package, "com.example.sample")
        self.assertEqual(parsed.class_name, "SampleEngine")
        self.assertFalse(parsed.is_static)

    def test_object_is_static(self):
        parsed = gen.parse_kotlin_source(MULTILINE)
        self.assertEqual(parsed.class_name, "NativeBridge")
        self.assertTrue(parsed.is_static)

    def test_parse_simple_function(self):
        parsed = gen.parse_kotlin_source(SIMPLE)
        load = parsed.functions[0]
        self.assertEqual(load.name, "nativeLoad")
        self.assertEqual([p.name for p in load.params], ["modelPath", "threads"])
        self.assertEqual([p.kotlin_type for p in load.params], ["String", "Int"])
        self.assertEqual(load.return_type, "Long")

    def test_parse_void_function(self):
        parsed = gen.parse_kotlin_source(SIMPLE)
        release = parsed.functions[1]
        self.assertEqual(release.name, "nativeRelease")
        self.assertEqual(release.return_type, None)
        self.assertEqual(len(release.params), 1)

    def test_parse_multiline_with_default_and_nullable(self):
        parsed = gen.parse_kotlin_source(MULTILINE)
        process = parsed.functions[0]
        self.assertEqual(
            [p.kotlin_type for p in process.params],
            ["Long", "String", "Int", "Float"],
        )
        self.assertEqual(process.params[2].name, "timeout")  # default value stripped
        self.assertEqual(process.return_type, "ByteArray?")

    def test_parse_generic_array_param(self):
        parsed = gen.parse_kotlin_source(MULTILINE)
        batch = parsed.functions[1]
        self.assertEqual(batch.params[1].kotlin_type, "Array<String>")
        self.assertEqual(batch.params[2].kotlin_type, "Boolean")
        self.assertEqual(batch.return_type, "IntArray")


class TestMangling(unittest.TestCase):
    def test_basic_name(self):
        name = gen.jni_function_name("com.example.sample", "SampleEngine", "nativeLoad")
        self.assertEqual(name, "Java_com_example_sample_SampleEngine_nativeLoad")

    def test_underscore_in_method(self):
        name = gen.jni_function_name("com.example", "Foo", "native_load")
        self.assertEqual(name, "Java_com_example_Foo_native_1load")

    def test_no_package(self):
        name = gen.jni_function_name("", "Foo", "bar")
        self.assertEqual(name, "Java_Foo_bar")


if __name__ == "__main__":
    unittest.main()
