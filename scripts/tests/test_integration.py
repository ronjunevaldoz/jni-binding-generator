"""Integration test: generated C++ compiles against real JNI headers.

Skipped automatically when a C++ compiler or the JDK's jni.h cannot be found,
so the suite still runs in minimal environments.
"""

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(SCRIPTS_DIR))

gen = importlib.import_module("jni-binding-generator")


# Covers every type in TYPE_MAP / RETURN_MAP so the compile test catches
# signature regressions for all supported Kotlin → JNI mappings.
NEW_BINDING = """
package com.example.integration

class NewEngine {
    // Primitives
    external fun nativeOpen(path: String, threads: Int, gpu: Boolean): Long
    external fun nativeSetScale(handle: Long, scale: Float): Double
    external fun nativeGetShort(handle: Long, idx: Int): Short
    external fun nativeGetByte(handle: Long, idx: Int): Byte

    // String
    external fun nativeGetName(handle: Long): String
    external fun nativeMaybeTag(handle: Long): String?

    // Primitive arrays
    external fun nativeInfer(
        handle: Long,
        logits: FloatArray,
        ids: IntArray,
        weights: LongArray,
        samples: ShortArray,
        gains: DoubleArray,
        mask: BooleanArray,
    ): ByteArray?

    // Object arrays
    external fun nativeBatch(handle: Long, prompts: Array<String>): IntArray

    // List variants
    external fun nativeGetTags(handle: Long): List<String>
    external fun nativeGetScores(handle: Long): List<Float>
    external fun nativeGetCounts(handle: Long): List<Int>
    external fun nativeGetWeights(handle: Long): List<Long>
    external fun nativeGetValues(handle: Long): List<Double>
    external fun nativeGetFlags(handle: Long): List<Boolean>
    external fun nativeGetBytes(handle: Long): List<Byte>
    external fun nativeGetChunks(handle: Long): List<List<String>>

    // Set variants
    external fun nativeGetKeySet(handle: Long): Set<String>
    external fun nativeGetIdSet(handle: Long): Set<Int>

    // Map variants
    external fun nativeGetMeta(handle: Long): Map<String, String>
    external fun nativeGetFreqs(handle: Long): Map<String, Int>
    external fun nativeGetLabels(handle: Long): Map<Int, String>

    // Enum (auto-detected PascalCase)
    external fun nativeGetStrategy(handle: Long): SamplingStrategy
    external fun nativeSetStrategy(handle: Long, strategy: SamplingStrategy)

    // Nullable params
    external fun nativeMaybeInfer(handle: Long?, prompt: String?): String?

    // Void return
    external fun nativeClose(handle: Long)
}
"""


def _find_compiler():
    for cc in ("clang++", "g++", "c++"):
        path = shutil.which(cc)
        if path:
            return path
    return None


def _jni_include_dirs():
    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        try:
            out = subprocess.run(
                ["/usr/libexec/java_home"], capture_output=True, text=True, timeout=10
            )
            if out.returncode == 0:
                java_home = out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            java_home = None
    if not java_home:
        return None
    base = Path(java_home) / "include"
    if not (base / "jni.h").exists():
        return None
    dirs = [base]
    # Platform md header (jni_md.h) lives in an OS-specific subdir.
    for sub in ("darwin", "linux", "win32"):
        if (base / sub).exists():
            dirs.append(base / sub)
    return dirs


class TestGeneratedCompiles(unittest.TestCase):
    def test_new_binding_compiles(self):
        compiler = _find_compiler()
        if not compiler:
            self.skipTest("no C++ compiler found")
        includes = _jni_include_dirs()
        if not includes:
            self.skipTest("JDK jni.h not found (set JAVA_HOME)")

        parsed = gen.parse_kotlin_source(NEW_BINDING)
        content = gen.generate_file(parsed, "NewEngine.kt")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shutil.copy(SCRIPTS_DIR / "jni-utils.h", tmp_path / "jni-utils.h")
            cpp = tmp_path / "NewEngine_jni.gen.cpp"
            cpp.write_text(content, encoding="utf-8")

            cmd = [compiler, "-std=c++17", "-fsyntax-only"]
            for d in includes:
                cmd += ["-I", str(d)]
            cmd += ["-I", str(tmp_path), str(cpp)]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"generated C++ failed to compile:\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
