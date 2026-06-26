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
| `ByteArray`  | ✅ | ✅ | `std::vector<uint8_t>`  | `jbyteArray`  |
| `IntArray`   | ✅ | ✅ | `std::vector<int32_t>`  | `jintArray`   |
| `LongArray`  | ✅ | ✅ | `std::vector<int64_t>`  | `jlongArray`  |
| `FloatArray` | ✅ | ✅ | `std::vector<float>`    | `jfloatArray` |

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
| `List<Boolean>` | ✅ | ✅ | `std::vector<bool>`         | `jobject` | `extract_list_bool`     | —                  |
| `List<Byte>`    | ✅ | ✅ | `std::vector<int8_t>`       | `jobject` | `extract_list_byte`     | —                  |

For return types the generated TODO body includes a comment like:
```
// Return: use make_list_string(env, yourResult) to build the jobject.
```

## Map (java.util.Map)

| Kotlin type              | As param | As return | C++ type                                          | JNI type  |
|---|:---:|:---:|---|---|
| `Map<String, String>`    | ✅ | ✅ | `std::unordered_map<std::string, std::string>` | `jobject` |
| `Map<String, Int>`       | ✅ | ✅ | `std::unordered_map<std::string, int32_t>`     | `jobject` |
| `Map<Int, String>`       | ✅ | ✅ | `std::unordered_map<int32_t, std::string>`     | `jobject` |

## Complex types (not supported)

| Kotlin type               | As param | As return | Notes |
|---|:---:|:---:|---|
| Data class / POJO         | ❌ | ❌ | Requires per-field reflection; out of scope |
| `Enum` (any named enum)   | ✅ | ✅ | Any capitalized Kotlin type is auto-detected as an enum. Param → `int32_t` via `enum_ordinal(env, obj)`. Return → `jint` ordinal; convert back with `MyEnum.values()[result]` on Kotlin side. |
| `Set<T>`                  | ❌ | ❌ | No planned timeline |
| `Array<T>` (non-String)   | ❌ | ❌ | Use `TArray` typed arrays instead |
| Nested `List<List<T>>`    | ❌ | ❌ | No planned timeline |

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
