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
#include <unordered_map>
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
    // EP-6a fix: release before any heap allocation that could throw std::bad_alloc,
    // so the pinned chars are freed on every path including exceptions.
    std::string result;
    try {
        result = chars;
    } catch (...) {
        env->ReleaseStringUTFChars(jstr, chars);
        throw;
    }
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
        // EP-6b fix: convert before push_back so DeleteLocalRef runs even if
        // push_back throws std::bad_alloc.
        std::string str = jstring2string(env, element);
        env->DeleteLocalRef(element);
        out.push_back(std::move(str));
    }
    return out;
}

// --------------------------------------------------------------------------- //
// List marshalling (java.util.List <-> C++)
// --------------------------------------------------------------------------- //

inline std::vector<std::string> extract_list_string(JNIEnv* env, jobject list) {
    std::vector<std::string> out;
    if (!list) return out;
    jclass cls       = env->FindClass("java/util/List");
    jmethodID sizeM  = env->GetMethodID(cls, "size", "()I");
    jmethodID getM   = env->GetMethodID(cls, "get",  "(I)Ljava/lang/Object;");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jstring elem = static_cast<jstring>(env->CallObjectMethod(list, getM, i));
        std::string str = jstring2string(env, elem);
        env->DeleteLocalRef(elem);
        out.push_back(std::move(str));
    }
    env->DeleteLocalRef(cls);
    return out;
}

inline std::vector<int32_t> extract_list_int(JNIEnv* env, jobject list) {
    std::vector<int32_t> out;
    if (!list) return out;
    jclass listCls  = env->FindClass("java/util/List");
    jclass intCls   = env->FindClass("java/lang/Integer");
    jmethodID sizeM = env->GetMethodID(listCls, "size", "()I");
    jmethodID getM  = env->GetMethodID(listCls, "get",  "(I)Ljava/lang/Object;");
    jmethodID valM  = env->GetMethodID(intCls,  "intValue", "()I");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jobject elem = env->CallObjectMethod(list, getM, i);
        out.push_back(static_cast<int32_t>(env->CallIntMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(listCls);
    return out;
}

inline std::vector<int64_t> extract_list_long(JNIEnv* env, jobject list) {
    std::vector<int64_t> out;
    if (!list) return out;
    jclass listCls  = env->FindClass("java/util/List");
    jclass longCls  = env->FindClass("java/lang/Long");
    jmethodID sizeM = env->GetMethodID(listCls, "size",      "()I");
    jmethodID getM  = env->GetMethodID(listCls, "get",       "(I)Ljava/lang/Object;");
    jmethodID valM  = env->GetMethodID(longCls, "longValue", "()J");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jobject elem = env->CallObjectMethod(list, getM, i);
        out.push_back(static_cast<int64_t>(env->CallLongMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(longCls);
    env->DeleteLocalRef(listCls);
    return out;
}

inline std::vector<float> extract_list_float(JNIEnv* env, jobject list) {
    std::vector<float> out;
    if (!list) return out;
    jclass listCls  = env->FindClass("java/util/List");
    jclass floatCls = env->FindClass("java/lang/Float");
    jmethodID sizeM = env->GetMethodID(listCls,  "size",       "()I");
    jmethodID getM  = env->GetMethodID(listCls,  "get",        "(I)Ljava/lang/Object;");
    jmethodID valM  = env->GetMethodID(floatCls, "floatValue", "()F");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jobject elem = env->CallObjectMethod(list, getM, i);
        out.push_back(static_cast<float>(env->CallFloatMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(floatCls);
    env->DeleteLocalRef(listCls);
    return out;
}

inline std::vector<double> extract_list_double(JNIEnv* env, jobject list) {
    std::vector<double> out;
    if (!list) return out;
    jclass listCls   = env->FindClass("java/util/List");
    jclass doubleCls = env->FindClass("java/lang/Double");
    jmethodID sizeM  = env->GetMethodID(listCls,   "size",        "()I");
    jmethodID getM   = env->GetMethodID(listCls,   "get",         "(I)Ljava/lang/Object;");
    jmethodID valM   = env->GetMethodID(doubleCls, "doubleValue", "()D");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jobject elem = env->CallObjectMethod(list, getM, i);
        out.push_back(static_cast<double>(env->CallDoubleMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(doubleCls);
    env->DeleteLocalRef(listCls);
    return out;
}

inline jobject make_list_string(JNIEnv* env, const std::vector<std::string>& vec) {
    jclass cls    = env->FindClass("java/util/ArrayList");
    jmethodID ctor = env->GetMethodID(cls, "<init>", "(I)V");
    jmethodID add  = env->GetMethodID(cls, "add",    "(Ljava/lang/Object;)Z");
    jobject list  = env->NewObject(cls, ctor, static_cast<jint>(vec.size()));
    for (const auto& s : vec) {
        jstring jstr = env->NewStringUTF(s.c_str());
        env->CallBooleanMethod(list, add, jstr);
        env->DeleteLocalRef(jstr);
    }
    env->DeleteLocalRef(cls);
    return list;
}

inline jobject make_list_int(JNIEnv* env, const std::vector<int32_t>& vec) {
    jclass listCls = env->FindClass("java/util/ArrayList");
    jclass intCls  = env->FindClass("java/lang/Integer");
    jmethodID ctor    = env->GetMethodID(listCls, "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(listCls, "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(intCls, "valueOf", "(I)Ljava/lang/Integer;");
    jobject list = env->NewObject(listCls, ctor, static_cast<jint>(vec.size()));
    for (int32_t v : vec) {
        jobject boxed = env->CallStaticObjectMethod(intCls, valueOf, static_cast<jint>(v));
        env->CallBooleanMethod(list, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(listCls);
    return list;
}

// --------------------------------------------------------------------------- //
// Map marshalling (java.util.Map <-> C++)
// --------------------------------------------------------------------------- //

inline std::unordered_map<std::string, std::string>
extract_map_string_string(JNIEnv* env, jobject map) {
    std::unordered_map<std::string, std::string> out;
    if (!map) return out;
    jclass mapCls   = env->FindClass("java/util/Map");
    jclass setCls   = env->FindClass("java/util/Set");
    jclass iterCls  = env->FindClass("java/util/Iterator");
    jclass entryCls = env->FindClass("java/util/Map$Entry");
    jmethodID entrySetM = env->GetMethodID(mapCls,   "entrySet", "()Ljava/util/Set;");
    jmethodID iteratorM = env->GetMethodID(setCls,   "iterator", "()Ljava/util/Iterator;");
    jmethodID hasNextM  = env->GetMethodID(iterCls,  "hasNext",  "()Z");
    jmethodID nextM     = env->GetMethodID(iterCls,  "next",     "()Ljava/lang/Object;");
    jmethodID getKeyM   = env->GetMethodID(entryCls, "getKey",   "()Ljava/lang/Object;");
    jmethodID getValueM = env->GetMethodID(entryCls, "getValue", "()Ljava/lang/Object;");
    jobject entrySet = env->CallObjectMethod(map, entrySetM);
    jobject iter     = env->CallObjectMethod(entrySet, iteratorM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject entry = env->CallObjectMethod(iter, nextM);
        jstring k     = static_cast<jstring>(env->CallObjectMethod(entry, getKeyM));
        jstring v     = static_cast<jstring>(env->CallObjectMethod(entry, getValueM));
        out[jstring2string(env, k)] = jstring2string(env, v);
        env->DeleteLocalRef(v);
        env->DeleteLocalRef(k);
        env->DeleteLocalRef(entry);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(entrySet);
    env->DeleteLocalRef(entryCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    env->DeleteLocalRef(mapCls);
    return out;
}

inline jobject make_map_string_string(
        JNIEnv* env,
        const std::unordered_map<std::string, std::string>& map) {
    jclass cls    = env->FindClass("java/util/HashMap");
    jmethodID ctor = env->GetMethodID(cls, "<init>", "(I)V");
    jmethodID put  = env->GetMethodID(cls, "put",
                         "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;");
    jobject result = env->NewObject(cls, ctor, static_cast<jint>(map.size()));
    for (const auto& [k, v] : map) {
        jstring jk = env->NewStringUTF(k.c_str());
        jstring jv = env->NewStringUTF(v.c_str());
        jobject prev = env->CallObjectMethod(result, put, jk, jv);
        if (prev) env->DeleteLocalRef(prev);
        env->DeleteLocalRef(jv);
        env->DeleteLocalRef(jk);
    }
    env->DeleteLocalRef(cls);
    return result;
}

#endif  // JNI_BINDING_GENERATOR_JNI_UTILS_H
