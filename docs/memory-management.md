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

## Summary

| Scenario | What to do |
|---|---|
| Calling `extract_*` helpers | Nothing — helpers own their refs |
| Returning `make_*` result from JNI function | Nothing — JVM takes ownership |
| Storing `make_*` result temporarily | Call `DeleteLocalRef` when done |
| Loop creating many local refs in hand-written body | Use `PushLocalFrame`/`PopLocalFrame` |
| Caching a class/object across calls | Use `NewGlobalRef`; release in `JNI_OnUnload` |
