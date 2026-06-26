# Changelog

All notable changes to jni-binding-generator are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [1.4.5] — 2026-06-26

### Fixed
- `docs/memory-management.md`: `TestHeaderPresent` (smoke test verifying
  `jni-utils.h` exists, is non-empty, and exposes >20 helpers) was present in
  `test_memory.py` but absent from the automated-tests table. Added.
- `CONTRIBUTING.md` / `docs/type-support-matrix.md`: the two "Adding a new type"
  checklists were inconsistent — one mentioned `jni-utils.h` helpers but not tests;
  the other mentioned tests but not helpers. Both now list all 6 steps:
  `TYPE_MAP` → `RETURN_MAP` → `jni-utils.h` helpers → `_MAKE_HELPER_MAP` →
  test → `type-support-matrix.md`.

---

## [1.4.4] — 2026-06-26

### Fixed
- `release.yml`: release archive and asset list did not include `scripts/__init__.py`
  (added in v1.4.3) — a user downloading a GitHub release and running `pip install`
  would get a broken entry point. Added `__init__.py` to both the tar archive and
  the per-file release assets. Also added `pyproject.toml` to the archive so the
  downloaded tarball is self-contained for `pip install .`.
- `examples/kmp-binding/iosApp/README.md`: rewrote to reference the generated
  `.def` and `.h` files that are already present in the repo, and show the exact
  `--ios-cinterop` command that produced them. The previous content gave generic
  manual-creation instructions without mentioning the generator flag.

---

## [1.4.3] — 2026-06-26

### Fixed
- **`pip install .` entry point was broken** — `jni_binding_generator:main` requires
  `scripts/__init__.py` to export `main`, but the file did not exist. The main script
  is named `jni-binding-generator.py` (hyphen) so it is not directly importable.
  Added `scripts/__init__.py` that loads the script via `importlib.util` and exposes
  `main`, with the module registered in `sys.modules` before execution to satisfy
  Python's dataclass `__module__` resolution.

---

## [1.4.2] — 2026-06-26

### Fixed
- `CONTRIBUTING.md`: "Python 3.9+ required" updated to "Python 3.10+" to match
  `requires-python` in pyproject.toml. "confirm all 140 tests pass" updated to 145.

---

## [1.4.1] — 2026-06-26

### Fixed
- `ruff.toml`: `target-version = "py39"` was inconsistent with the `>=3.10`
  minimum set in [1.4.0]. Updated to `"py310"` so `pyupgrade` and other
  version-aware rules target the correct baseline.

---

## [1.4.0] — 2026-06-26

### Fixed
- **Python version requirement** — `pyproject.toml` claimed `requires-python = ">=3.9"`
  but the generator uses `X | Y` union type syntax in dataclass fields and function
  annotations, which requires Python 3.10+. Python 3.9 reached EOL in October 2025.
  Updated to `>=3.10` and removed the `Python :: 3.9` classifier.
- `README.md`: "Python 3.9+" in the Quick Facts table updated to "Python 3.10+".
- `.github/workflows/ci.yml`: test matrix now covers both Python 3.10 and 3.12 across
  all three OSes (6 jobs) so the declared minimum version is actually exercised in CI.

---

## [1.3.9] — 2026-06-26

### Fixed
- `ACKNOWLEDGMENTS.md`: footer status was "Planning phase — awaiting go/no-go
  decision"; updated to reflect the current shipped state (v1.3.8, 145 tests).

---

## [1.3.8] — 2026-06-26

### Fixed
- `gradle-integration/README.md`: CI drift check section used `git diff
  --exit-code` instead of the built-in `--check` flag. Updated to show `--check`
  as the primary approach with an explanation of exit codes.
- `gradle-integration/README.md`: removed residual "Phase 3 preview" label from
  the CI drift heading.

---

## [1.3.7] — 2026-06-26

### Fixed
- `examples/sample-binding/README.md`: the committed `SampleEngine_jni_test.gen.cpp`
  output file was not mentioned. Added an Output entry describing the compile-time
  type-check file and a `--generate-tests` regenerate command.
- `gradle-integration/README.md`: removed stale "Phase 2" from the heading.

---

## [1.3.6] — 2026-06-26

### Fixed
- `docs/unit-testing.md`: three test classes existed in code but were absent from
  the docs — `TestMultiClass` (multi-class parse in `test_parser.py`),
  `TestGeneration` (main generator class in `test_generator.py`), and
  `TestGeneratedCompiles` (integration class in `test_integration.py`). All three
  now appear with accurate descriptions.

---

## [1.3.5] — 2026-06-26

### Fixed
- `docs/JNI_BINDING_GENERATOR_PLAN.md`: executive summary incorrectly said "Phases 2–3
  remain optional/future work" — both phases are fully implemented. Updated to reflect
  current state.
- `.pre-commit-config.yaml`: kmp-binding was only drift-checked in CI, not in pre-commit
  hooks. Added `jni-generator-drift-kmp-android` and `jni-generator-drift-kmp-desktop`
  hooks to match CI coverage across all four examples.

---

## [1.3.4] — 2026-06-26

### Added
- `docs/advanced-usage.md`: new `--check` / `--diff` section documenting the CI
  drift-detection workflow — YAML snippet, exit-code table, and the read-only
  guarantee for both flags.
- `docs/advanced-usage.md`: new `--package-filter` section explaining prefix-match
  semantics and the KMP use case (filtering `androidMain` sources to a specific
  package).

---

## [1.3.3] — 2026-06-26

### Added
- `docs/advanced-usage.md`: new `--ios-cinterop` section with full command
  example, annotated `.def` and `.h` output, and a step-by-step integration
  guide. The flag was previously documented only in the README one-liner.

---

## [1.3.2] — 2026-06-26

### Fixed
- `pyproject.toml`: removed dead `[tool.ruff]` / `[tool.ruff.lint]` sections that
  were shadowed by `ruff.toml` (which takes precedence). The two configs had
  diverged: `pyproject.toml` selected `["E","F","W","I"]` while `ruff.toml`
  selected `["E","F","I","UP","B"]`. Now there is a single source of truth.
- `README.md`: removed stale "Claude agent skill" bullet, pre-launch "template
  ready for evaluation / when repo is live" footer, and internal development
  narrative. Credits & Attribution section condensed to a concise paragraph.

---

## [1.3.1] — 2026-06-26

### Fixed
- **`@JvmName` on consecutive functions** — when two adjacent `external fun`
  declarations both carried `@JvmName`, the second function's annotation was
  discarded and it kept its Kotlin name. Fixed the parser to walk all `@JvmName`
  candidates in the look-behind window and accept the last one that has no
  `external fun` between it and the current function.
- Added regression test `test_jvm_name_on_consecutive_functions`.

### Changed
- Test count: 144 → 145

---

## [1.3.0] — 2026-06-26

### Fixed
- **`@JvmName` bleeding into the next function** — when a function annotated with
  `@JvmName("foo")` was followed by another `external fun` within 300 characters,
  the parser applied the annotation's name to both functions. The look-behind check
  now discards a `@JvmName` match if another `external fun` appears between the
  annotation and the current function.
- Added regression test `test_jvm_name_does_not_bleed_to_next_function` in
  `test_parser.py::TestJvmName`.

### Changed
- Test count: 143 → 144

---

## [1.2.9] — 2026-06-26

### Added
- `docs/advanced-usage.md`: new `--type-map` section documenting the full JSON
  schema (`types`, `returns`, `make_helpers`), field-by-field reference table,
  `is_handle`/`is_string` flags, override semantics, and a worked example with
  a pointer to `TestTypeMap`.

---

## [1.2.8] — 2026-06-26

### Fixed
- `test_integration.py`: compile fixture was missing 7 `Array<T>` boxed-array
  types (`Array<Byte/Boolean/Int/Short/Long/Float/Double>`) and an explicit
  `Unit` return. All 66 TYPE_MAP entries now have at least one compile-verified
  stub in the integration test.

---

## [1.2.7] — 2026-06-26

### Added
- `TestDryRun` in `test_driver.py` — 3 tests verifying `--dry-run` prints
  generated code with a `[dry-run]` marker and never writes files.
- `--dry-run` example added to README CLI section (flag existed but was
  undocumented in README).
- `TestDryRun` row added to `docs/unit-testing.md` driver table.

### Changed
- Test count: 140 → 143

---

## [1.2.6] — 2026-06-26

### Added
- `examples/android-binding/README.md` — before/after walkthrough with input/output
  table, Gradle integration notes, regenerate and drift-check commands.
- `examples/kmp-binding/README.md` — project structure diagram, per-target regenerate
  commands, iOS cinterop usage note.

---

## [1.2.5] — 2026-06-26

### Fixed
- `CONTRIBUTING.md`: rewrote stale content that said the project was "in planning phase"
  and "awaiting a go/no-go decision" — the project has been fully implemented since v1.0.0.
  Now accurately describes the development workflow, how to add a new type, and how to run
  the test suite.

### Changed
- `.pre-commit-config.yaml`: split single `jni-generator-drift` hook into two
  (`jni-generator-drift-sample` and `jni-generator-drift-android`) so the android-binding
  example is also checked on pre-commit, matching what CI already verifies.

---

## [1.2.4] — 2026-06-26

### Added
- `examples/android-binding/` — Android-only example that was promised in the
  CHANGELOG but never implemented: `src/ImageClassifier.kt` (7 external funs),
  `build.gradle.kts` (Gradle `Exec` task wired to `externalNativeBuild`),
  `CMakeLists.txt`, and the generated `ImageClassifier_jni.gen.cpp`.
- CI `drift` job now checks `examples/android-binding` alongside the existing
  sample-binding and kmp-binding drift checks.
- README examples tree and "See" link updated to include android-binding.

---

## [1.2.3] — 2026-06-26

### Fixed
- `--ios-cinterop`: `.def` and `include/*.h` files were rewritten unconditionally on
  every run, resetting their mtimes even when content was unchanged.  Now applies the
  same read-before-write guard used for `.gen.cpp` outputs so repeated runs are
  truly incremental.

### Added
- `TestIosCinterop` in `test_driver.py` extended with 3 new cases: `.def`
  `headers`/`headerFilter` lines present, package comment in `.def`, and a
  mtime-stability assertion that locks in the incremental behaviour.
- `TestTypeMap`, `TestDiffMode`, `TestVerboseMode`, `TestPackageFilter` driver
  test classes documented in `docs/unit-testing.md`.

### Changed
- Test count: 137 → 140

---

## [1.2.2] — 2026-06-26

### Fixed
- `release.yml`: CHANGELOG release-note extraction skipped `[Unreleased]` section
  and now correctly picks the first versioned entry — every tag release previously
  published blank release notes
- `test_memory.py`: `_all_function_bodies` false-positive on `inline` inside C++
  line comments caused `throw_java_exception` to appear twice in subtests
  (792 subtests, down from 798)

### Changed
- `docs/memory-management.md`: added `string2jstring` and `throw_illegal_*` wrappers
  to per-helper leak status table — every helper in `jni-utils.h` is now accounted for
- `docs/type-support-matrix.md`: complete overhaul — all 66 types documented in
  dedicated sections; added Enums and Unsupported types sections

---

## [1.2.1] — 2026-06-26

### Added
- `TestRemainingTypeCoverage` in `test_generator.py` — 24 new tests closing all remaining
  generator coverage gaps: `List<Int/Float>`, `List<List<Int/Float>>`, `Set<Int/Boolean/Double>`,
  `Map<String,String>`, `Map<Int,Int/Long/Float/Boolean/String>`, `FloatArray`, `LongArray`,
  `Array<Byte/Boolean/Short/Int/Long/Float/Double>`, `Unit` void return

### Changed
- Test count: 113 → 137
- `docs/type-support-matrix.md` — complete overhaul: all 66 types now documented in
  dedicated sections (Array<T>, List<List<T>>, Set<T>, Map<K,V>); added Enums and
  Unsupported types sections; removed misleading "Complex types" heading
- `docs/memory-management.md` — added `string2jstring` and `throw_illegal_*` to the
  per-helper leak status table for complete helper coverage

---

## [1.2.0] — 2026-06-26

### Added
- **Complete type coverage** — all 66 TYPE_MAP entries; every combination now supported:
  - `Map<Long, *>` — 6 new variants (`Int/Long/String/Float/Double/Boolean` values)
  - `Map<String, Double>` and `Map<Int, Double>` — Double value for all key types
  - `List<List<Short>>` and `List<List<Byte>>` — nested lists for all 8 scalar types
  - `Set<Byte>` and `Set<Short>` — Set family now covers all 8 scalar types
- `scripts/tests/test_memory.py` — 17 static-analysis tests (792 subtests) verifying that
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
