# Type support matrix

Status legend: ✅ supported · ⏳ planned · ❌ not supported

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

## Void

| Kotlin type | As param | As return | C++ type | JNI type |
|---|:---:|:---:|---|---|
| `Unit` | — | ✅ | `void` | `void` |

## Primitive arrays

| Kotlin type  | As param | As return | C++ type                    | JNI type      |
|---|:---:|:---:|---|---|
| `ByteArray`    | ✅ | ✅ | `std::vector<uint8_t>`  | `jbyteArray`    |
| `IntArray`     | ✅ | ✅ | `std::vector<int32_t>`  | `jintArray`     |
| `LongArray`    | ✅ | ✅ | `std::vector<int64_t>`  | `jlongArray`    |
| `FloatArray`   | ✅ | ✅ | `std::vector<float>`    | `jfloatArray`   |
| `ShortArray`   | ✅ | ✅ | `std::vector<int16_t>`  | `jshortArray`   |
| `DoubleArray`  | ✅ | ✅ | `std::vector<double>`   | `jdoubleArray`  |
| `BooleanArray` | ✅ | ✅ | `std::vector<bool>`     | `jbooleanArray` |

Nullable not supported for array types (JNI doesn't distinguish null vs empty array in practice).

## Object arrays

| Kotlin type      | As param | As return | C++ type                        | JNI type        |
|---|:---:|:---:|---|---|
| `Array<String>`  | ✅ | ✅ | `std::vector<std::string>`  | `jobjectArray`  |

## List (java.util.List)

| Kotlin type     | As param | As return | C++ type                        | JNI type  | Helper (param)          | Helper (return)    |
|---|:---:|:---:|---|---|---|---|
| `List<String>`  | ✅ | ✅ | `std::vector<std::string>`  | `jobject` | `extract_list_string`   | `make_list_string` |
| `List<Int>`     | ✅ | ✅ | `std::vector<int32_t>`      | `jobject` | `extract_list_int`      | `make_list_int`    |
| `List<Long>`    | ✅ | ✅ | `std::vector<int64_t>`      | `jobject` | `extract_list_long`     | `make_list_long`   |
| `List<Float>`   | ✅ | ✅ | `std::vector<float>`        | `jobject` | `extract_list_float`    | `make_list_float`  |
| `List<Double>`  | ✅ | ✅ | `std::vector<double>`       | `jobject` | `extract_list_double`   | `make_list_double` |
| `List<Boolean>` | ✅ | ✅ | `std::vector<bool>`         | `jobject` | `extract_list_bool`     | `make_list_bool`   |
| `List<Byte>`    | ✅ | ✅ | `std::vector<int8_t>`       | `jobject` | `extract_list_byte`     | `make_list_byte`   |
| `List<Short>`   | ✅ | ✅ | `std::vector<int16_t>`      | `jobject` | `extract_list_short`    | `make_list_short`  |

For return types the generated TODO body includes a comment like:
```
// Return: use make_list_string(env, yourResult) to build the jobject.
```

## Map (java.util.Map)

| Kotlin type              | As param | As return | C++ type                                          | JNI type  |
|---|:---:|:---:|---|---|
| `Map<String, String>`    | ✅ | ✅ | `std::unordered_map<std::string, std::string>` | `jobject` | `extract_map_string_string` / `make_map_string_string` |
| `Map<String, Int>`       | ✅ | ✅ | `std::unordered_map<std::string, int32_t>`     | `jobject` | `extract_map_string_int` / `make_map_string_int`       |
| `Map<String, Long>`      | ✅ | ✅ | `std::unordered_map<std::string, int64_t>`     | `jobject` | `extract_map_string_long` / `make_map_string_long`     |
| `Map<String, Float>`     | ✅ | ✅ | `std::unordered_map<std::string, float>`       | `jobject` | `extract_map_string_float` / `make_map_string_float`   |
| `Map<String, Boolean>`   | ✅ | ✅ | `std::unordered_map<std::string, bool>`        | `jobject` | `extract_map_string_bool` / `make_map_string_bool`     |
| `Map<Int, String>`       | ✅ | ✅ | `std::unordered_map<int32_t, std::string>`     | `jobject` | `extract_map_int_string` / `make_map_int_string`       |
| `Map<String, Double>`    | ✅ | ✅ | `std::unordered_map<std::string, double>`      | `jobject` | `extract_map_string_double` / `make_map_string_double` |
| `Map<Int, Double>`       | ✅ | ✅ | `std::unordered_map<int32_t, double>`          | `jobject` | `extract_map_int_double` / `make_map_int_double`       |
| `Map<Long, Int>`         | ✅ | ✅ | `std::unordered_map<int64_t, int32_t>`         | `jobject` | `extract_map_long_int` / `make_map_long_int`           |
| `Map<Long, Long>`        | ✅ | ✅ | `std::unordered_map<int64_t, int64_t>`         | `jobject` | `extract_map_long_long` / `make_map_long_long`         |
| `Map<Long, String>`      | ✅ | ✅ | `std::unordered_map<int64_t, std::string>`     | `jobject` | `extract_map_long_string` / `make_map_long_string`     |
| `Map<Long, Float>`       | ✅ | ✅ | `std::unordered_map<int64_t, float>`           | `jobject` | `extract_map_long_float` / `make_map_long_float`       |
| `Map<Long, Double>`      | ✅ | ✅ | `std::unordered_map<int64_t, double>`          | `jobject` | `extract_map_long_double` / `make_map_long_double`     |
| `Map<Long, Boolean>`     | ✅ | ✅ | `std::unordered_map<int64_t, bool>`            | `jobject` | `extract_map_long_bool` / `make_map_long_bool`         |

## Complex types (not supported)

| Kotlin type               | As param | As return | Notes |
|---|:---:|:---:|---|
| Data class / POJO         | ❌ | ❌ | Requires per-field reflection; intentionally out of scope |
| `Enum` (any named enum)   | ✅ | ✅ | Auto-detected: any `^[A-Z][A-Za-z0-9_]*$` type → `int32_t` ordinal via `enum_ordinal(env, obj)` |
| `Set<String>`             | ✅ | ✅ | `std::unordered_set<std::string>` via `extract_set_string` / `make_set_string` |
| `Set<Int>`                | ✅ | ✅ | `std::unordered_set<int32_t>` via `extract_set_int` / `make_set_int` |
| `Set<Long>`               | ✅ | ✅ | `std::unordered_set<int64_t>` via `extract_set_long` / `make_set_long` |
| `Set<Float>`              | ✅ | ✅ | `std::unordered_set<float>` via `extract_set_float` / `make_set_float` |
| `Array<Int>`              | ✅ | ✅ | `jobjectArray` → `std::vector<int32_t>` via `extract_boxed_int_array` |
| `Array<Long>`             | ✅ | ✅ | `jobjectArray` → `std::vector<int64_t>` via `extract_boxed_long_array` |
| `Array<Float>`            | ✅ | ✅ | `jobjectArray` → `std::vector<float>` via `extract_boxed_float_array` |
| `Array<Double>`           | ✅ | ✅ | `jobjectArray` → `std::vector<double>` via `extract_boxed_double_array` |
| `List<List<String>>`      | ✅ | ✅ | Nested list via `extract_list_list_string` / `make_list_list_string` |

## Nullable parameters (`T?`)

All supported types accept a `?` suffix. The effect:

- Non-nullable → required-value guard emitted (null/empty check throws `IllegalArgumentException` / `IllegalStateException`)
- Nullable → guard skipped; `null` flows through to the hand-written body unchanged

## Adding a new type

1. Add a `TypeInfo` entry to `TYPE_MAP` in `jni-binding-generator.py`
2. Add a matching entry to `RETURN_MAP`
3. Add a helper to `jni-utils.h` (`extract_*` for params, `make_*` for returns)
4. If the helper calls JNI APIs (anything other than a pure C cast), it already
   gets an `env->ExceptionCheck()` guard from `_needs_exception_check` — no
   extra work needed for strings/vectors/maps
5. Update this file
