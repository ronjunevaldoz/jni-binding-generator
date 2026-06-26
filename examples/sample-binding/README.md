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

[`generated/SampleEngine_jni_test.gen.cpp`](generated/SampleEngine_jni_test.gen.cpp) —
compile-time type-check file produced by `--generate-tests`. Every `extract_*`
and `make_*` helper call is inside an `if (false)` block so the compiler
verifies types without executing them.

## Regenerate

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated

# Also regenerate the type-check file:
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated \
    --generate-tests
```

## Verify it compiles

The generated file `#include`s [`scripts/jni-utils.h`](../../scripts/jni-utils.h).
To syntax-check against the real JNI headers:

```bash
# macOS (Homebrew/temurin JDK):
JH=$(/usr/libexec/java_home)
clang++ -std=c++17 -fsyntax-only \
    -I"$JH/include" -I"$JH/include/darwin" \
    -I scripts \
    examples/sample-binding/generated/SampleEngine_jni.gen.cpp

# Linux: the platform header lives in include/linux, and JAVA_HOME is
# usually already set (or use `dirname $(dirname $(readlink -f $(which javac)))`):
g++ -std=c++17 -fsyntax-only \
    -I"$JAVA_HOME/include" -I"$JAVA_HOME/include/linux" \
    -I scripts \
    examples/sample-binding/generated/SampleEngine_jni.gen.cpp
```

> The automated [`test_integration.py`](../../scripts/tests/test_integration.py)
> does this cross-platform: it resolves the JDK include dirs for darwin/linux/win32
> and skips when no compiler/JDK is present.
