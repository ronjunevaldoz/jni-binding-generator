// Precompiled script plugin: JNI binding generation.
//
// Apply in a module with:
//
//     plugins { id("jni-generator") }
//
// Then configure one or more bindings:
//
//     jniGenerator {
//         generatorScript = file("$rootDir/scripts/jni-binding-generator.py")
//         bindings {
//             register("llama") {
//                 kotlinSource = layout.projectDirectory.dir("core/llama/src/jvmMain")
//                 outputDir    = layout.projectDirectory.dir("native/jni/generated/llama")
//             }
//         }
//     }
//
// This registers:
//   * generateJniBindings<Name>  — one Exec task per binding
//   * generateJniBindings        — aggregate task running all of them
//
// The aggregate task is wired to depend on each per-binding task, and each
// per-binding task declares its Kotlin source as an input and the output dir
// as an output so Gradle can skip regeneration when nothing changed.

import org.gradle.api.Named
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.provider.Property
import org.gradle.api.tasks.Exec

/** One Kotlin-source → C++-output mapping. */
abstract class JniBindingSpec(private val specName: String) : Named {
    override fun getName(): String = specName

    /**
     * Source **directory** containing `external fun` declarations (scanned
     * recursively). The generator's CLI also accepts a single `.kt` file; if
     * you need that, use the raw `Exec` task in the README instead, which can
     * point `--kotlin-source` at a file.
     */
    abstract val kotlinSource: DirectoryProperty

    /** Directory where generated `*_jni.gen.cpp` files are written. */
    abstract val outputDir: DirectoryProperty
}

abstract class JniGeneratorExtension {
    /** Python interpreter to run the generator with. Defaults to "python3". */
    abstract val python: Property<String>

    /** Path to `jni-binding-generator.py`. */
    abstract val generatorScript: org.gradle.api.file.RegularFileProperty

    /** Container of named bindings. */
    abstract val bindings: org.gradle.api.NamedDomainObjectContainer<JniBindingSpec>
}

val ext = extensions.create<JniGeneratorExtension>("jniGenerator")
ext.python.convention("python3")

val aggregate = tasks.register("generateJniBindings") {
    group = "jni"
    description = "Generate C++ JNI bindings for all configured Kotlin sources"
}

ext.bindings.all {
    val binding = this
    val capName = binding.name.replaceFirstChar { it.uppercase() }
    val task = tasks.register<Exec>("generateJniBindings$capName") {
        group = "jni"
        description = "Generate C++ JNI bindings for '${binding.name}'"

        // Track the generator script too, so edits to it re-run the task.
        inputs.file(ext.generatorScript).withPropertyName("generatorScript")
        inputs.dir(binding.kotlinSource).withPropertyName("kotlinSource")
        outputs.dir(binding.outputDir).withPropertyName("outputDir")

        executable = ext.python.get()
        args(
            ext.generatorScript.get().asFile.absolutePath,
            "--kotlin-source", binding.kotlinSource.get().asFile.absolutePath,
            "--output", binding.outputDir.get().asFile.absolutePath,
        )
    }
    aggregate.configure { dependsOn(task) }
}
