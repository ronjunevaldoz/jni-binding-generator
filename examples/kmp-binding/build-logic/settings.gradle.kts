// Settings for the included build-logic build.
//
// In the consuming project's root settings.gradle.kts, include this build:
//
//     pluginManagement {
//         includeBuild("build-logic")
//     }

dependencyResolutionManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

rootProject.name = "build-logic"
include(":convention")
