# KMP Binding — Kotlin Multiplatform example

A Kotlin Multiplatform project showing how the JNI binding generator fits into
a KMP module that targets Android, Desktop (JVM), and iOS.

## Structure

```
shared/src/
  commonMain/   NativeBridge.kt          — expect class (platform-agnostic API)
  androidMain/  NativeBridgeJni.kt       — external fun declarations (generator input)
                NativeBridge.android.kt  — actual class delegating to JNI
  desktopMain/  NativeBridgeJni.kt       — external fun declarations (generator input)
                NativeBridge.desktop.kt  — actual class delegating to JNI
  iosMain/      NativeBridge.ios.kt      — actual class using Kotlin/Native cinterop

androidApp/src/main/cpp/generated/       — generated JNI stubs (Android)
desktopApp/src/jvmMain/cpp/generated/    — generated JNI stubs (Desktop JVM)
```

## Input

`shared/src/androidMain/kotlin/…/NativeBridgeJni.kt` — eleven `external fun`
declarations wrapping a language model inference library.

`shared/src/desktopMain/kotlin/…/NativeBridgeJni.kt` — same declarations for
the Desktop JVM target (identical API, separate `System.loadLibrary` call).

## Output

`androidApp/src/main/cpp/generated/NativeBridgeJni_jni.gen.cpp`
`desktopApp/src/jvmMain/cpp/generated/NativeBridgeJni_jni.gen.cpp`

Both files share the same structure: `Java_*` entry points with marshalling
helpers from `jni-utils.h` and TODO bodies for the native implementation.

## Regenerate

```bash
# Android target
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/kmp-binding/shared/src/androidMain/kotlin \
    --output examples/kmp-binding/androidApp/src/main/cpp/generated

# Desktop JVM target
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/kmp-binding/shared/src/desktopMain/kotlin \
    --output examples/kmp-binding/desktopApp/src/jvmMain/cpp/generated
```

## Verify no drift

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/kmp-binding/shared/src/androidMain/kotlin \
    --output examples/kmp-binding/androidApp/src/main/cpp/generated \
    --check

python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/kmp-binding/shared/src/desktopMain/kotlin \
    --output examples/kmp-binding/desktopApp/src/jvmMain/cpp/generated \
    --check
```

## iOS target

The `iosMain` actual does **not** use JNI — it calls into a native C library via
Kotlin/Native cinterop. Use the `--ios-cinterop` flag to generate the `.def` file
and C header skeleton:

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/kmp-binding/shared/src/androidMain/kotlin \
    --output /tmp/kmp-generated \
    --ios-cinterop /tmp/kmp-cinterop
```
