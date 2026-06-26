import org.jetbrains.kotlin.gradle.ExperimentalKotlinGradlePluginApi
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.library)
    id("jni-generator")  // from build-logic — typed DSL for JNI binding generation
}

kotlin {
    androidTarget {
        @OptIn(ExperimentalKotlinGradlePluginApi::class)
        compilerOptions { jvmTarget.set(JvmTarget.JVM_11) }
    }

    iosX64()
    iosArm64()
    iosSimulatorArm64()

    jvm("desktop") {
        @OptIn(ExperimentalKotlinGradlePluginApi::class)
        compilerOptions { jvmTarget.set(JvmTarget.JVM_11) }
    }

    sourceSets {
        commonMain.dependencies {}
        androidMain.dependencies {}
        iosMain.dependencies {}
        val desktopMain by getting { dependencies {} }
    }
}

android {
    namespace = "com.example.kmmbinding"
    compileSdk = 34
    defaultConfig { minSdk = 24 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

// ---------------------------------------------------------------------------
// JNI binding generation — using the typed convention plugin (id("jni-generator"))
//
// The plugin registers:
//   * generateJniBindingsAndroid   — androidMain → androidApp/…/generated
//   * generateJniBindingsDesktop   — desktopMain → desktopApp/…/generated
//   * generateJniBindings          — aggregate (runs both)
//
// Gradle tracks inputs (Kotlin source + generator script) and outputs (generated
// dir) so tasks are skipped when nothing changed.
// ---------------------------------------------------------------------------

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

// Wire generation to run before the Android preBuild lifecycle task so the
// C++ stubs are always present before CMake is invoked.
tasks.named("preBuild") {
    dependsOn("generateJniBindings")
}
