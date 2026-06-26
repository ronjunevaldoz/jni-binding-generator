package com.example.kmmbinding

/**
 * Cross-platform interface to a native inference engine.
 *
 * - Android / JVM Desktop: actual implementations delegate to JNI via
 *   NativeBridgeJni (external fun declarations processed by jni-binding-generator.py).
 * - iOS: actual implementation uses Kotlin/Native cinterop (see NativeBridge.ios.kt).
 */
expect class NativeBridge() {
    /** Creates a native engine instance. Returns an opaque handle. */
    fun create(modelPath: String, threads: Int, useGpu: Boolean): Long

    /** Destroys the engine and releases all resources. */
    fun destroy(handle: Long)

    /** Runs text generation. */
    fun generate(handle: Long, prompt: String, maxTokens: Int): String

    /** Tokenises [text] and returns the token ids. */
    fun tokenize(handle: Long, text: String): IntArray

    /** Detokenises [tokens] back to text. */
    fun detokenize(handle: Long, tokens: IntArray): String

    /** Returns a float embedding vector for [text]. */
    fun embed(handle: Long, text: String): List<Float>

    /** Returns the model's string metadata. */
    fun getMetadata(handle: Long): Map<String, String>

    /** Returns the sampling parameter map (temperature, top_p, …). */
    fun getSamplerParams(handle: Long): Map<String, Float>

    /** Sets sampling parameters. */
    fun setSamplerParams(handle: Long, temperature: Float, topP: Float, topK: Int)

    /** Vocabulary size of the loaded model. */
    fun getVocabSize(handle: Long): Int

    /** Maximum context window of the loaded model. */
    fun getContextSize(handle: Long): Int
}
