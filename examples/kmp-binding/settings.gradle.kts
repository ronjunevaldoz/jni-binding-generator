rootProject.name = "kmp-binding"

pluginManagement {
    // Include the local build-logic so `id("jni-generator")` resolves without
    // publishing to a plugin portal.  The build-logic directory is a copy of
    // gradle-integration/build-logic from the jni-binding-generator repo root.
    includeBuild("build-logic")
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}

include(":shared", ":androidApp", ":desktopApp")
