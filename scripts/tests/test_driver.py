"""Tests for the driver: --check drift mode, incremental writes, errors."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gen = importlib.import_module("jni-binding-generator")


SOURCE = """
package com.example.sample

class SampleEngine {
    external fun nativeLoad(modelPath: String, threads: Int): Long
    external fun nativeRelease(handle: Long)
}
"""

BAD_SOURCE = """
package a.b

class N {
    external fun ok(x: Int): Long
    external fun bad(
        y: weird_type,
    ): Long
}
"""


class DriverTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = self.root / "src"
        self.src.mkdir()
        self.out = self.root / "out"
        (self.src / "SampleEngine.kt").write_text(SOURCE, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_gen(self, *extra):
        return gen.main(["--kotlin-source", str(self.src), "--output", str(self.out), *extra])


class TestIncrementalWrites(DriverTestCase):
    def test_first_run_writes(self):
        self.assertEqual(self.run_gen(), gen.EXIT_OK)
        out_file = self.out / "SampleEngine_jni.gen.cpp"
        self.assertTrue(out_file.exists())

    def test_second_run_does_not_touch_file(self):
        self.run_gen()
        out_file = self.out / "SampleEngine_jni.gen.cpp"
        before_mtime = out_file.stat().st_mtime_ns
        before_text = out_file.read_text()
        # Re-run: content identical, file must not be rewritten.
        self.run_gen()
        self.assertEqual(out_file.read_text(), before_text)
        self.assertEqual(out_file.stat().st_mtime_ns, before_mtime)


class TestCheckMode(DriverTestCase):
    def test_check_up_to_date(self):
        self.run_gen()
        self.assertEqual(self.run_gen("--check"), gen.EXIT_OK)

    def test_check_missing_output_is_drift(self):
        # Never generated -> --check should report drift.
        self.assertEqual(self.run_gen("--check"), gen.EXIT_DRIFT)

    def test_check_detects_drift_after_source_change(self):
        self.run_gen()
        # Change the Kotlin source so generated output would differ.
        (self.src / "SampleEngine.kt").write_text(
            SOURCE.replace("threads: Int", "threads: Int, extra: String"),
            encoding="utf-8",
        )
        self.assertEqual(self.run_gen("--check"), gen.EXIT_DRIFT)

    def test_check_does_not_write(self):
        self.run_gen("--check")
        self.assertFalse((self.out / "SampleEngine_jni.gen.cpp").exists())


class TestOutputNaming(DriverTestCase):
    def test_same_class_name_different_packages_no_collision(self):
        multi = self.root / "multi"
        a = multi / "a"
        b = multi / "b"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        (a / "Foo.kt").write_text(
            "package com.a\nclass Foo { external fun nativeX(h: Long) }",
            encoding="utf-8",
        )
        (b / "Foo.kt").write_text(
            "package com.b\nclass Foo { external fun nativeY(h: Long) }",
            encoding="utf-8",
        )
        rc = gen.main(["--kotlin-source", str(multi), "--output", str(self.out)])
        self.assertEqual(rc, gen.EXIT_OK)
        names = sorted(p.name for p in self.out.glob("*.gen.cpp"))
        self.assertEqual(names, ["com_a_Foo_jni.gen.cpp", "com_b_Foo_jni.gen.cpp"])

    def test_unique_class_uses_short_name(self):
        self.run_gen()  # single SampleEngine
        self.assertTrue((self.out / "SampleEngine_jni.gen.cpp").exists())


class TestGenerateTests(DriverTestCase):
    def test_generate_tests_flag_emits_test_file(self):
        rc = self.run_gen("--generate-tests")
        self.assertEqual(rc, gen.EXIT_OK)
        test_file = self.out / "SampleEngine_jni_test.gen.cpp"
        self.assertTrue(test_file.exists(), "expected test file to be written")

    def test_generate_tests_content(self):
        self.run_gen("--generate-tests")
        content = (self.out / "SampleEngine_jni_test.gen.cpp").read_text()
        self.assertIn("if (false)", content)
        self.assertIn("int main()", content)
        self.assertIn("AUTO-GENERATED", content)

    def test_generate_tests_incremental(self):
        self.run_gen("--generate-tests")
        test_file = self.out / "SampleEngine_jni_test.gen.cpp"
        before_mtime = test_file.stat().st_mtime_ns
        self.run_gen("--generate-tests")
        self.assertEqual(test_file.stat().st_mtime_ns, before_mtime)


class TestErrors(DriverTestCase):
    def test_missing_source_path_is_usage_error(self):
        rc = gen.main(["--kotlin-source", str(self.root / "nope"), "--output", str(self.out)])
        self.assertEqual(rc, gen.EXIT_USAGE)

    def test_unknown_type_reports_line_and_function(self):
        import io
        from contextlib import redirect_stderr

        bad_dir = self.root / "badsrc"
        bad_dir.mkdir()
        (bad_dir / "N.kt").write_text(BAD_SOURCE, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = gen.main(["--kotlin-source", str(bad_dir), "--output", str(self.root / "bo")])
        self.assertEqual(rc, gen.EXIT_PARSE)
        err = buf.getvalue()
        self.assertIn("line 6", err)  # `external fun bad(` is on line 6
        self.assertIn("bad()", err)
        self.assertIn("weird_type", err)

    def test_line_number_is_accurate(self):
        parsed = gen.parse_kotlin_source(BAD_SOURCE)
        bad = next(f for f in parsed.functions if f.name == "bad")
        # `external fun bad(` is on line 6 of BAD_SOURCE (1-based, leading newline).
        self.assertEqual(bad.line, 6)

    def test_source_with_no_external_funs_is_usage_error(self):
        no_funs = self.root / "nofuns"
        no_funs.mkdir()
        (no_funs / "Plain.kt").write_text(
            "package com.example\nclass Plain { fun normal() {} }", encoding="utf-8"
        )
        rc = gen.main(["--kotlin-source", str(no_funs), "--output", str(self.out)])
        self.assertEqual(rc, gen.EXIT_USAGE)


class TestTypeMap(DriverTestCase):
    _CUSTOM_SOURCE = """
package com.example

class N {
    external fun load(cfg: NativeConfig): Long
    external fun getConfigs(h: Long): ConfigList
}
"""
    _TYPE_MAP_JSON = """{
  "types": {
    "NativeConfig": {
      "jni_type": "jobject",
      "cpp_type": "native_config_t",
      "convert": "extract_native_config({env}, {var})"
    },
    "ConfigList": {
      "jni_type": "jobject",
      "cpp_type": "std::vector<native_config_t>",
      "convert": "extract_config_list({env}, {var})"
    }
  },
  "returns": {
    "NativeConfig": ["jobject", "nullptr"],
    "ConfigList": ["jobject", "nullptr"]
  },
  "make_helpers": {
    "ConfigList": ["make_config_list", "std::vector<native_config_t>"]
  }
}"""

    def setUp(self):
        super().setUp()
        (self.src / "N.kt").write_text(self._CUSTOM_SOURCE, encoding="utf-8")
        self.type_map = self.root / "types.json"
        self.type_map.write_text(self._TYPE_MAP_JSON, encoding="utf-8")

    def test_custom_type_resolves_without_error(self):
        rc = self.run_gen("--type-map", str(self.type_map))
        self.assertEqual(rc, gen.EXIT_OK)

    def test_custom_type_appears_in_output(self):
        self.run_gen("--type-map", str(self.type_map))
        content = (self.out / "N_jni.gen.cpp").read_text(encoding="utf-8")
        self.assertIn("extract_native_config(env, cfg)", content)
        self.assertIn("make_config_list", content)

    def test_missing_type_map_file_is_usage_error(self):
        rc = self.run_gen("--type-map", str(self.root / "no_such.json"))
        self.assertEqual(rc, gen.EXIT_USAGE)


class TestDryRun(DriverTestCase):
    def test_dry_run_does_not_write_files(self):
        self.run_gen("--dry-run")
        self.assertFalse((self.out / "SampleEngine_jni.gen.cpp").exists())

    def test_dry_run_prints_generated_code(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.run_gen("--dry-run")
        self.assertEqual(rc, gen.EXIT_OK)
        out = buf.getvalue()
        self.assertIn("Java_com_example_sample_SampleEngine", out)
        self.assertIn("[dry-run]", out)

    def test_dry_run_shows_all_functions(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            self.run_gen("--dry-run")
        out = buf.getvalue()
        self.assertIn("nativeLoad", out)
        self.assertIn("nativeRelease", out)


class TestDiffMode(DriverTestCase):
    def test_diff_no_existing_shows_output(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.run_gen("--diff")
        self.assertEqual(rc, gen.EXIT_OK)
        out = buf.getvalue()
        self.assertIn("SampleEngine_jni.gen.cpp", out)

    def test_diff_does_not_write_files(self):
        self.run_gen("--diff")
        self.assertFalse((self.out / "SampleEngine_jni.gen.cpp").exists())

    def test_diff_unchanged_reports_unchanged(self):
        import io
        from contextlib import redirect_stdout

        self.run_gen()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.run_gen("--diff")
        self.assertEqual(rc, gen.EXIT_OK)
        self.assertIn("unchanged", buf.getvalue())

    def test_diff_after_source_change_shows_diff(self):
        import io
        from contextlib import redirect_stdout

        self.run_gen()
        (self.src / "SampleEngine.kt").write_text(
            SOURCE.replace("threads: Int", "threads: Int, extra: String"),
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.run_gen("--diff")
        self.assertEqual(rc, gen.EXIT_OK)
        out = buf.getvalue()
        self.assertIn("@@", out)


class TestVerboseMode(DriverTestCase):
    def test_verbose_prints_class_name(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.run_gen("--verbose")
        self.assertEqual(rc, gen.EXIT_OK)
        self.assertIn("SampleEngine", buf.getvalue())

    def test_verbose_prints_function_names(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            self.run_gen("--verbose")
        out = buf.getvalue()
        self.assertIn("nativeLoad", out)
        self.assertIn("nativeRelease", out)


class TestPackageFilter(DriverTestCase):
    def _write_two_packages(self):
        (self.src / "A.kt").write_text(
            "package com.example.a\nclass A { external fun doA(x: Int): Long }",
            encoding="utf-8",
        )
        (self.src / "B.kt").write_text(
            "package com.example.b\nclass B { external fun doB(x: Int): Long }",
            encoding="utf-8",
        )

    def test_filter_restricts_output(self):
        self._write_two_packages()
        rc = gen.main(
            [
                "--kotlin-source",
                str(self.src),
                "--output",
                str(self.out),
                "--package-filter",
                "com.example.a",
            ]
        )
        self.assertEqual(rc, gen.EXIT_OK)
        names = [p.name for p in self.out.glob("*.gen.cpp")]
        self.assertTrue(any("A_jni" in n or "A" in n for n in names), names)
        self.assertFalse(any("B" in n for n in names), names)

    def test_no_filter_includes_all(self):
        self._write_two_packages()
        rc = gen.main(["--kotlin-source", str(self.src), "--output", str(self.out)])
        self.assertEqual(rc, gen.EXIT_OK)
        names = [p.name for p in self.out.glob("*.gen.cpp")]
        self.assertGreaterEqual(len(names), 2)


class TestIosCinterop(DriverTestCase):
    def test_ios_cinterop_writes_def_file(self):
        ios_out = self.root / "cinterop"
        rc = gen.main(
            [
                "--kotlin-source",
                str(self.src),
                "--output",
                str(self.out),
                "--ios-cinterop",
                str(ios_out),
            ]
        )
        self.assertEqual(rc, gen.EXIT_OK)
        def_files = list(ios_out.glob("*.def"))
        self.assertGreater(len(def_files), 0)

    def test_ios_cinterop_writes_c_header(self):
        ios_out = self.root / "cinterop"
        gen.main(
            [
                "--kotlin-source",
                str(self.src),
                "--output",
                str(self.out),
                "--ios-cinterop",
                str(ios_out),
            ]
        )
        headers = list((ios_out / "include").glob("*.h"))
        self.assertGreater(len(headers), 0)

    def test_ios_cinterop_header_contains_c_types(self):
        ios_out = self.root / "cinterop"
        gen.main(
            [
                "--kotlin-source",
                str(self.src),
                "--output",
                str(self.out),
                "--ios-cinterop",
                str(ios_out),
            ]
        )
        header_text = (ios_out / "include" / "SampleEngine.h").read_text()
        self.assertIn("int32_t", header_text)
        self.assertIn("int64_t", header_text)
        self.assertIn("native_load", header_text)

    def test_ios_cinterop_def_has_headers_line(self):
        ios_out = self.root / "cinterop"
        gen.main(
            [
                "--kotlin-source",
                str(self.src),
                "--output",
                str(self.out),
                "--ios-cinterop",
                str(ios_out),
            ]
        )
        def_text = (ios_out / "SampleEngine.def").read_text()
        self.assertIn("headers = include/SampleEngine.h", def_text)
        self.assertIn("headerFilter = include/**", def_text)

    def test_ios_cinterop_def_has_package_comment(self):
        ios_out = self.root / "cinterop"
        gen.main(
            [
                "--kotlin-source",
                str(self.src),
                "--output",
                str(self.out),
                "--ios-cinterop",
                str(ios_out),
            ]
        )
        def_text = (ios_out / "SampleEngine.def").read_text()
        self.assertIn("SampleEngine", def_text)

    def test_ios_cinterop_incremental(self):
        ios_out = self.root / "cinterop"
        args = [
            "--kotlin-source",
            str(self.src),
            "--output",
            str(self.out),
            "--ios-cinterop",
            str(ios_out),
        ]
        gen.main(args)
        def_file = ios_out / "SampleEngine.def"
        mtime_after_first = def_file.stat().st_mtime
        gen.main(args)
        self.assertEqual(
            def_file.stat().st_mtime,
            mtime_after_first,
            "def file was rewritten on second run (should be incremental)",
        )


if __name__ == "__main__":
    unittest.main()
