# Changelog

All notable changes to jni-binding-generator are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [1.5.5] — 2026-06-26

### Fixed
- **`make_*` helpers crash on OOM** (`jni-utils.h`) — `NewObject` can return null when
  an `OutOfMemoryError` is pending. All 42 `make_list_*`, `make_set_*`, and
  `make_map_*` helpers now null-check the result and return `nullptr` immediately,
  leaving the pending exception intact instead of dereferencing null.
- **`enum_ordinal` missing guard on `GetMethodID` result** (`jni-utils.h`) — If
  `ordinalM` was null, `CallIntMethod` was undefined behaviour. Added a null-check
  that cleans up the local ref and returns `-1`.
- **`--kotlin-from-header` maps mutable `char*` to `String`** — `const char*` (input
  string) and `char*` (C output buffer) were both mapped to `String`. Mutable `char*`
  params are now correctly mapped to `ByteArray`. `ImageClassifier.kt` and its
  generated JNI stub regenerated accordingly.

---

## [1.5.4] — 2026-06-26

### Fixed
- **Broken `gradlew` scripts in example projects** — Both `examples/android-binding`
  and `examples/kmp-binding` shipped a simplified stub that failed with
  `Error: could not find or load main class "-Xmx64m"` due to JVM opts quoting.
  Replaced both with the standard 248-line Gradle wrapper script and committed
  the `gradle-wrapper.jar` (44 KB) so `./gradlew generateAll` works immediately
  after cloning, with no manual wrapper bootstrap needed.

---

## [1.5.3] — 2026-06-26

### Fixed
- **Release archive was missing all seven submodules** — `release.yml` tar only
  included `jni-binding-generator.py`, `__init__.py`, and `jni-utils.h`; the
  seven `_*.py` submodules required at runtime were absent, causing
  `ModuleNotFoundError` for anyone who installed from the release tarball.
  All submodules now included; standalone script uploads removed (the archive
  is the correct delivery artifact).
- **CI drift job missing `--kotlin-from-header --check` step** — The `drift`
  job in `ci.yml` checked that `ImageClassifier_jni.gen.cpp` was up to date
  with `ImageClassifier.kt`, but did not verify that `ImageClassifier.kt` was
  up to date with `image_classifier.h`. Added a dedicated "Check android-binding
  Kotlin stubs" step that runs `--kotlin-from-header --check` before the forward-
  pass check.
- **Pre-commit `files:` patterns missing `_kotlin_gen.py`** — Changes to the
  reverse generator did not trigger tests or drift hooks. Updated all five hook
  patterns to include `_kotlin_gen`.
- **Added `jni-generator-drift-android-kt` pre-commit hook** — Detects drift
  between `image_classifier.h` and the generated `ImageClassifier.kt` at commit
  time (reverse-direction counterpart to the existing forward-pass hook).
- **`android-binding` was not bootstrappable** — Added `settings.gradle.kts`,
  `gradle/wrapper/gradle-wrapper.properties`, `gradlew`, and `gradlew.bat` so
  `./gradlew generateAll` works without a pre-installed Gradle.
- **`kmp-binding/shared/src/jvmMain` was an empty directory** — Added
  `NativeBridge.jvm.kt` with a comment explaining the source set's purpose.

### Changed
- **README "Try It" block** — Added `--kotlin-from-header` example; updated
  KMP Gradle snippet to show the convention plugin DSL (raw `Exec` task kept as
  a secondary option).
- **`.gitignore`** — Added Gradle/Android build artifact entries: `.gradle/`,
  `**/build/`, `gradle-wrapper.jar`, `local.properties`, `.kotlin/`,
  `compose-desktop.pro`.
- **`gradle-integration/README.md`** — Removed stale "not executed offline"
  caveat; replaced with a pointer to `examples/kmp-binding/` as the living
  reference.
- **`CONTRIBUTING.md`** — Expanded drift-check step to list all five checks
  (three forward-pass + one reverse-pass + sample-binding), matching the
  pre-commit hooks exactly.

---

## [1.5.2] — 2026-06-26

### Added
- **`examples/android-binding` — full C→Kotlin→C++ round-trip demo:**
  - New `include/image_classifier.h` — concrete C API header as `--kotlin-from-header` input.
  - `src/ImageClassifier.kt` is now **auto-generated** from the header (Phase 1).
  - `build.gradle.kts` gains three `jni` group tasks: `generateKotlinFromHeader`
    (Phase 1), `generateJniBindings` (Phase 2), and `generateAll` (both in order).
  - README updated with the two-phase pipeline diagram and per-task docs.
- **`examples/kmp-binding` — convention plugin + app entry points:**
  - `build-logic/` — local copy of `gradle-integration/build-logic`; exposes
    `id("jni-generator")` without publishing to a plugin portal.
  - `settings.gradle.kts` now includes the build-logic via `includeBuild("build-logic")`.
  - `shared/build.gradle.kts` switched from raw `Exec` tasks to the typed DSL:
    `jniGenerator { bindings { register("android") { … } register("desktop") { … } } }`.
  - `androidApp/src/main/kotlin/…/MainActivity.kt` — Compose Activity entry point.
  - `androidApp/src/main/AndroidManifest.xml`.
  - `desktopApp/src/desktopMain/kotlin/…/Main.kt` — Compose Desktop entry point.
  - `gradle/wrapper/gradle-wrapper.properties` + `gradlew` / `gradlew.bat` —
    project is now bootstrappable without a pre-installed Gradle.
  - README rewritten to document the plugin DSL, all Gradle tasks, and platform targets.

---

## [1.5.1] — 2026-06-26

### Added
- **`--kotlin-from-header FILE`** — reverse-generation mode that parses a C/C++
  header and emits a Kotlin `object { external fun … }` stub file ready for JNI
  wiring.
  - `--kotlin-package PKG` sets the package declaration in the generated file.
  - Supports `--dry-run` (print without writing) and `--check` (exit 3 on drift),
    consistent with the forward-generation flags.
  - Generates a companion `.kt` named after the header stem (e.g. `engine.h` →
    `Engine.kt`).
- **`scripts/_kotlin_gen.py`** — new module implementing the C→Kotlin reverse
  generator:
  - `_C_PARAM_MAP` / `_C_RETURN_MAP` — parameter and return type tables;
    pointer-array params map to `*Array` types while returned pointers map to
    `Long` (opaque handle convention).
  - `_strip_c_source()` — removes comments, preprocessor lines, struct/union/enum
    blocks, typedefs, `extern "C"` wrappers, `__attribute__`, and `__declspec`.
  - `parse_c_header(source)` / `parse_c_header_file(path)` — parse C function
    declarations, deduplicate by name, skip type keywords and C++ operators.
  - `generate_kotlin_stubs(source, …)` / `generate_kotlin_from_header(path, …)` —
    produce the full `.kt` file content.
  - `_header_to_object_name(path)` — derives the Kotlin object name from the
    header filename (`my_engine.h` → `MyEngine`).
- **55 new tests** in `scripts/tests/test_kotlin_gen.py` covering type mapping,
  name conversion, source stripping, parser edge cases, full stub generation,
  and CLI integration (207 tests total, up from 152).

---

## [1.5.0] — 2026-06-26

### Changed
- **Modularized `scripts/jni-binding-generator.py`** — the 1,409-line monolith
  is split into six focused modules:
  - `scripts/_models.py` — `Param`, `ExternalFunction`, `ParsedFile`, exit constants
  - `scripts/_types.py` — `TypeInfo`, `TYPE_MAP`, `RETURN_MAP`, `_MAKE_HELPER_MAP`,
    type-mapping helpers, `load_type_map`
  - `scripts/_parser.py` — Kotlin parsing, `mangle`, `jni_function_name`
  - `scripts/_generator.py` — C++ code generation, output naming
  - `scripts/_ios.py` — iOS/Kotlin-Native cinterop skeleton generation
  - `scripts/_driver.py` — `run()`, `parse_args()`, `main()`, `collect_kotlin_files()`
- `scripts/jni-binding-generator.py` is now a 60-line entry point that patches
  `sys.path` and re-exports every public symbol, so all existing tests and the
  `__init__.py` pip shim remain unchanged.
- Pre-commit drift hooks updated to trigger on any `scripts/_*.py` change, not
  only on `scripts/jni-binding-generator.py`.
- `ruff.toml` — added `[lint.per-file-ignores]` to suppress `E402` for the entry
  point (imports must follow the `sys.path` patch).
- `CONTRIBUTING.md` and `docs/type-support-matrix.md` — "Adding a New Type"
  instructions now point to `scripts/_types.py`.
- `README.md` — repository structure tree updated to list all six new modules.

---

## [1.4.8] — 2026-06-26

### Fixed
- **`--check --ios-cinterop` wrote cinterop files** — `main()` called
  `generate_ios_cinterop_files()` unconditionally after `run()` returned 0, so
  `--check` (and `--dry-run`) would still create `.def` and `include/*.h` files
  when the JNI output was already up to date. Added `not args.check and not
  args.dry_run` guard. Both flags are now fully read-only as documented.
- Added 2 regression tests in `TestIosCinterop`:
  `test_check_does_not_write_cinterop_files` and
  `test_dry_run_does_not_write_cinterop_files`.

### Changed
- Test count: 150 → 152
- `docs/unit-testing.md`: updated `TestIosCinterop` description to include the
  read-only assertions.

---

## [1.4.7] — 2026-06-26

### Fixed
- **`--check --generate-tests` silently passed when test file was missing** — the
  `not check` guard at the generate-tests branch entirely skipped test-file logic
  during check mode, so `--check --generate-tests` always exited 0 regardless of
  whether `*_jni_test.gen.cpp` existed or was up to date. The guard is removed;
  check mode now computes the expected test content and appends the test path to
  `drifted` if the file is absent or out of date, printing `[check] …: missing` or
  `[check] …: drift`. Write behavior when `check=False` is unchanged.
- Added 4 regression tests in `TestGenerateTests` covering missing, stale, up-to-date,
  and no-write assertions for `--check --generate-tests`.

### Added
- `docs/advanced-usage.md`: three new sections covering flags that were absent from
  the doc:
  - `--generate-tests` — emit `*_jni_test.gen.cpp` compile-time type-check files;
    includes `--check --generate-tests` combo for CI drift detection of test files.
  - `--dry-run` — preview generated C++ to stdout without writing files.
  - `--verbose` — print class and function names during generation.
  - Exit code table in the `--check` section expanded to all four codes (0/1/2/3).
- `docs/JNI_BINDING_GENERATOR_PLAN.md`: updated three remaining "Python 3.9+"
  references to "Python 3.10+".
- `.github/workflows/ci.yml` / `.pre-commit-config.yaml`: sample-binding drift check
  now passes `--generate-tests` so the committed `*_jni_test.gen.cpp` is also verified.
- `gradle-integration/README.md`: added `--check --generate-tests` variant to CI drift
  section.
- `examples/sample-binding/README.md`: merged two-step regenerate into one command with
  `--generate-tests`; added Drift check section.

### Changed
- Test count: 146 → 150

---

## [1.4.6] — 2026-06-26

### Added
- `test_source_with_no_external_funs_is_usage_error` in `TestErrors`
  (`test_driver.py`) — the "No external functions found" `EXIT_USAGE` path was
  exercised manually but had no regression test. New test covers a `.kt` file
  with no `external fun` declarations.

### Changed
- Test count: 145 → 146
- `docs/unit-testing.md`: updated `TestErrors` description; updated header count.
- `README.md` / `CONTRIBUTING.md`: updated test count to 146.

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
