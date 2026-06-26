# Memory management in generated JNI bindings

This document explains the local-reference contract used by `jni-utils.h` helpers
and what hand-written native bodies must do to avoid leaks.

## JNI local references

Every JNI object returned by `FindClass`, `NewObject`, `CallObjectMethod`, etc. is a
*local reference* — it is valid only for the duration of the native call and is freed
automatically when the call returns. The JVM guarantees at least 16 local slots per
native frame (most runtimes give 512+). If you create more than the limit without
releasing them you get `JNI DETECTED ERROR … local reference table overflow`.

## What `jni-utils.h` helpers do

Every helper (`extract_*`, `make_*`) owns all local refs it creates internally and
releases them before returning. Callers do not need to release any JNI objects the
helpers look up internally (classes, method IDs, iterator objects, etc.).

```
// Safe — extract_list_string manages its own refs internally.
std::vector<std::string> tags = extract_list_string(env, tagList);
```

## Ownership of `make_*` return values

`make_list_*`, `make_set_*`, and `make_map_*` return a **new local reference** (`jobject`).
The caller owns this reference.

**If you return it directly from the JNI function**, the JVM takes ownership — no action needed:

```cpp
// Correct: returning the jobject as the function's return value.
return make_list_string(env, myStrings);
```

**If you store or pass it and then return something else**, delete it when done:

```cpp
jobject result = make_list_string(env, myStrings);
do_something_with(result);
env->DeleteLocalRef(result);   // required — you're not returning it
return someOtherValue;
```

**Never** store a local ref across a JNI call boundary or in a field/global without
promoting it to a global ref with `NewGlobalRef`.

## Large-loop pattern — `PushLocalFrame` / `PopLocalFrame`

Helpers that iterate (extract_list_*, extract_map_*, extract_set_*) call
`DeleteLocalRef` on each element inside the loop, so the ref count stays bounded
regardless of collection size.

If your hand-written body creates local refs in a loop, use frames:

```cpp
for (int i = 0; i < count; ++i) {
    if (env->PushLocalFrame(16) < 0) return nullptr; // OOM
    // ... create local refs freely ...
    env->PopLocalFrame(nullptr); // frees all refs created since Push
}
```

## The EP-6 fixes in `jstring2string`

The `jstring2string` helper holds a `GetStringUTFChars` pin. It converts the pinned
chars to `std::string` inside a `try/catch` so that the pin is always released even
if the heap allocation throws `std::bad_alloc` (EP-6a fix). The `extract_string_array`
helper converts each element to `std::string` before calling `push_back` for the same
reason (EP-6b fix).

## Global references

None of the generated code or `jni-utils.h` uses `NewGlobalRef`. If your hand-written
body needs to cache a class or object across multiple JNI calls (e.g. storing in a
`static` or a C++ singleton), you must promote it:

```cpp
// In your hand-written body or an init function:
static jclass g_myClass = nullptr;
if (!g_myClass) {
    jclass local = env->FindClass("com/example/MyClass");
    g_myClass = static_cast<jclass>(env->NewGlobalRef(local));
    env->DeleteLocalRef(local);
}
```

Release global refs when the native library is unloaded via `JNI_OnUnload`:

```cpp
void JNI_OnUnload(JavaVM* vm, void*) {
    JNIEnv* env;
    vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    env->DeleteGlobalRef(g_myClass);
}
```

## Automated memory-safety tests

`scripts/tests/test_memory.py` runs static analysis over every helper in `jni-utils.h`
at CI time. It checks:

| Test class | What it verifies |
|---|---|
| `TestGetStringUTFCharsLifecycle` | Every `GetStringUTFChars` is paired with `ReleaseStringUTFChars` (EP-6) |
| `TestFindClassBalance` | `DeleteLocalRef` count ≥ `FindClass` count per function |
| `TestGetObjectArrayElementRelease` | Every `GetObjectArrayElement` result has a matching `DeleteLocalRef` |
| `TestNewStringUTFInLoop` | `NewStringUTF` inside a loop → `DeleteLocalRef` present |
| `TestBoxedObjectCreationInLoop` | `CallStaticObjectMethod` inside a loop → `DeleteLocalRef` present |
| `TestIteratorLoopCleanup` | Iterator-loop (`hasNextM`) functions delete `entry`/key/value and the iterator itself |
| `TestExtractMakeHelpersHaveCleanup` | Every `extract_*/make_*` that creates local refs has a `DeleteLocalRef` |
| `TestNestedListHelpers` | All 16 `extract/make_list_list_*` helpers release inner-list refs and class refs |
| `TestBoxedArrayHelpers` | `extract_boxed_*_array` helpers delete each element ref and the class ref |

Helpers that use `Get*ArrayRegion` (primitive arrays copied into a C buffer without creating
local refs) are correctly excluded from the `DeleteLocalRef` coverage check.

## Per-helper leak status

Full audit completed 2026-06-26; counts updated 2026-06-26 as new type families were added.
All helpers verified clean. Static regression tests in `test_memory.py` guard every family.

| Helper family | Count | Local refs released | Notes |
|---|---|---|---|
| `extract_*_array` (primitive, region-copy) | 7 | N/A | `Get*ArrayRegion` — no local refs created |
| `extract_string_array` | 1 | ✅ | `DeleteLocalRef(element)` per-element (EP-6b) |
| `extract_list_*` | 8 | ✅ | `DeleteLocalRef(elem)` in loop + all class refs |
| `make_list_*` | 8 | ✅ | `DeleteLocalRef(boxed)` in loop + all class refs |
| `extract_set_*` | 8 | ✅ | `DeleteLocalRef(elem)` + `iter` + all class refs |
| `make_set_*` | 8 | ✅ | `DeleteLocalRef(boxed)` + all class refs |
| `extract_map_*` | 18 | ✅ | `DeleteLocalRef(entry/k/v)` in loop + `iter`/`entrySet` + all class refs |
| `make_map_*` | 18 | ✅ | `DeleteLocalRef(prev)` if non-null + `jk`/`jv` in loop + all class refs |
| `extract_boxed_*_array` | 7 | ✅ | `DeleteLocalRef(elem)` per-element + class ref |
| `extract_list_list_*` | 8 | ✅ | `DeleteLocalRef(inner)` per iteration + `listCls` |
| `make_list_list_*` | 8 | ✅ | `DeleteLocalRef(innerList)` per iteration + `cls` |
| `jstring2string` | 1 | ✅ | `ReleaseStringUTFChars` in try + catch (EP-6a) |
| `string2jstring` | 1 | N/A | Calls `NewStringUTF`; returns local ref directly to caller — caller owns it |
| `throw_java_exception` | 1 | ✅ | `DeleteLocalRef(clazz)` after `ThrowNew` |
| `throw_illegal_state` / `throw_illegal_argument` / `throw_runtime` | 3 | N/A | Thin wrappers over `throw_java_exception`; no additional local refs |
| `enum_ordinal` | 1 | ✅ | `DeleteLocalRef(cls)` |

## Summary

| Scenario | What to do |
|---|---|
| Calling `extract_*` helpers | Nothing — helpers own their refs |
| Returning `make_*` result from JNI function | Nothing — JVM takes ownership |
| Storing `make_*` result temporarily | Call `DeleteLocalRef` when done |
| Loop creating many local refs in hand-written body | Use `PushLocalFrame`/`PopLocalFrame` |
| Caching a class/object across calls | Use `NewGlobalRef`; release in `JNI_OnUnload` |
