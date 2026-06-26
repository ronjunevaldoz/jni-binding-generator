# Changelog

All notable changes to jni-binding-generator are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [1.2.0] — 2026-06-26

### Added
- **Complete type coverage** — all 66 TYPE_MAP entries; every combination now supported:
  - `Map<Long, *>` — 6 new variants (`Int/Long/String/Float/Double/Boolean` values)
  - `Map<String, Double>` and `Map<Int, Double>` — Double value for all key types
  - `List<List<Short>>` and `List<List<Byte>>` — nested lists for all 8 scalar types
  - `Set<Byte>` and `Set<Short>` — Set family now covers all 8 scalar types
- `scripts/tests/test_memory.py` — 17 static-analysis tests (798 subtests) verifying that
  every JNI local-reference acquisition in `jni-utils.h` has a matching release (EP-6,
  `FindClass`/`DeleteLocalRef` balance, iterator-loop cleanup, boxed object release)
- `scripts/tests/test_integration.py` — compile-check fixture extended to cover all new
  type families; now exercises all 66 TYPE_MAP entries against the real JDK `jni.h`
- `docs/memory-management.md` — automated-tests table and per-helper leak status for all
  helpers in `jni-utils.h` (audited clean 2026-06-26)

### Changed
- Test count: 58 → 113 across 5 suites (added `test_memory.py` suite)
- `docs/unit-testing.md`: updated test count and added `test_memory.py` suite description

### Previously added (in 1.1.0)
- `--diff` flag — prints a unified diff of what would change without writing files
- `--type-map FILE` flag — loads custom Kotlin→JNI type mappings from a JSON file
- Multi-class support: a single `.kt` file with multiple `class`/`object` declarations now produces one binding file per class (`parse_kotlin_source_multi`)
- Android project example under `examples/android-binding/` with `build.gradle.kts`, `CMakeLists.txt`, and generated bindings
- Windows CI support (`windows-latest` added to test matrix)
- GitHub Actions release workflow — cuts a GitHub Release with `jni-binding-generator.py` and `jni-utils.h` as assets on `vX.Y.Z` tag push
- `List<Short>`, `Set<Long>`, `Set<Float>`, `Set<Boolean>`, `Set<Double>`
- `Map<String,Long>`, `Map<String,Float>`, `Map<String,Boolean>`
- `Map<Int,Int>`, `Map<Int,Long>`, `Map<Int,Float>`, `Map<Int,Boolean>`
- `Array<Byte>`, `Array<Boolean>`, `Array<Short>`
- `List<List<Int>>`, `List<List<Float>>`, `List<List<Long>>`, `List<List<Double>>`, `List<List<Bool>>`, `List<List<String>>`
- `docs/advanced-usage.md` — thread safety, `JNI_OnLoad`, exception propagation, Android NDK setup, unsupported constructs
- `docs/type-support-matrix.md` — all supported Kotlin types with param/return status

---

## [1.0.0] — 2026-04-01

### Added
- Initial release
- Python generator (`jni-binding-generator.py`) that reads Kotlin `external fun` declarations and emits JNI C++ boilerplate
- `jni-utils.h` header-only C++ helpers for common JNI type conversions
- Sample binding under `examples/sample-binding/`
- `--dry-run`, `--check` (drift detection), and `--generate-tests` flags
- Gradle plugin integration via `build.gradle.kts` exec task
- GitHub Actions CI with lint (ruff) and test (Ubuntu + macOS) jobs
- Type support: primitives, strings, primitive arrays, `Array<String>`, `List<T>`, `Set<T>`, `Map<K,V>`, nullable variants, auto-detected enums, top-level functions, `@JvmName` override, nested classes
