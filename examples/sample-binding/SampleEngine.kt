package com.example.sample

/**
 * Sample Kotlin/JVM wrapper around a native C++ inference engine.
 *
 * Only the `external fun` declarations matter to the generator. Everything
 * else (the class itself, doc comments, helper methods) is ignored.
 *
 * Run the generator over this file to produce SampleEngine_jni.gen.cpp:
 *
 *   python3 scripts/jni-binding-generator.py \
 *       --kotlin-source examples/sample-binding/SampleEngine.kt \
 *       --output examples/sample-binding/generated
 */
class SampleEngine {

    /** Loads a model from disk and returns an opaque native handle. */
    external fun nativeLoad(
        modelPath: String,
        threads: Int,
    ): Long

    /** Runs inference for a single prompt and returns raw output bytes. */
    external fun nativeProcess(
        handle: Long,
        input: String,
        timeout: Int,
        temperature: Float,
    ): ByteArray?

    /** Tokenizes a batch of strings against the loaded model. */
    external fun nativeTokenizeBatch(
        handle: Long,
        prompts: Array<String>,
        addBos: Boolean,
    ): IntArray

    /** Frees the native handle. */
    external fun nativeRelease(handle: Long)

    /** Returns the tag list associated with the loaded model. */
    external fun nativeGetTags(handle: Long): List<String>

    /** Searches with string options and returns ranked result IDs. */
    external fun nativeSearch(
        handle: Long,
        query: String,
        options: Map<String, String>,
    ): List<String>
}
