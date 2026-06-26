import org.jetbrains.kotlin.gradle.ExperimentalKotlinGradlePluginApi
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.library)
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
// JNI binding generation
// Run the generator against each JVM-targeted source set that has external fun
// declarations.  The generator reads Kotlin source; CMake picks up the output.
// ---------------------------------------------------------------------------

val generatorScript = rootProject.file("../../scripts/jni-binding-generator.py")

tasks.register<Exec>("generateJniAndroid") {
    group = "build"
    description = "Regenerate JNI C++ bindings for the androidMain source set"
    commandLine(
        "python3", generatorScript.absolutePath,
        "--kotlin-source",
        layout.projectDirectory.dir("src/androidMain/kotlin").asFile.absolutePath,
        "--output",
        rootProject.file("androidApp/src/main/cpp/generated").absolutePath,
    )
}

tasks.register<Exec>("generateJniDesktop") {
    group = "build"
    description = "Regenerate JNI C++ bindings for the desktop (jvmMain) source set"
    commandLine(
        "python3", generatorScript.absolutePath,
        "--kotlin-source",
        layout.projectDirectory.dir("src/desktopMain/kotlin").asFile.absolutePath,
        "--output",
        rootProject.file("desktopApp/src/jvmMain/cpp/generated").absolutePath,
    )
}

tasks.named("preBuild") {
    dependsOn("generateJniAndroid", "generateJniDesktop")
}
