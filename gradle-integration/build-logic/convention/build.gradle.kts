// Build file for the convention module that hosts precompiled script plugins.
//
// The `kotlin-dsl` plugin compiles every `*.gradle.kts` under
// src/main/kotlin into an applyable plugin whose id is the file name
// (so `jni-generator.gradle.kts` becomes `id("jni-generator")`).

plugins {
    `kotlin-dsl`
}

group = "com.example.buildlogic"
