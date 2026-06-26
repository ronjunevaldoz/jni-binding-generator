package com.example.kmmbinding

// iOS actual uses Kotlin/Native cinterop.
// 1. Add a cinterop definition in shared/build.gradle.kts:
//      iosMain { cinterops { val kmmbinding by creating { defFile("src/nativeInterop/cinterop/kmmbinding.def") } } }
// 2. Expose the C functions in a .def file pointing to your header.
// 3. Replace the stub bodies below with calls to the interop bindings.
//
// No JNI is involved on iOS — the generator does not process this file.

import kotlinx.cinterop.ExperimentalForeignApi

@OptIn(ExperimentalForeignApi::class)
actual class NativeBridge actual constructor() {
    actual fun create(modelPath: String, threads: Int, useGpu: Boolean): Long {
        // TODO: kmmbinding_create(modelPath, threads, useGpu)
        return 0L
    }

    actual fun destroy(handle: Long) {
        // TODO: kmmbinding_destroy(handle)
    }

    actual fun generate(handle: Long, prompt: String, maxTokens: Int): String {
        // TODO: kmmbinding_generate(handle, prompt, maxTokens)?.toKString() ?: ""
        return ""
    }

    actual fun tokenize(handle: Long, text: String): IntArray = IntArray(0)

    actual fun detokenize(handle: Long, tokens: IntArray): String = ""

    actual fun embed(handle: Long, text: String): List<Float> = emptyList()

    actual fun getMetadata(handle: Long): Map<String, String> = emptyMap()

    actual fun getSamplerParams(handle: Long): Map<String, Float> = emptyMap()

    actual fun setSamplerParams(handle: Long, temperature: Float, topP: Float, topK: Int) {}

    actual fun getVocabSize(handle: Long): Int = 0

    actual fun getContextSize(handle: Long): Int = 0
}
