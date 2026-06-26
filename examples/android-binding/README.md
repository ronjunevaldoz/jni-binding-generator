# Android Binding — Gradle + CMake integration example

A minimal Android-only project showing how to wire the JNI binding generator
into an Android app's build system.

## Input

[`src/ImageClassifier.kt`](src/ImageClassifier.kt) — seven `external fun`
declarations covering the types common in Android native libraries:

| Function | Demonstrates |
|---|---|
| `nativeCreate(String, Int, Boolean): Long` | string + primitives, returns handle |
| `nativeClassify(Long, ByteArray, Int, Int): FloatArray` | raw pixel bytes in, scores out |
| `nativeGetLabels(Long): List<String>` | list-of-strings return |
| `nativeGetMetadata(Long): Map<String, String>` | string map return |
| `nativeSetOptions(Long, Map<String, Float>)` | float-value map param, void return |
| `nativeTopK(Long, Int): Map<String, Float>` | mixed-value map return |
| `nativeDestroy(Long)` | resource release, void return |

## Output

[`generated/ImageClassifier_jni.gen.cpp`](generated/ImageClassifier_jni.gen.cpp) —
JNI entry points with correct `Java_*` mangled names, argument marshalling,
null/empty checks, and TODO bodies for the native implementation.

## Gradle integration

[`build.gradle.kts`](build.gradle.kts) shows a `generateJniBindings` `Exec` task
wired to run before `externalNativeBuildDebug` / `externalNativeBuildRelease`.
The generator only writes the output file when its content changes, so no-op runs
do not invalidate the CMake build.

[`CMakeLists.txt`](CMakeLists.txt) shows where to add the generated `.cpp` to your
`add_library` target and how to point the include path at `jni-utils.h`.

## Regenerate

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/android-binding/src/ImageClassifier.kt \
    --output examples/android-binding/generated
```

## Verify no drift

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/android-binding/src/ImageClassifier.kt \
    --output examples/android-binding/generated \
    --check
```
