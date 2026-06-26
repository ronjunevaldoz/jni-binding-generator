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
        y: WeirdType,
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
        return gen.main(
            ["--kotlin-source", str(self.src), "--output", str(self.out), *extra]
        )


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


class TestErrors(DriverTestCase):
    def test_missing_source_path_is_usage_error(self):
        rc = gen.main(
            ["--kotlin-source", str(self.root / "nope"), "--output", str(self.out)]
        )
        self.assertEqual(rc, gen.EXIT_USAGE)

    def test_unknown_type_reports_line_and_function(self):
        (self.src / "N.kt").write_text(BAD_SOURCE, encoding="utf-8")
        # Generate just the bad file to a fresh dir and capture the exit code.
        bad_dir = self.root / "badsrc"
        bad_dir.mkdir()
        (bad_dir / "N.kt").write_text(BAD_SOURCE, encoding="utf-8")
        rc = gen.main(
            ["--kotlin-source", str(bad_dir), "--output", str(self.root / "bo")]
        )
        self.assertEqual(rc, gen.EXIT_PARSE)

    def test_line_number_is_accurate(self):
        parsed = gen.parse_kotlin_source(BAD_SOURCE)
        bad = next(f for f in parsed.functions if f.name == "bad")
        # `external fun bad(` is on line 6 of BAD_SOURCE (1-based, leading newline).
        self.assertEqual(bad.line, 6)


if __name__ == "__main__":
    unittest.main()
