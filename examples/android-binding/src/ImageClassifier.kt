package com.example.android.classifier

/**
 * Native image-classification engine bound via JNI.
 *
 * Run the generator over this file to (re)produce the C++ stub:
 *
 *   python3 scripts/jni-binding-generator.py \
 *       --kotlin-source examples/android-binding/src/ImageClassifier.kt \
 *       --output examples/android-binding/generated
 *
 * The generated file (ImageClassifier_jni.gen.cpp) contains the JNI entry
 * points and conversion helpers.  Fill in the TODO bodies with calls to your
 * native classifier library.
 */
class ImageClassifier {

    /** Loads the model from an asset path and returns an opaque handle. */
    external fun nativeCreate(modelPath: String, threads: Int, useGpu: Boolean): Long

    /** Classifies a single image from raw ARGB pixel bytes and returns label scores. */
    external fun nativeClassify(handle: Long, rgbaPixels: ByteArray, width: Int, height: Int): FloatArray

    /** Returns the human-readable labels for all output classes. */
    external fun nativeGetLabels(handle: Long): List<String>

    /** Returns inference metadata (e.g. "model_version", "backend"). */
    external fun nativeGetMetadata(handle: Long): Map<String, String>

    /** Sets runtime options such as confidence threshold and top-k. */
    external fun nativeSetOptions(handle: Long, options: Map<String, Float>)

    /** Returns the top-k label names and their scores as a flat index map. */
    external fun nativeTopK(handle: Long, k: Int): Map<String, Float>

    /** Frees all native resources associated with the handle. */
    external fun nativeDestroy(handle: Long)
}
