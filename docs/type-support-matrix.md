# Type support matrix

Status legend: ✅ supported · ❌ not supported

## Primitives

| Kotlin type | As param | As return | C++ type | JNI type | Nullable `?` |
|---|:---:|:---:|---|---|:---:|
| `Int`     | ✅ | ✅ | `int32_t`        | `jint`     | ✅ |
| `Long`    | ✅ | ✅ | `void*` (handle) | `jlong`    | ✅ |
| `Float`   | ✅ | ✅ | `float`          | `jfloat`   | ✅ |
| `Double`  | ✅ | ✅ | `double`         | `jdouble`  | ✅ |
| `Boolean` | ✅ | ✅ | `bool`           | `jboolean` | ✅ |
| `Short`   | ✅ | ✅ | `int16_t`        | `jshort`   | ✅ |
| `Byte`    | ✅ | ✅ | `int8_t`         | `jbyte`    | ✅ |

> `Long` is treated as an opaque native handle (`void*`). A plain `Int64` that
> isn't a pointer should be post-cast in the hand-written body.

## String

| Kotlin type | As param | As return | C++ type | JNI type | Nullable `?` |
|---|:---:|:---:|---|---|:---:|
| `String` | ✅ | ✅ | `std::string` | `jstring` | ✅ |

Non-nullable `String` params get an `.empty()` guard; nullable ones (`String?`) do not.

> **`--kotlin-from-header` only:** `const char*` maps to `String` (input). Mutable `char*`
> (no `const`) maps to `ByteArray` — it is treated as a C output buffer, which Java/Kotlin
> cannot represent as an immutable `String`.

## Void

| Kotlin type | As param | As return | C++ type | JNI type |
|---|:---:|:---:|---|---|
| `Unit` | — | ✅ | `void` | `void` |

## Primitive arrays

| Kotlin type    | As param | As return | C++ type                | JNI type        |
|---|:---:|:---:|---|---|
| `ByteArray`    | ✅ | ✅ | `std::vector<uint8_t>`  | `jbyteArray`    |
| `IntArray`     | ✅ | ✅ | `std::vector<int32_t>`  | `jintArray`     |
| `LongArray`    | ✅ | ✅ | `std::vector<int64_t>`  | `jlongArray`    |
| `FloatArray`   | ✅ | ✅ | `std::vector<float>`    | `jfloatArray`   |
| `ShortArray`   | ✅ | ✅ | `std::vector<int16_t>`  | `jshortArray`   |
| `DoubleArray`  | ✅ | ✅ | `std::vector<double>`   | `jdoubleArray`  |
| `BooleanArray` | ✅ | ✅ | `std::vector<bool>`     | `jbooleanArray` |

Nullable not supported for array types (JNI doesn't distinguish null vs empty array in practice).

## Object arrays (`Array<T>`)

Boxed-object arrays. Each element is unboxed via `CallObjectMethod` → primitive extract.

| Kotlin type      | As param | As return | C++ type                       | JNI type       | Helper (param)                |
|---|:---:|:---:|---|---|---|
| `Array<String>`  | ✅ | ✅ | `std::vector<std::string>`  | `jobjectArray` | `extract_string_array` / `make_boxed_string_array`      |
| `Array<Byte>`    | ✅ | ✅ | `std::vector<int8_t>`       | `jobjectArray` | `extract_boxed_byte_array` / `make_boxed_byte_array`    |
| `Array<Short>`   | ✅ | ✅ | `std::vector<int16_t>`      | `jobjectArray` | `extract_boxed_short_array` / `make_boxed_short_array`  |
| `Array<Int>`     | ✅ | ✅ | `std::vector<int32_t>`      | `jobjectArray` | `extract_boxed_int_array` / `make_boxed_int_array`      |
| `Array<Long>`    | ✅ | ✅ | `std::vector<int64_t>`      | `jobjectArray` | `extract_boxed_long_array` / `make_boxed_long_array`    |
| `Array<Float>`   | ✅ | ✅ | `std::vector<float>`        | `jobjectArray` | `extract_boxed_float_array` / `make_boxed_float_array`  |
| `Array<Double>`  | ✅ | ✅ | `std::vector<double>`       | `jobjectArray` | `extract_boxed_double_array` / `make_boxed_double_array`|
| `Array<Boolean>` | ✅ | ✅ | `std::vector<bool>`         | `jobjectArray` | `extract_boxed_bool_array` / `make_boxed_bool_array`    |

## List (java.util.List)

| Kotlin type     | As param | As return | C++ type                    | JNI type  | Helper (param)        | Helper (return)      |
|---|:---:|:---:|---|---|---|---|
| `List<String>`  | ✅ | ✅ | `std::vector<std::string>`  | `jobject` | `extract_list_string`  | `make_list_string`   |
| `List<Int>`     | ✅ | ✅ | `std::vector<int32_t>`      | `jobject` | `extract_list_int`     | `make_list_int`      |
| `List<Long>`    | ✅ | ✅ | `std::vector<int64_t>`      | `jobject` | `extract_list_long`    | `make_list_long`     |
| `List<Float>`   | ✅ | ✅ | `std::vector<float>`        | `jobject` | `extract_list_float`   | `make_list_float`    |
| `List<Double>`  | ✅ | ✅ | `std::vector<double>`       | `jobject` | `extract_list_double`  | `make_list_double`   |
| `List<Boolean>` | ✅ | ✅ | `std::vector<bool>`         | `jobject` | `extract_list_bool`    | `make_list_bool`     |
| `List<Byte>`    | ✅ | ✅ | `std::vector<int8_t>`       | `jobject` | `extract_list_byte`    | `make_list_byte`     |
| `List<Short>`   | ✅ | ✅ | `std::vector<int16_t>`      | `jobject` | `extract_list_short`   | `make_list_short`    |

## Nested List (List<List<T>>)

| Kotlin type          | As param | As return | C++ type                             | JNI type  | Helper (param)              | Helper (return)            |
|---|:---:|:---:|---|---|---|---|
| `List<List<String>>` | ✅ | ✅ | `std::vector<std::vector<std::string>>` | `jobject` | `extract_list_list_string` | `make_list_list_string` |
| `List<List<Int>>`    | ✅ | ✅ | `std::vector<std::vector<int32_t>>`     | `jobject` | `extract_list_list_int`    | `make_list_list_int`    |
| `List<List<Long>>`   | ✅ | ✅ | `std::vector<std::vector<int64_t>>`     | `jobject` | `extract_list_list_long`   | `make_list_list_long`   |
| `List<List<Float>>`  | ✅ | ✅ | `std::vector<std::vector<float>>`       | `jobject` | `extract_list_list_float`  | `make_list_list_float`  |
| `List<List<Double>>` | ✅ | ✅ | `std::vector<std::vector<double>>`      | `jobject` | `extract_list_list_double` | `make_list_list_double` |
| `List<List<Boolean>>`| ✅ | ✅ | `std::vector<std::vector<bool>>`        | `jobject` | `extract_list_list_bool`   | `make_list_list_bool`   |
| `List<List<Byte>>`   | ✅ | ✅ | `std::vector<std::vector<int8_t>>`      | `jobject` | `extract_list_list_byte`   | `make_list_list_byte`   |
| `List<List<Short>>`  | ✅ | ✅ | `std::vector<std::vector<int16_t>>`     | `jobject` | `extract_list_list_short`  | `make_list_list_short`  |

## Set (java.util.Set)

| Kotlin type     | As param | As return | C++ type                           | JNI type  | Helper (param)       | Helper (return)     |
|---|:---:|:---:|---|---|---|---|
| `Set<String>`   | ✅ | ✅ | `std::unordered_set<std::string>`  | `jobject` | `extract_set_string`  | `make_set_string`   |
| `Set<Int>`      | ✅ | ✅ | `std::unordered_set<int32_t>`      | `jobject` | `extract_set_int`     | `make_set_int`      |
| `Set<Long>`     | ✅ | ✅ | `std::unordered_set<int64_t>`      | `jobject` | `extract_set_long`    | `make_set_long`     |
| `Set<Float>`    | ✅ | ✅ | `std::unordered_set<float>`        | `jobject` | `extract_set_float`   | `make_set_float`    |
| `Set<Double>`   | ✅ | ✅ | `std::unordered_set<double>`       | `jobject` | `extract_set_double`  | `make_set_double`   |
| `Set<Boolean>`  | ✅ | ✅ | `std::unordered_set<bool>`         | `jobject` | `extract_set_bool`    | `make_set_bool`     |
| `Set<Byte>`     | ✅ | ✅ | `std::unordered_set<int8_t>`       | `jobject` | `extract_set_byte`    | `make_set_byte`     |
| `Set<Short>`    | ✅ | ✅ | `std::unordered_set<int16_t>`      | `jobject` | `extract_set_short`   | `make_set_short`    |

## Map (java.util.Map)

18 combinations: 3 key types (`String`, `Int`, `Long`) × 6 value types (`String`, `Int`, `Long`, `Float`, `Double`, `Boolean`).

| Kotlin type              | As param | As return | C++ type                                           | Helper (param / return)                              |
|---|:---:|:---:|---|---|
| `Map<String, String>`    | ✅ | ✅ | `std::unordered_map<std::string, std::string>` | `extract_map_string_string` / `make_map_string_string` |
| `Map<String, Int>`       | ✅ | ✅ | `std::unordered_map<std::string, int32_t>`     | `extract_map_string_int` / `make_map_string_int`       |
| `Map<String, Long>`      | ✅ | ✅ | `std::unordered_map<std::string, int64_t>`     | `extract_map_string_long` / `make_map_string_long`     |
| `Map<String, Float>`     | ✅ | ✅ | `std::unordered_map<std::string, float>`       | `extract_map_string_float` / `make_map_string_float`   |
| `Map<String, Double>`    | ✅ | ✅ | `std::unordered_map<std::string, double>`      | `extract_map_string_double` / `make_map_string_double` |
| `Map<String, Boolean>`   | ✅ | ✅ | `std::unordered_map<std::string, bool>`        | `extract_map_string_bool` / `make_map_string_bool`     |
| `Map<Int, String>`       | ✅ | ✅ | `std::unordered_map<int32_t, std::string>`     | `extract_map_int_string` / `make_map_int_string`       |
| `Map<Int, Int>`          | ✅ | ✅ | `std::unordered_map<int32_t, int32_t>`         | `extract_map_int_int` / `make_map_int_int`             |
| `Map<Int, Long>`         | ✅ | ✅ | `std::unordered_map<int32_t, int64_t>`         | `extract_map_int_long` / `make_map_int_long`           |
| `Map<Int, Float>`        | ✅ | ✅ | `std::unordered_map<int32_t, float>`           | `extract_map_int_float` / `make_map_int_float`         |
| `Map<Int, Double>`       | ✅ | ✅ | `std::unordered_map<int32_t, double>`          | `extract_map_int_double` / `make_map_int_double`       |
| `Map<Int, Boolean>`      | ✅ | ✅ | `std::unordered_map<int32_t, bool>`            | `extract_map_int_bool` / `make_map_int_bool`           |
| `Map<Long, String>`      | ✅ | ✅ | `std::unordered_map<int64_t, std::string>`     | `extract_map_long_string` / `make_map_long_string`     |
| `Map<Long, Int>`         | ✅ | ✅ | `std::unordered_map<int64_t, int32_t>`         | `extract_map_long_int` / `make_map_long_int`           |
| `Map<Long, Long>`        | ✅ | ✅ | `std::unordered_map<int64_t, int64_t>`         | `extract_map_long_long` / `make_map_long_long`         |
| `Map<Long, Float>`       | ✅ | ✅ | `std::unordered_map<int64_t, float>`           | `extract_map_long_float` / `make_map_long_float`       |
| `Map<Long, Double>`      | ✅ | ✅ | `std::unordered_map<int64_t, double>`          | `extract_map_long_double` / `make_map_long_double`     |
| `Map<Long, Boolean>`     | ✅ | ✅ | `std::unordered_map<int64_t, bool>`            | `extract_map_long_bool` / `make_map_long_bool`         |

## Enums

Any `^[A-Z][A-Za-z0-9_]*$` type not in `TYPE_MAP` is auto-detected as an enum:

| Kotlin type     | As param | As return | C++ type  | JNI type  | Helper              |
|---|:---:|:---:|---|---|---|
| Any named enum  | ✅ | ✅ | `int32_t` | `jint`    | `enum_ordinal(env, obj)` |

## Unsupported types

| Kotlin type        | Notes |
|---|---|
| Data class / POJO  | Requires per-field reflection; intentionally out of scope |
| `suspend fun`      | Coroutine continuation not expressible in JNI |
| Extension receiver | `fun T.f()` form not supported |
| `vararg`           | Variable-argument functions not supported |
| Function types     | `(A) -> B` lambda params not supported |

## Nullable parameters (`T?`)

All supported types accept a `?` suffix. The effect:

- Non-nullable → required-value guard emitted (null/empty check throws `IllegalArgumentException` / `IllegalStateException`)
- Nullable → guard skipped; `null` flows through to the hand-written body unchanged

## Adding a new type

1. Add a `TypeInfo` entry to `TYPE_MAP` in `scripts/_types.py`
2. Add a matching entry to `RETURN_MAP` in `scripts/_types.py`
3. Add `extract_*` (param) and/or `make_*` (return) helpers to `jni-utils.h`
4. Add a `_MAKE_HELPER_MAP` entry in `scripts/_types.py` pointing to the new `make_*` helper
5. Write a test in `scripts/tests/test_generator.py`
6. Update this file

If the helper calls JNI APIs (anything other than a pure C cast), it already
gets an `env->ExceptionCheck()` guard from `_needs_exception_check` — no
extra work needed for strings/vectors/maps.
