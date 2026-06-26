package com.example.kmmbinding

/**
 * Raw JNI declarations for the JVM Desktop target.
 * Processed by jni-binding-generator.py the same way as the Android variant.
 *
 * Regenerate with:
 *   python3 scripts/jni-binding-generator.py \
 *     --kotlin-source shared/src/desktopMain/kotlin \
 *     --output desktopApp/src/jvmMain/cpp/generated
 */
internal class NativeBridgeJni {
    external fun nativeCreate(modelPath: String, threads: Int, useGpu: Boolean): Long
    external fun nativeDestroy(handle: Long)
    external fun nativeGenerate(handle: Long, prompt: String, maxTokens: Int): String
    external fun nativeTokenize(handle: Long, text: String): IntArray
    external fun nativeDetokenize(handle: Long, tokens: IntArray): String
    external fun nativeEmbed(handle: Long, text: String): List<Float>
    external fun nativeGetMetadata(handle: Long): Map<String, String>
    external fun nativeGetSamplerParams(handle: Long): Map<String, Float>
    external fun nativeSetSamplerParams(handle: Long, temperature: Float, topP: Float, topK: Int)
    external fun nativeGetVocabSize(handle: Long): Int
    external fun nativeGetContextSize(handle: Long): Int
}
