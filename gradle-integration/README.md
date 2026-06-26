# Gradle Integration

Two ways to run the generator from Gradle. Start with **Option A** — it needs
zero plugin infrastructure and is the right choice for one or two bindings.
Move to **Option B** when you have several bindings and want a typed DSL.

> **Note:** These files were authored against the Gradle Kotlin DSL but were
> not executed in the environment they were written in (no Gradle binary /
> offline). Treat them as a starting template — run `./gradlew tasks` once
> after copying to confirm the task appears. The Python CLI they invoke is
> tested and verified.

---

## Option A — Raw task (recommended to start)

Paste directly into the `build.gradle.kts` of the module that owns your native
build (no plugin, no `build-logic`):

```kotlin
tasks.register<Exec>("generateJniBindings") {
    group = "jni"
    description = "Generate C++ JNI bindings from Kotlin external functions"

    val kotlinSource = layout.projectDirectory.dir("../core/llama/src/jvmMain")
    val outputDir = layout.projectDirectory.dir("native/jni/generated/llama")
    val script = layout.projectDirectory.file("../scripts/jni-binding-generator.py")

    inputs.file(script)          // re-run when the generator itself changes
    inputs.dir(kotlinSource)
    outputs.dir(outputDir)

    commandLine(
        "python3",
        script.asFile.absolutePath,
        "--kotlin-source", kotlinSource.asFile.absolutePath,
        "--output", outputDir.asFile.absolutePath,
    )
}
```

Run it:

```bash
./gradlew generateJniBindings
```

For multiple bindings, register one task per binding (e.g.
`generateJniBindingsLlama`, `generateJniBindingsWhisper`) and an aggregate:

```kotlin
tasks.register("generateJniBindings") {
    group = "jni"
    dependsOn("generateJniBindingsLlama", "generateJniBindingsWhisper")
}
```

---

## Option B — Convention plugin with a DSL

For projects that already use a `build-logic` included build, copy
[`build-logic/`](build-logic/) into your project (or merge the
[`jni-generator.gradle.kts`](build-logic/convention/src/main/kotlin/jni-generator.gradle.kts)
precompiled plugin into your existing convention module).

**1. Include the build** in the root `settings.gradle.kts`:

```kotlin
pluginManagement {
    includeBuild("build-logic")
}
```

**2. Apply and configure** in your native module's `build.gradle.kts`:

```kotlin
plugins {
    id("jni-generator")
}

jniGenerator {
    generatorScript = file("$rootDir/scripts/jni-binding-generator.py")
    bindings {
        register("llama") {
            kotlinSource = layout.projectDirectory.dir("../core/llama/src/jvmMain")
            outputDir    = layout.projectDirectory.dir("native/jni/generated/llama")
        }
        register("whisper") {
            kotlinSource = layout.projectDirectory.dir("../core/whisper/src/jvmMain")
            outputDir    = layout.projectDirectory.dir("native/jni/generated/whisper")
        }
    }
}
```

This registers `generateJniBindingsLlama`, `generateJniBindingsWhisper`, and an
aggregate `generateJniBindings`. Each per-binding task declares its Kotlin
source as an input and its output directory as an output, so Gradle skips
regeneration when nothing changed.

---

## Wire into the native build lifecycle (optional)

Make generation run automatically before the native build, without coupling the
two if generation is skipped:

```kotlin
tasks.matching { it.name == "buildNative" }.configureEach {
    dependsOn("generateJniBindings")
}
```

Generated `*.gen.cpp` files are not committed (see the project `.gitignore`);
they are produced on demand like protobuf output.

---

## CI drift check (optional, Phase 3 preview)

To catch hand-edits to generated files, regenerate in CI and fail if the result
differs from what is checked in (only relevant if you *do* commit generated
output):

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source core/llama/src/jvmMain \
    --output native/jni/generated/llama
git diff --exit-code native/jni/generated/llama
```
