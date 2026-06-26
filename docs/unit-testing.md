# Unit testing guide

All tests live under `scripts/tests/` and run with Python's built-in `unittest`
(216 tests across 6 suites). No extra dependencies are required beyond a JDK
(for the compilation test).

## Running the tests

```bash
# All suites at once
python3 -m unittest discover -s scripts/tests

# Verbose (prints each test name)
python3 -m unittest discover -s scripts/tests -v

# Single suite
python3 -m unittest scripts/tests/test_generator
```

The pre-commit hook runs the full suite automatically on every commit that
touches `scripts/*.py` or `scripts/*.h`:

```yaml
- id: jni-generator-tests
  entry: python3 -m unittest discover -s scripts/tests
```

## Test suites

### `test_parser.py` — Kotlin source parsing

Tests `parse_kotlin_source()`, `mangle()`, and `jni_function_name()`.

| Class | What it covers |
|---|---|
| `TestKotlinFunctionParser` | Package, class name, param/return parsing, nullable `?`, default values, multiline signatures, `object` → `is_static` |
| `TestUnsupportedConstructs` | Hard errors for `suspend external fun`, extension receivers, `vararg`, function-type params |
| `TestNestedClass` | `Outer$Inner` class name; `$` → `_00024` in generated JNI symbol |
| `TestJvmName` | `@JvmName("x")` overrides Kotlin function name; does not bleed into the next function |
| `TestTopLevelFun` | Top-level `external fun` uses `<FilenameKt>` class; fallback to `Native` when no filename |
| `TestMangling` | JNI name mangling: underscores → `_1`, dots → `_`, `$` → `_00024`, no-package case |
| `TestMultiClass` | `parse_kotlin_source_multi()`: two classes in one file produce two `KotlinParsed` results, each with the correct functions and shared package |

### `test_generator.py` — C++ code generation

Tests `generate_function()`, `generate_file()`, and `generate_test_file()`. Each
test parses a minimal inline Kotlin snippet and asserts on the generated C++ string.

| Class / Test | What it pins |
|---|---|
| **`TestGeneration`** | Core generation tests (all rows below) |
| `test_signature_and_marshalling` | Full JNI signature, `jstring2string`, `static_cast`, `extern "C" JNIEXPORT` header |
| `test_handle_and_string_error_checks` | Null-handle guard, empty-string guard, `jbyteArray` nullable return |
| `test_array_and_boolean_marshalling` | `extract_string_array`, `bool` cast, `jintArray` return |
| `test_void_return` | `void` return, bare `return;`, no `return ;` with space |
| `test_static_object_receiver` | `jclass clazz` vs `jobject thiz` for `object` declarations |
| `test_unknown_type_is_actionable` | Lowercase-start type raises `UnknownTypeError` mentioning `TYPE_MAP` |
| `test_enum_type_maps_to_ordinal` | Capitalized unknown type → `enum_ordinal`, `int32_t` |
| `test_nullable_params_skip_required_guards` | `Long?` / `String?` are marshalled but get no guard |
| `test_non_nullable_still_guarded` | Non-nullable `Long` / `String` get the null/empty guard |
| `test_double_array_and_bool_array` | `DoubleArray` / `BooleanArray` param types + `ShortArray` return |
| `test_short_array` | `ShortArray` param + return |
| `test_list_bool_return_hints_make_helper` | TODO body contains `make_list_bool` hint |
| `test_list_byte_return_hints_make_helper` | TODO body contains `make_list_byte` hint |
| `test_map_int_string_return_hints_make_helper` | TODO body contains `make_map_int_string` hint |
| `test_generate_test_file_structure` | Generated test file has header, `if (false)`, `int main()`, named check function |
| `test_generate_test_file_covers_param_helpers` | Extract helper calls present for String and Int params |
| `test_generate_test_file_covers_make_helpers` | `make_list_string`, `make_map_string_int`, `make_set_string` present for return types |
| `test_generate_test_file_skips_void` | Void-return functions emit no `make_*` call |
| `test_full_file_has_header_and_includes` | File header, `#include <jni.h>`, `#include "jni-utils.h"`, correct `extern "C"` count |
| `TestNewTypeFamily` | `List<Short>`, all `Set<*>` variants, all `Map<*,*>` variants, `List<List<*>>` — extract/make helpers |
| `TestNestedListLongDoubleBoolean` | `List<List<Long/Double/Boolean>>` — param and return via `generate_file()` |
| `TestNestedListString` | `List<List<String>>` — param and return |
| `TestRemainingTypeCoverage` | All 22 previously-untested types: `List<Int/Float>`, `List<List<Int/Float>>`, `Set<Int/Boolean/Double>`, `Map<String,String>`, `Map<Int,Int/Long/Float/Boolean/String>`, `FloatArray`, `LongArray`, `Array<Byte/Boolean/Short/Int/Long/Float/Double>`, `Unit` |

### `test_driver.py` — CLI driver behaviour

Tests `main()` end-to-end using real temp directories. Covers the full write
→ check → drift cycle.

| Class | What it covers |
|---|---|
| `TestIncrementalWrites` | First run writes the file; second run with identical content does not touch mtime |
| `TestCheckMode` | `--check` passes when up-to-date, fails on missing output, fails after source change, never writes |
| `TestOutputNaming` | Two `Foo` classes in different packages get qualified names (`com_a_Foo_jni.gen.cpp`); unique class keeps short name |
| `TestGenerateTests` | `--generate-tests` writes `*_jni_test.gen.cpp`, content has correct structure, second run is incremental (mtime unchanged); `--check --generate-tests` detects missing, stale, and up-to-date test files without writing |
| `TestDryRun` | `--dry-run` prints generated code and `[dry-run]` marker to stdout; never writes files |
| `TestErrors` | Missing source path → `EXIT_USAGE`; source with no `external fun` → `EXIT_USAGE`; unknown lowercase type → `EXIT_PARSE` with line number and function name in stderr |
| `TestTypeMap` | `--type-map` JSON injects custom types into the binding; missing file → `EXIT_USAGE` |
| `TestDiffMode` | `--diff` prints a unified diff but never writes files; reports "unchanged" when output is up-to-date |
| `TestVerboseMode` | `--verbose` prints class and function names to stdout |
| `TestPackageFilter` | `--package-filter` restricts output to matching packages; all packages included when flag is absent |
| `TestIosCinterop` | `--ios-cinterop` writes `.def` and `include/*.h` files; header contains C types; `.def` has `headers`/`headerFilter` lines and package comment; second run is incremental (mtime unchanged); `--check` and `--dry-run` never write cinterop files |
| `TestStrictTypes` | `--strict-types` passes on a fully-mapped header, exits `EXIT_PARSE` on an unknown type, does nothing without the flag |
| `TestScoreCommand` | `--score` exits `EXIT_OK` and does not require `--output` |

### `test_memory.py` — JNI local-reference static analysis

Static-analysis tests over `jni-utils.h` that verify every JNI local-reference
acquisition is paired with a matching release. No runtime JVM required.

| Class | What it covers |
|---|---|
| `TestGetStringUTFCharsLifecycle` | Every `GetStringUTFChars` paired with `ReleaseStringUTFChars` (EP-6) |
| `TestFindClassBalance` | `DeleteLocalRef` count ≥ `FindClass` count per function |
| `TestGetObjectArrayElementRelease` | Every `GetObjectArrayElement` result has a matching `DeleteLocalRef` |
| `TestNewStringUTFInLoop` | `NewStringUTF` inside a loop → `DeleteLocalRef` present |
| `TestBoxedObjectCreationInLoop` | `CallStaticObjectMethod` inside a loop → `DeleteLocalRef` present |
| `TestIteratorLoopCleanup` | Iterator-loop functions delete `entry`/key/value and the iterator itself |
| `TestExtractMakeHelpersHaveCleanup` | Every `extract_*/make_*` that creates local refs has a `DeleteLocalRef` |
| `TestNestedListHelpers` | All 16 `extract/make_list_list_*` helpers release inner-list refs and class refs |
| `TestBoxedArrayHelpers` | `extract_boxed_*_array` helpers delete each element ref and the class ref |
| `TestJniUtilsQuality` | Every `env->NewObject(…)` call in a `make_*` helper is immediately followed by a null-guard `if (!var) return nullptr;` (EP-6b invariant) |
| `TestHeaderPresent` | Smoke test: header exists, is non-empty, and has >20 helpers |

Helpers using `Get*ArrayRegion` (primitive arrays copied into a C buffer, no local ref
created) are correctly excluded from the `DeleteLocalRef` coverage check.

### `test_kotlin_gen.py` — C header → Kotlin reverse generator

Tests `parse_c_header()`, `generate_kotlin_stubs()`, `generate_kotlin_from_header()`,
and the `--kotlin-from-header` CLI flag.

| Class | What it covers |
|---|---|
| `TestReturnTypeMapping` | `void`→`Unit`, `int32_t`→`Int`, `void*`→`Long`, `const char*`→`String`; returned pointer arrays are `Long` handles (not `FloatArray`/`IntArray`); `bool`, `float`, `double`, `int64_t` scalar returns; unknown struct pointer gets `Long /* TODO */` |
| `TestParamTypeMapping` | `void*`→`Long`, `const char*`→`String`, `int32_t`→`Int`; `float*`→`FloatArray`, `uint8_t*`→`ByteArray`; `bool`→`Boolean`; unknown type→`Long /* TODO */`; `(void)` and `()` produce no params |
| `TestNameConversion` | Snake→camelCase function names; already-camelCase passed through; single-word names; snake→camel param names; unnamed params get `paramN` placeholders; `_header_to_object_name` for various filename patterns |
| `TestSourceStripping` | Line comments, block comments, preprocessor (`#pragma once`, `#include`), struct blocks, typedef function pointers, `extern "C" { }` wrappers, `const` qualifier on param types |
| `TestParserEdgeCases` | Four-function header parsed in order; duplicate names deduplicated; no-function source returns empty list; multi-param parsing; `int32_t *out` (star on name) → `IntArray` |
| `TestGenerateKotlinStubs` | `package` line present; `object` declaration; all three `external fun` names; `void` return omits `: Unit`; non-void return includes type; empty source returns `""`; missing package gets `TODO`; `System.loadLibrary` hint; file ends with `}` |
| `TestKotlinFromHeaderCLI` | `--kotlin-from-header` writes the `.kt` file with the correct functions; `--dry-run` prints but does not write; `--check` returns `EXIT_DRIFT` on missing file and `EXIT_OK` when up-to-date; `--kotlin-package` sets the package; missing header → `EXIT_USAGE`; mode works without `--kotlin-source` |

### `test_integration.py` — compile check

`TestGeneratedCompiles` generates a C++ binding from an inline Kotlin snippet and
compiles it with the system C++ compiler against the real JDK `jni.h`. The fixture
covers every supported Kotlin type: all primitive scalars, all array variants
(`ByteArray` through `BooleanArray`), all `List<T>` / `Set<T>` / `Map<K,V>`
combinations, nested collections, enums, nullable params, and void return.

The test skips automatically when no compiler or no JDK headers are found, so
it never breaks CI in minimal environments. Set `JAVA_HOME` to point the test
at a specific JDK.

```bash
# Force a specific JDK
JAVA_HOME=/usr/lib/jvm/java-17-openjdk python3 -m unittest discover -s scripts/tests -p test_integration.py
```

## Compile-time type-check files (`--generate-tests`)

Passing `--generate-tests` to the generator emits a `*_jni_test.gen.cpp`
alongside each binding. Every `extract_*` and `make_*` helper call is placed
inside an `if (false)` block — the compiler verifies the types of each call
without executing it. Any signature regression in `jni-utils.h` becomes a
compile error rather than a silent runtime bug.

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated \
    --generate-tests
```

This produces `examples/sample-binding/generated/SampleEngine_jni_test.gen.cpp`.
Compile it with `-fsyntax-only` as part of CI:

```bash
clang++ -std=c++17 -fsyntax-only \
    -I$JAVA_HOME/include -I$JAVA_HOME/include/darwin \
    -Iscripts \
    examples/sample-binding/generated/SampleEngine_jni_test.gen.cpp
```

The file is incremental — it is only rewritten when its content changes.

## Writing a new test

### Adding a type mapping test

The fastest way to verify a new type is a one-liner parse + assertion:

```python
def test_my_new_type(self):
    parsed = gen.parse_kotlin_source(
        "package a.b\nclass N { external fun f(data: MyType): MyType }"
    )
    out = gen.generate_function(parsed, parsed.functions[0])
    self.assertIn("extract_my_type(env, data)", out)    # param marshalling
    self.assertIn("JNIEXPORT jmytype JNICALL", out)     # return JNI type
```

### Adding a return-hint test

```python
def test_my_collection_return_hint(self):
    parsed = gen.parse_kotlin_source(
        "package a.b\nclass N { external fun f(h: Long): MyCollection }"
    )
    out = gen.generate_function(parsed, parsed.functions[0])
    self.assertIn("make_my_collection", out)
```

### Adding a driver test

Driver tests create real files in a `tempfile.TemporaryDirectory`. Use the
`DriverTestCase` base class — it sets up `self.src`, `self.out`, and
`self.run_gen(*extra)`:

```python
class TestMyScenario(DriverTestCase):
    def test_something(self):
        (self.src / "MyClass.kt").write_text(MY_SOURCE, encoding="utf-8")
        rc = self.run_gen()
        self.assertEqual(rc, gen.EXIT_OK)
        self.assertTrue((self.out / "MyClass_jni.gen.cpp").exists())
```

## Exit codes

| Code | Constant | Meaning |
|---|---|---|
| 0 | `EXIT_OK` | Success |
| 1 | `EXIT_USAGE` | No input files / bad path |
| 2 | `EXIT_PARSE` | Unrecognized type or parse failure |
| 3 | `EXIT_DRIFT` | `--check` found out-of-date or missing output |
