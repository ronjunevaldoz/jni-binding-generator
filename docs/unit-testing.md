# Unit testing guide

All tests live under `scripts/tests/` and run with Python's built-in `unittest`
(52 tests across 4 suites). No extra dependencies are required beyond a JDK
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
| `TestJvmName` | `@JvmName("x")` overrides Kotlin function name in generated output |
| `TestTopLevelFun` | Top-level `external fun` uses `<FilenameKt>` class; fallback to `Native` when no filename |
| `TestMangling` | JNI name mangling: underscores → `_1`, dots → `_`, `$` → `_00024`, no-package case |

### `test_generator.py` — C++ code generation

Tests `generate_function()`, `generate_file()`, and `generate_test_file()`. Each
test parses a minimal inline Kotlin snippet and asserts on the generated C++ string.

| Test | What it pins |
|---|---|
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

### `test_driver.py` — CLI driver behaviour

Tests `main()` end-to-end using real temp directories. Covers the full write
→ check → drift cycle.

| Class | What it covers |
|---|---|
| `TestIncrementalWrites` | First run writes the file; second run with identical content does not touch mtime |
| `TestCheckMode` | `--check` passes when up-to-date, fails on missing output, fails after source change, never writes |
| `TestOutputNaming` | Two `Foo` classes in different packages get qualified names (`com_a_Foo_jni.gen.cpp`); unique class keeps short name |
| `TestGenerateTests` | `--generate-tests` writes `*_jni_test.gen.cpp`, content has correct structure, second run is incremental (mtime unchanged) |
| `TestErrors` | Missing source path → `EXIT_USAGE`; unknown lowercase type → `EXIT_PARSE` with line number and function name in stderr |

### `test_integration.py` — compile check

Generates a C++ binding from an inline Kotlin snippet and compiles it with the
system C++ compiler against the real JDK `jni.h`. The fixture covers every
supported Kotlin type: all primitive scalars, all array variants (`ByteArray`
through `BooleanArray`), all `List<T>` / `Set<T>` / `Map<K,V>` combinations,
nested collections, enums, nullable params, and void return.

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
