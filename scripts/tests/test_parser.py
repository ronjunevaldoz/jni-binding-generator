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


class TestUnsupportedConstructs(unittest.TestCase):
    def test_suspend_fun_raises(self):
        with self.assertRaises(gen.UnknownTypeError) as ctx:
            gen.parse_kotlin_source("package a\nclass N { external suspend fun f(x: Int): Long }")
        self.assertIn("suspend", str(ctx.exception))

    def test_extension_fun_raises(self):
        with self.assertRaises(gen.UnknownTypeError) as ctx:
            gen.parse_kotlin_source("package a\nclass N { external fun String.foo(): Int }")
        self.assertIn("Extension", str(ctx.exception))

    def test_vararg_raises(self):
        with self.assertRaises(gen.UnknownTypeError) as ctx:
            gen.parse_kotlin_source(
                "package a\nclass N { external fun f(vararg items: String): Int }"
            )
        self.assertIn("vararg", str(ctx.exception))

    def test_function_type_param_raises(self):
        with self.assertRaises(gen.UnknownTypeError) as ctx:
            gen.parse_kotlin_source(
                "package a\nclass N { external fun f(cb: (Int) -> String): Long }"
            )
        self.assertIn("function-type", str(ctx.exception))


class TestNestedClass(unittest.TestCase):
    def test_nested_class_jni_name(self):
        parsed = gen.parse_kotlin_source(
            "package com.example\nclass Outer { class Inner { external fun f(x: Int): Long } }"
        )
        # class_name stores the Kotlin $ separator; mangle() converts it to _00024.
        self.assertEqual(parsed.class_name, "Outer$Inner")
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("Java_com_example_Outer_00024Inner_f", out)

    def test_dollar_sign_mangled_in_jni_name(self):
        self.assertEqual(gen.mangle("Outer$Inner"), "Outer_00024Inner")


class TestJvmName(unittest.TestCase):
    def test_jvm_name_overrides_kotlin_name(self):
        parsed = gen.parse_kotlin_source(
            'package a\nclass N {\n  @JvmName("bar")\n  external fun foo(x: Int): Long\n}'
        )
        self.assertEqual(parsed.functions[0].name, "bar")
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("Java_a_N_bar(", out)
        self.assertNotIn("Java_a_N_foo", out)


class TestTopLevelFun(unittest.TestCase):
    def test_top_level_uses_filename_kt(self):
        parsed = gen.parse_kotlin_source(
            "package com.example\nexternal fun nativeFoo(x: Int): Long",
            filename="Utils.kt",
        )
        self.assertEqual(parsed.class_name, "UtilsKt")
        self.assertTrue(parsed.is_static)
        out = gen.generate_function(parsed, parsed.functions[0])
        self.assertIn("Java_com_example_UtilsKt_nativeFoo", out)
        self.assertIn("jclass clazz", out)

    def test_top_level_no_filename_falls_back(self):
        parsed = gen.parse_kotlin_source("package a\nexternal fun foo(x: Int): Long")
        self.assertEqual(parsed.class_name, "Native")


class TestMultiClass(unittest.TestCase):
    _SOURCE = """
package com.example

class Alpha {
    external fun doAlpha(x: Int): Long
}

class Beta {
    external fun doBeta(s: String): Int
}
"""

    def test_two_classes_produce_two_parsed_files(self):
        results = gen.parse_kotlin_source_multi(self._SOURCE)
        self.assertEqual(len(results), 2)
        names = {r.class_name for r in results}
        self.assertEqual(names, {"Alpha", "Beta"})

    def test_each_class_has_its_own_functions(self):
        results = gen.parse_kotlin_source_multi(self._SOURCE)
        by_class = {r.class_name: r for r in results}
        self.assertEqual([f.name for f in by_class["Alpha"].functions], ["doAlpha"])
        self.assertEqual([f.name for f in by_class["Beta"].functions], ["doBeta"])

    def test_package_propagated_to_each_class(self):
        results = gen.parse_kotlin_source_multi(self._SOURCE)
        for r in results:
            self.assertEqual(r.package, "com.example")

    def test_single_class_fast_path(self):
        results = gen.parse_kotlin_source_multi(
            "package a\nclass Solo { external fun f(x: Int): Long }"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].class_name, "Solo")


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
