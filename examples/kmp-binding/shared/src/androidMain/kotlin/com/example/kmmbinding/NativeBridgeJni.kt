package com.example.kmmbinding

/**
 * Raw JNI declarations for the Android target.
 * This file is the direct input to jni-binding-generator.py — every
 * external fun here gets a C++ JNI stub in androidApp/src/main/cpp/generated/.
 *
 * Regenerate with:
 *   python3 scripts/jni-binding-generator.py \
 *     --kotlin-source shared/src/androidMain/kotlin \
 *     --output androidApp/src/main/cpp/generated
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
