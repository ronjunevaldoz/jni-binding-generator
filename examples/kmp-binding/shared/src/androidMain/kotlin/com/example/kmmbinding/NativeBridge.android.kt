package com.example.kmmbinding

actual class NativeBridge actual constructor() {
    private val jni = NativeBridgeJni()

    actual fun create(modelPath: String, threads: Int, useGpu: Boolean): Long =
        jni.nativeCreate(modelPath, threads, useGpu)

    actual fun destroy(handle: Long) = jni.nativeDestroy(handle)

    actual fun generate(handle: Long, prompt: String, maxTokens: Int): String =
        jni.nativeGenerate(handle, prompt, maxTokens)

    actual fun tokenize(handle: Long, text: String): IntArray =
        jni.nativeTokenize(handle, text)

    actual fun detokenize(handle: Long, tokens: IntArray): String =
        jni.nativeDetokenize(handle, tokens)

    actual fun embed(handle: Long, text: String): List<Float> =
        jni.nativeEmbed(handle, text)

    actual fun getMetadata(handle: Long): Map<String, String> =
        jni.nativeGetMetadata(handle)

    actual fun getSamplerParams(handle: Long): Map<String, Float> =
        jni.nativeGetSamplerParams(handle)

    actual fun setSamplerParams(handle: Long, temperature: Float, topP: Float, topK: Int) =
        jni.nativeSetSamplerParams(handle, temperature, topP, topK)

    actual fun getVocabSize(handle: Long): Int = jni.nativeGetVocabSize(handle)

    actual fun getContextSize(handle: Long): Int = jni.nativeGetContextSize(handle)

    companion object {
        init { System.loadLibrary("kmmbinding") }
    }
}
