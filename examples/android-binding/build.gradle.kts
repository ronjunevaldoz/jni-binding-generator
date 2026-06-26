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
// JNI binding generator task
//
// Runs jni-binding-generator.py to keep generated/ImageClassifier_jni.gen.cpp
// in sync with src/ImageClassifier.kt.  The generator only writes the file
// when its content changes, so this task does not invalidate the CMake build
// on no-op runs.
// --------------------------------------------------------------------------
val generatorScript = rootProject.file("../../scripts/jni-binding-generator.py")
val kotlinSource    = file("src/ImageClassifier.kt")
val generatedDir    = file("generated")

tasks.register<Exec>("generateJniBindings") {
    group = "build"
    description = "Regenerate C++ JNI stubs from Kotlin external fun declarations"

    inputs.file(kotlinSource)
    outputs.dir(generatedDir)

    commandLine(
        "python3", generatorScript.absolutePath,
        "--kotlin-source", kotlinSource.absolutePath,
        "--output", generatedDir.absolutePath,
    )
}

// Ensure the stubs are generated before the native build.
tasks.matching { it.name.startsWith("buildCMake") || it.name == "externalNativeBuildDebug" || it.name == "externalNativeBuildRelease" }.configureEach {
    dependsOn("generateJniBindings")
}
