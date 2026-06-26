// jni-utils.h — helper utilities used by generated JNI bindings.
//
// Copy this header next to the generated *_jni.gen.cpp files (or onto an
// include path the native build sees). The generator emits calls to these
// helpers; keeping them here means the generated code stays small and the
// conversions stay reviewable in one place.
//
// All functions are header-only / inline so the header can be dropped into a
// project without a separate translation unit.

#ifndef JNI_BINDING_GENERATOR_JNI_UTILS_H
#define JNI_BINDING_GENERATOR_JNI_UTILS_H

#include <jni.h>

#include <cstdint>
#include <string>
#include <vector>

// --------------------------------------------------------------------------- //
// Exception throwing
// --------------------------------------------------------------------------- //

inline void throw_java_exception(JNIEnv* env, const char* cls, const char* msg) {
    jclass clazz = env->FindClass(cls);
    if (clazz != nullptr) {
        env->ThrowNew(clazz, msg);
        env->DeleteLocalRef(clazz);
    }
}

inline void throw_illegal_state(JNIEnv* env, const char* msg) {
    throw_java_exception(env, "java/lang/IllegalStateException", msg);
}

inline void throw_illegal_argument(JNIEnv* env, const char* msg) {
    throw_java_exception(env, "java/lang/IllegalArgumentException", msg);
}

inline void throw_runtime(JNIEnv* env, const char* msg) {
    throw_java_exception(env, "java/lang/RuntimeException", msg);
}

// --------------------------------------------------------------------------- //
// String marshalling
// --------------------------------------------------------------------------- //

inline std::string jstring2string(JNIEnv* env, jstring jstr) {
    if (jstr == nullptr) {
        return {};
    }
    const char* chars = env->GetStringUTFChars(jstr, nullptr);
    if (chars == nullptr) {
        return {};  // OutOfMemoryError already pending
    }
    std::string result(chars);
    env->ReleaseStringUTFChars(jstr, chars);
    return result;
}

inline jstring string2jstring(JNIEnv* env, const std::string& str) {
    return env->NewStringUTF(str.c_str());
}

// --------------------------------------------------------------------------- //
// Primitive-array marshalling (Java -> C++)
// --------------------------------------------------------------------------- //

inline std::vector<uint8_t> extract_byte_array(JNIEnv* env, jbyteArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<uint8_t> out(static_cast<size_t>(len));
    if (len > 0) {
        env->GetByteArrayRegion(arr, 0, len, reinterpret_cast<jbyte*>(out.data()));
    }
    return out;
}

inline std::vector<float> extract_float_array(JNIEnv* env, jfloatArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<float> out(static_cast<size_t>(len));
    if (len > 0) {
        env->GetFloatArrayRegion(arr, 0, len, out.data());
    }
    return out;
}

inline std::vector<int32_t> extract_int_array(JNIEnv* env, jintArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<int32_t> out(static_cast<size_t>(len));
    if (len > 0) {
        env->GetIntArrayRegion(arr, 0, len, reinterpret_cast<jint*>(out.data()));
    }
    return out;
}

inline std::vector<int64_t> extract_long_array(JNIEnv* env, jlongArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<int64_t> out(static_cast<size_t>(len));
    if (len > 0) {
        env->GetLongArrayRegion(arr, 0, len, reinterpret_cast<jlong*>(out.data()));
    }
    return out;
}

// --------------------------------------------------------------------------- //
// String-array marshalling (Java String[] -> C++)
// --------------------------------------------------------------------------- //

inline std::vector<std::string> extract_string_array(JNIEnv* env, jobjectArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<std::string> out;
    out.reserve(static_cast<size_t>(len));
    for (jsize i = 0; i < len; ++i) {
        jstring element = static_cast<jstring>(env->GetObjectArrayElement(arr, i));
        out.push_back(jstring2string(env, element));
        env->DeleteLocalRef(element);
    }
    return out;
}

#endif  // JNI_BINDING_GENERATOR_JNI_UTILS_H
