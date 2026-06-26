package com.example.myapp

/**
 * JNI bridge for the native inference engine.
 * Run the generator to regenerate NativeBridge_jni.gen.cpp:
 *
 *   python3 scripts/jni-binding-generator.py \
 *     --kotlin-source examples/android-binding/src/main/kotlin \
 *     --output examples/android-binding/src/main/cpp/generated
 */
class NativeBridge {
    // Lifecycle
    external fun nativeCreate(modelPath: String, threads: Int, useGpu: Boolean): Long
    external fun nativeDestroy(handle: Long)

    // Inference
    external fun nativeGenerate(handle: Long, prompt: String, maxTokens: Int): String
    external fun nativeGenerateTokens(handle: Long, prompt: String, maxTokens: Int): IntArray

    // Config / metadata
    external fun nativeGetModelName(handle: Long): String
    external fun nativeGetMetadata(handle: Long): Map<String, String>
    external fun nativeGetVocabSize(handle: Long): Int
    external fun nativeGetContextSize(handle: Long): Int

    // Embeddings
    external fun nativeEmbed(handle: Long, text: String): List<Float>
    external fun nativeBatchEmbed(handle: Long, texts: Array<String>): List<List<Float>>

    // Sampling
    external fun nativeSetSamplerParams(
        handle: Long,
        temperature: Float,
        topP: Float,
        topK: Int,
    )

    external fun nativeGetSamplerParams(handle: Long): Map<String, Float>

    // Token utilities
    external fun nativeTokenize(handle: Long, text: String): IntArray
    external fun nativeDetokenize(handle: Long, tokens: IntArray): String

    companion object {
        init {
            System.loadLibrary("myapp")
        }
    }
}
