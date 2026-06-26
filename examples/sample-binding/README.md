# Sample Binding — Before & After

A worked example of the generator turning Kotlin `external fun` declarations
into C++ JNI entry points.

## Input

[`SampleEngine.kt`](SampleEngine.kt) — a Kotlin/JVM wrapper with four
`external fun` declarations covering the common cases:

| Function | Demonstrates |
|---|---|
| `nativeLoad(String, Int): Long` | string + primitive marshalling, string error check |
| `nativeProcess(Long, String, Int, Float): ByteArray?` | handle null-check, nullable return |
| `nativeTokenizeBatch(Long, Array<String>, Boolean): IntArray` | string-array + boolean marshalling |
| `nativeRelease(Long)` | void return, handle-only |

## Output

[`generated/SampleEngine_jni.gen.cpp`](generated/SampleEngine_jni.gen.cpp) —
fully-formed JNI entry points with correct `Java_*` mangled names, argument
marshalling, null/empty error checks, and a TODO body for the hand-written
native call.

## Regenerate

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated
```

## Verify it compiles

The generated file `#include`s [`scripts/jni-utils.h`](../../scripts/jni-utils.h).
To syntax-check against the real JNI headers:

```bash
JH=$(/usr/libexec/java_home)
clang++ -std=c++17 -fsyntax-only \
    -I"$JH/include" -I"$JH/include/darwin" \
    -I scripts \
    examples/sample-binding/generated/SampleEngine_jni.gen.cpp
```
