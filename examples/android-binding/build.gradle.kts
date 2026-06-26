// Example: Android-only project using jni-binding-generator
//
// This shows how to wire the generator as a Gradle task so that the C++ stub
// is always regenerated from the Kotlin external-fun declarations before the
// native build runs.

plugins {
    id("com.android.application")
    kotlin("android")
}

android {
    namespace = "com.example.android.classifier"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.android.classifier"
        minSdk = 24
        targetSdk = 34

        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }

        externalNativeBuild {
            cmake {
                cppFlags("-std=c++17")
                arguments("-DANDROID_STL=c++_shared")
            }
        }
    }

    externalNativeBuild {
        cmake {
            path = file("CMakeLists.txt")
        }
    }
}

// --------------------------------------------------------------------------
// JNI binding generator — two-phase pipeline
//
// Phase 1: C header → Kotlin stubs  (`--kotlin-from-header`)
//   Reads include/image_classifier.h and writes src/ImageClassifier.kt.
//   Re-run whenever the C API changes.
//
// Phase 2: Kotlin stubs → C++ JNI bindings  (forward pass)
//   Reads src/ImageClassifier.kt and writes generated/ImageClassifier_jni.gen.cpp.
//   Runs automatically before the CMake build.
//
// Run both from the command line:
//   ./gradlew generateKotlinFromHeader generateJniBindings
// --------------------------------------------------------------------------
val generatorScript = rootProject.file("../../scripts/jni-binding-generator.py")
val cHeader         = file("include/image_classifier.h")
val kotlinSource    = file("src/ImageClassifier.kt")
val generatedDir    = file("generated")

// Phase 1 — reverse: C header → Kotlin object with external fun declarations
tasks.register<Exec>("generateKotlinFromHeader") {
    group = "jni"
    description = "Scaffold Kotlin external fun stubs from include/image_classifier.h"

    inputs.file(cHeader)
    inputs.file(generatorScript)
    outputs.file(kotlinSource)

    commandLine(
        "python3", generatorScript.absolutePath,
        "--kotlin-from-header", cHeader.absolutePath,
        "--output", file("src").absolutePath,
        "--kotlin-package", "com.example.android.classifier",
    )
}

// Phase 2 — forward: Kotlin stubs → C++ JNI bindings
tasks.register<Exec>("generateJniBindings") {
    group = "jni"
    description = "Regenerate C++ JNI stubs from Kotlin external fun declarations"

    // generateKotlinFromHeader must run first if the header changed.
    // When running only `generateJniBindings` directly (e.g. after editing
    // the .kt by hand), this dependency is skipped.
    inputs.file(kotlinSource)
    inputs.file(generatorScript)
    outputs.dir(generatedDir)

    commandLine(
        "python3", generatorScript.absolutePath,
        "--kotlin-source", kotlinSource.absolutePath,
        "--output", generatedDir.absolutePath,
    )
}

// Full pipeline: header → Kotlin → C++
tasks.register("generateAll") {
    group = "jni"
    description = "Full pipeline: C header → Kotlin stubs → C++ JNI bindings"
    dependsOn("generateKotlinFromHeader", "generateJniBindings")
    tasks.named("generateJniBindings").configure { mustRunAfter("generateKotlinFromHeader") }
}

// Ensure JNI stubs are up to date before the native CMake build.
tasks.matching {
    it.name.startsWith("buildCMake") ||
    it.name == "externalNativeBuildDebug" ||
    it.name == "externalNativeBuildRelease"
}.configureEach {
    dependsOn("generateJniBindings")
}
