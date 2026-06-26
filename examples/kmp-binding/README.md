# KMP Binding — Kotlin Multiplatform example

A Kotlin Multiplatform project showing how the JNI binding generator fits into
a KMP module that targets Android, Desktop (JVM), and iOS.

## Structure

```
build-logic/                         ← copy of gradle-integration/build-logic
    convention/
        src/main/kotlin/
            jni-generator.gradle.kts ← id("jni-generator") convention plugin
shared/src/
  commonMain/   NativeBridge.kt          — expect class (cross-platform API)
  androidMain/  NativeBridgeJni.kt       — external fun declarations (generator input)
                NativeBridge.android.kt  — actual class delegating to JNI
  desktopMain/  NativeBridgeJni.kt       — external fun declarations (generator input)
                NativeBridge.desktop.kt  — actual class delegating to JNI
  iosMain/      NativeBridge.ios.kt      — actual class using Kotlin/Native cinterop
androidApp/
  src/main/
    kotlin/…/MainActivity.kt            — Compose entry point
    AndroidManifest.xml
    cpp/
      generated/NativeBridgeJni_jni.gen.cpp   ← generated JNI stubs (Android)
desktopApp/
  src/desktopMain/kotlin/…/Main.kt     — Compose Desktop entry point
  src/jvmMain/cpp/
    generated/NativeBridgeJni_jni.gen.cpp     ← generated JNI stubs (Desktop JVM)
iosApp/src/nativeInterop/cinterop/    ← cinterop .def + C header skeleton
```

## Convention plugin

`shared/build.gradle.kts` applies `id("jni-generator")` from the local
`build-logic` included build (a copy of `gradle-integration/build-logic` from
the repo root).  The plugin provides a typed DSL instead of hand-rolled `Exec`
tasks:

```kotlin
jniGenerator {
    generatorScript = rootProject.file("../../scripts/jni-binding-generator.py")

    bindings {
        register("android") {
            kotlinSource = layout.projectDirectory.dir("src/androidMain/kotlin")
            outputDir    = rootProject.layout.projectDirectory.dir("androidApp/src/main/cpp/generated")
        }
        register("desktop") {
            kotlinSource = layout.projectDirectory.dir("src/desktopMain/kotlin")
            outputDir    = rootProject.layout.projectDirectory.dir("desktopApp/src/jvmMain/cpp/generated")
        }
    }
}
```

This registers:
- `generateJniBindingsAndroid` — androidMain → androidApp/…/generated
- `generateJniBindingsDesktop` — desktopMain → desktopApp/…/generated
- `generateJniBindings` — aggregate (runs both)

Gradle tracks inputs (Kotlin source + generator script) and output dirs so
tasks are **skipped when nothing changed** — no unnecessary CMake cache invalidation.

## Regenerate

```bash
# Both targets at once (via the plugin aggregate task)
./gradlew :shared:generateJniBindings

# Android only
./gradlew :shared:generateJniBindingsAndroid

# Desktop only
./gradlew :shared:generateJniBindingsDesktop
```

Or call the Python CLI directly:

```bash
# Android
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/kmp-binding/shared/src/androidMain/kotlin \
    --output examples/kmp-binding/androidApp/src/main/cpp/generated

# Desktop JVM
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
Kotlin/Native cinterop.  Use `--ios-cinterop` to generate the `.def` and header:

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/kmp-binding/shared/src/androidMain/kotlin \
    --output examples/kmp-binding/androidApp/src/main/cpp/generated \
    --ios-cinterop examples/kmp-binding/iosApp/src/nativeInterop/cinterop
```

Then:
1. Edit the generated `include/NativeBridgeJni.h` to match your real C API.
2. Fill in `staticLibraries` / `libraryPaths` in `NativeBridgeJni.def`.
3. Wire the cinterop in `shared/build.gradle.kts` (see `iosApp/README.md`).
4. Replace stub bodies in `NativeBridge.ios.kt` with cinterop calls.
