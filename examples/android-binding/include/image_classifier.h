// image_classifier.h — C API for the native image-classification engine.
//
// This header is the input to `--kotlin-from-header`.  Run:
//
//   python3 scripts/jni-binding-generator.py \
//       --kotlin-from-header examples/android-binding/include/image_classifier.h \
//       --output examples/android-binding/src \
//       --kotlin-package com.example.android.classifier
//
// to regenerate src/ImageClassifier.kt with Kotlin external fun stubs.
// Then regenerate the C++ JNI bindings from that stub with the forward pass:
//
//   python3 scripts/jni-binding-generator.py \
//       --kotlin-source examples/android-binding/src/ImageClassifier.kt \
//       --output examples/android-binding/generated
//
#pragma once
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Loads a TFLite / ONNX model from disk.  Returns an opaque handle, or 0 on failure. */
void* image_classifier_create(const char* model_path, int32_t threads, bool use_gpu);

/** Releases all resources associated with the classifier. */
void image_classifier_destroy(void* handle);

/**
 * Runs inference on a single ARGB frame.
 * @param handle   Handle from image_classifier_create.
 * @param pixels   Raw ARGB bytes, width × height × 4.
 * @param width    Frame width in pixels.
 * @param height   Frame height in pixels.
 * @param scores   Caller-allocated output buffer of at least num_classes floats.
 * @param num_classes  Length of the scores buffer.
 * @return Number of classes written, or -1 on error.
 */
int32_t image_classifier_classify(
    void*           handle,
    const uint8_t*  pixels,
    int32_t         width,
    int32_t         height,
    float*          scores,
    int32_t         num_classes
);

/** Returns the number of output classes. */
int32_t image_classifier_num_classes(void* handle);

/**
 * Copies the label string for class_index into buf (null-terminated, at most
 * buf_len bytes including the terminator).  Returns the number of bytes written.
 */
int32_t image_classifier_get_label(void* handle, int32_t class_index, char* buf, int32_t buf_len);

/** Returns the model version string (static lifetime — caller must not free). */
const char* image_classifier_version(void* handle);

/** Sets a float runtime option by name (e.g. "confidence_threshold", "top_k"). */
void image_classifier_set_option(void* handle, const char* key, float value);

/** Gets a float runtime option by name.  Returns 0.0 if key is not found. */
float image_classifier_get_option(void* handle, const char* key);

#ifdef __cplusplus
}
#endif
