# AGENTS.md — jni-binding-generator

## What this project is

A Python CLI that generates C++ JNI boilerplate from Kotlin `external fun` declarations
(forward pass), and can also reverse-engineer Kotlin stubs from C/C++ headers
(`--kotlin-from-header`). The repo also ships a Gradle convention plugin
(`gradle-integration/build-logic/`) and two example projects.

## Essential commands

```bash
# Run all tests
python3 -m unittest discover -s scripts/tests -v

# Lint + format
ruff check scripts/ && ruff format --check scripts/

# All 5 drift checks (same as CI)
python3 scripts/jni-binding-generator.py \
  --kotlin-source examples/sample-binding/SampleEngine.kt \
  --output examples/sample-binding/generated --check --generate-tests

python3 scripts/jni-binding-generator.py \
  --kotlin-source examples/kmp-binding/shared/src/androidMain/kotlin \
  --output examples/kmp-binding/androidApp/src/main/cpp/generated --check

python3 scripts/jni-binding-generator.py \
  --kotlin-source examples/kmp-binding/shared/src/desktopMain/kotlin \
  --output examples/kmp-binding/desktopApp/src/jvmMain/cpp/generated --check

python3 scripts/jni-binding-generator.py \
  --kotlin-from-header examples/android-binding/include/image_classifier.h \
  --output examples/android-binding/src \
  --kotlin-package com.example.android.classifier --check

python3 scripts/jni-binding-generator.py \
  --kotlin-source examples/android-binding/src/ImageClassifier.kt \
  --output examples/android-binding/generated --check

# Score generation quality
python3 scripts/jni-binding-generator.py --score
```

## Architecture

```
scripts/
  jni-binding-generator.py   # thin entry point, re-exports all public symbols
  _driver.py                 # CLI arg parsing + dispatch
  _parser.py                 # Kotlin external fun parser
  _generator.py              # forward pass: Kotlin → C++ JNI stubs
  _kotlin_gen.py             # reverse pass: C header → Kotlin stubs
  _ios.py                    # --ios-cinterop: cinterop .def + C header
  _models.py                 # shared dataclasses (KotlinClass, KotlinFunc, …)
  _types.py                  # TYPE_MAP, RETURN_MAP, _MAKE_HELPER_MAP
  jni-utils.h                # C++ helper library (extract_*, make_*, jstring2string)
  tests/
    test_generator.py        # forward-pass tests
    test_kotlin_gen.py       # reverse-pass tests
    test_parser.py           # Kotlin parser tests
    test_driver.py           # CLI integration tests
    test_integration.py      # end-to-end compile tests (needs JDK)
    test_memory.py           # jni-utils.h memory-safety tests
```

## Invariants every PR must preserve

1. **`ruff check` + `ruff format --check` on `scripts/`** — zero warnings.
2. **All tests pass** — `python3 -m unittest discover -s scripts/tests`.
3. **All 5 drift checks pass** — run the commands above or let pre-commit do it.
4. **`jni-utils.h` null-guard rule** — every `env->NewObject(...)` line in any
   `make_*` helper must be immediately followed by `if (!<varname>) return nullptr;`.
   Enforced by `test_memory.py::TestJniUtilsQuality::test_new_object_null_guard`.
5. **`const char*` → `String`, mutable `char*` → `ByteArray`** — do not map
   non-const `char*` to `String` in the reverse generator.
6. **Version + CHANGELOG in sync** — bump `pyproject.toml` version and add a
   `CHANGELOG.md` entry in the same commit.

## How to add a new type

1. Add a `TypeInfo` entry to `TYPE_MAP` in `scripts/_types.py`
2. Add a matching entry to `RETURN_MAP` in `scripts/_types.py`
3. Add `extract_*` (param) and/or `make_*` (return) helpers to `jni-utils.h`
   — **null-guard `NewObject` immediately after the call**
4. Add a `_MAKE_HELPER_MAP` entry in `scripts/_types.py`
5. Write tests in `scripts/tests/test_generator.py`
6. Update `docs/type-support-matrix.md`

## Versioning

- Format: `MAJOR.MINOR.PATCH` — currently in `1.x` beta
- Bump patch for bug fixes, minor for new types/features
- Every release: update `pyproject.toml` version + `CHANGELOG.md` entry + `git tag vX.Y.Z`
- Release workflow fires automatically on `v*.*.*` tags

## Exit codes

| Code | Constant | Meaning |
|---|---|---|
| 0 | EXIT_OK | Success |
| 1 | EXIT_USAGE | Bad arguments or missing file |
| 2 | EXIT_PARSE | Kotlin/C parse error |
| 3 | EXIT_DRIFT | `--check` found stale files |
