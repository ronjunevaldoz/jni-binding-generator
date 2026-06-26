# Advanced usage

## Thread safety and `JNIEnv*`

`JNIEnv*` is per-thread. A pointer obtained on the main thread cannot be passed
to a background thread and used there — doing so crashes the JVM with a hard
abort, not a catchable exception.

If your native code spawns threads or uses an async callback:

```cpp
// In your native library callback (called from a C++ thread):
JavaVM* g_jvm = nullptr;  // saved in JNI_OnLoad

void my_native_callback(int result) {
    JNIEnv* env = nullptr;
    bool did_attach = false;
    if (g_jvm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) == JNI_EDETACHED) {
        g_jvm->AttachCurrentThread(reinterpret_cast<void**>(&env), nullptr);
        did_attach = true;
    }

    // ... use env ...

    if (did_attach) {
        g_jvm->DetachCurrentThread();
    }
}
```

## `JNI_OnLoad` — caching `JavaVM` and method IDs

`JNI_OnLoad` runs once when the `.so` is loaded via `System.loadLibrary`. Use it
to cache the `JavaVM*` and any frequently-used method IDs so you don't look them
up on every call.

```cpp
static JavaVM* g_jvm = nullptr;

jint JNI_OnLoad(JavaVM* vm, void*) {
    g_jvm = vm;
    JNIEnv* env = nullptr;
    vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    // cache method IDs here if needed
    return JNI_VERSION_1_6;
}

void JNI_OnUnload(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6);
    // delete any global refs created in JNI_OnLoad
}
```

Place this in a hand-written `<Library>-jni.cpp`, not in the generated file.

## Exception propagation from native to Kotlin

The generator stubs throw `IllegalStateException` / `IllegalArgumentException`
for null handles and empty required strings. For errors from your own native code,
use the helpers in `jni-utils.h`:

```cpp
// In your hand-written body:
int rc = my_library_call(handle_ptr, input_val.c_str());
if (rc != 0) {
    throw_runtime(env, "nativeProcess: library returned an error");
    return nullptr;
}
```

To rethrow a C++ exception as a Java exception:

```cpp
try {
    result = my_library_call(handle_ptr);
} catch (const std::exception& e) {
    throw_runtime(env, e.what());
    return nullptr;
}
```

Do not let C++ exceptions propagate past the JNI boundary — the JVM does not
understand them and the process will terminate.

## Android NDK

The generator and `jni-utils.h` work with the Android NDK unchanged. The only
difference is in the build setup — there is no `JAVA_HOME`; the NDK ships its
own `jni.h`.

**CMakeLists.txt:**

```cmake
cmake_minimum_required(VERSION 3.22)
project(my_jni)

add_library(my_jni SHARED
    # generated stub:
    generated/MyEngine_jni.gen.cpp
    # hand-written logic:
    my_engine-jni.cpp
)

target_include_directories(my_jni PRIVATE
    ${CMAKE_SOURCE_DIR}/include  # where jni-utils.h lives
    # NDK jni.h is on the include path automatically via the NDK toolchain
)
```

**Integration test with NDK:**

The `test_integration.py` compile test skips when `JAVA_HOME` is unset. To run
it against the NDK instead, set `JAVA_HOME` to point at the NDK sysroot:

```bash
NDK=$ANDROID_NDK_HOME  # e.g. ~/Library/Android/sdk/ndk/26.1.10909125
JAVA_HOME=$NDK/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr \
    python3 -m unittest discover -s scripts/tests -p test_integration.py
```

## Unsupported Kotlin constructs

The generator hard-errors on constructs it cannot safely translate:

| Construct | Error message | Workaround |
|---|---|---|
| `suspend external fun` | "suspend external fun is not supported" | Expose a plain `external fun`, call it from a coroutine dispatcher |
| Extension receiver (`fun String.foo()`) | "Extension external fun is not supported" | Move into a class or object |
| `vararg` params | "vararg parameters are not supported" | Pass `Array<T>` or `List<T>` instead |
| Function-type params (`(Int) -> String`) | "function-type parameters are not supported" | Pass a callback handle (`Long`) or use an interface |

Top-level `external fun` (outside any class) is supported — the generator emits
the `<Filename>Kt` class name that the Kotlin compiler produces.
