plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.myapp"
    compileSdk = 34

    defaultConfig {
        minSdk = 24
        externalNativeBuild {
            cmake {
                cppFlags += "-std=c++17"
                arguments += listOf(
                    "-DANDROID_STL=c++_shared",
                )
            }
        }
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
        }
    }
}

// Regenerate JNI bindings before every build.
// Requires Python 3.9+ and the generator script at the repo root.
val generatorScript = rootProject.file("../../scripts/jni-binding-generator.py")
val kotlinSrcDir = file("src/main/kotlin")
val generatedCppDir = file("src/main/cpp/generated")

tasks.register<Exec>("generateJniBindings") {
    group = "build"
    description = "Regenerate JNI C++ bindings from Kotlin external fun declarations"
    commandLine(
        "python3", generatorScript.absolutePath,
        "--kotlin-source", kotlinSrcDir.absolutePath,
        "--output", generatedCppDir.absolutePath,
    )
}

tasks.named("preBuild") {
    dependsOn("generateJniBindings")
}
