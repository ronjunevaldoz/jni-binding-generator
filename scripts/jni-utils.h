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
#include <unordered_set>
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

inline std::vector<int16_t> extract_short_array(JNIEnv* env, jshortArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<int16_t> out(static_cast<size_t>(len));
    if (len > 0) {
        env->GetShortArrayRegion(arr, 0, len, reinterpret_cast<jshort*>(out.data()));
    }
    return out;
}

inline std::vector<double> extract_double_array(JNIEnv* env, jdoubleArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<double> out(static_cast<size_t>(len));
    if (len > 0) {
        env->GetDoubleArrayRegion(arr, 0, len, out.data());
    }
    return out;
}

inline std::vector<bool> extract_bool_array(JNIEnv* env, jbooleanArray arr) {
    if (arr == nullptr) {
        return {};
    }
    const jsize len = env->GetArrayLength(arr);
    std::vector<jboolean> raw(static_cast<size_t>(len));
    if (len > 0) {
        env->GetBooleanArrayRegion(arr, 0, len, raw.data());
    }
    std::vector<bool> out;
    out.reserve(static_cast<size_t>(len));
    for (jboolean b : raw) {
        out.push_back(b == JNI_TRUE);
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
// Enum marshalling (Kotlin enum -> int32_t ordinal)
// --------------------------------------------------------------------------- //

// Extract the ordinal of any Kotlin/Java enum passed as jobject.
// In the generated stub the parameter type is jobject; cast it before calling.
// Returns -1 if enumObj is null.
inline int32_t enum_ordinal(JNIEnv* env, jobject enumObj) {
    if (!enumObj) return -1;
    jclass cls        = env->GetObjectClass(enumObj);
    jmethodID ordinalM = env->GetMethodID(cls, "ordinal", "()I");
    jint ord = env->CallIntMethod(enumObj, ordinalM);
    env->DeleteLocalRef(cls);
    return static_cast<int32_t>(ord);
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

inline std::vector<bool> extract_list_bool(JNIEnv* env, jobject list) {
    std::vector<bool> out;
    if (!list) return out;
    jclass listCls   = env->FindClass("java/util/List");
    jclass boolCls   = env->FindClass("java/lang/Boolean");
    jmethodID sizeM  = env->GetMethodID(listCls,  "size",         "()I");
    jmethodID getM   = env->GetMethodID(listCls,  "get",          "(I)Ljava/lang/Object;");
    jmethodID valM   = env->GetMethodID(boolCls,  "booleanValue", "()Z");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jobject elem = env->CallObjectMethod(list, getM, i);
        out.push_back(env->CallBooleanMethod(elem, valM) == JNI_TRUE);
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(boolCls);
    env->DeleteLocalRef(listCls);
    return out;
}

inline std::vector<int8_t> extract_list_byte(JNIEnv* env, jobject list) {
    std::vector<int8_t> out;
    if (!list) return out;
    jclass listCls  = env->FindClass("java/util/List");
    jclass byteCls  = env->FindClass("java/lang/Byte");
    jmethodID sizeM = env->GetMethodID(listCls, "size",      "()I");
    jmethodID getM  = env->GetMethodID(listCls, "get",       "(I)Ljava/lang/Object;");
    jmethodID valM  = env->GetMethodID(byteCls, "byteValue", "()B");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jobject elem = env->CallObjectMethod(list, getM, i);
        out.push_back(static_cast<int8_t>(env->CallByteMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(byteCls);
    env->DeleteLocalRef(listCls);
    return out;
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

inline jobject make_list_long(JNIEnv* env, const std::vector<int64_t>& vec) {
    jclass listCls  = env->FindClass("java/util/ArrayList");
    jclass longCls  = env->FindClass("java/lang/Long");
    jmethodID ctor    = env->GetMethodID(listCls, "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(listCls, "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(longCls, "valueOf", "(J)Ljava/lang/Long;");
    jobject list = env->NewObject(listCls, ctor, static_cast<jint>(vec.size()));
    for (int64_t v : vec) {
        jobject boxed = env->CallStaticObjectMethod(longCls, valueOf, static_cast<jlong>(v));
        env->CallBooleanMethod(list, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(longCls);
    env->DeleteLocalRef(listCls);
    return list;
}

inline jobject make_list_float(JNIEnv* env, const std::vector<float>& vec) {
    jclass listCls  = env->FindClass("java/util/ArrayList");
    jclass floatCls = env->FindClass("java/lang/Float");
    jmethodID ctor    = env->GetMethodID(listCls,  "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(listCls,  "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(floatCls, "valueOf", "(F)Ljava/lang/Float;");
    jobject list = env->NewObject(listCls, ctor, static_cast<jint>(vec.size()));
    for (float v : vec) {
        jobject boxed = env->CallStaticObjectMethod(floatCls, valueOf, static_cast<jfloat>(v));
        env->CallBooleanMethod(list, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(floatCls);
    env->DeleteLocalRef(listCls);
    return list;
}

inline jobject make_list_double(JNIEnv* env, const std::vector<double>& vec) {
    jclass listCls   = env->FindClass("java/util/ArrayList");
    jclass doubleCls = env->FindClass("java/lang/Double");
    jmethodID ctor    = env->GetMethodID(listCls,   "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(listCls,   "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(doubleCls, "valueOf", "(D)Ljava/lang/Double;");
    jobject list = env->NewObject(listCls, ctor, static_cast<jint>(vec.size()));
    for (double v : vec) {
        jobject boxed = env->CallStaticObjectMethod(doubleCls, valueOf, static_cast<jdouble>(v));
        env->CallBooleanMethod(list, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(doubleCls);
    env->DeleteLocalRef(listCls);
    return list;
}

inline jobject make_list_bool(JNIEnv* env, const std::vector<bool>& vec) {
    jclass listCls  = env->FindClass("java/util/ArrayList");
    jclass boolCls  = env->FindClass("java/lang/Boolean");
    jmethodID ctor    = env->GetMethodID(listCls, "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(listCls, "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(boolCls, "valueOf", "(Z)Ljava/lang/Boolean;");
    jobject list = env->NewObject(listCls, ctor, static_cast<jint>(vec.size()));
    for (bool v : vec) {
        jobject boxed = env->CallStaticObjectMethod(boolCls, valueOf, v ? JNI_TRUE : JNI_FALSE);
        env->CallBooleanMethod(list, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(boolCls);
    env->DeleteLocalRef(listCls);
    return list;
}

inline jobject make_list_byte(JNIEnv* env, const std::vector<int8_t>& vec) {
    jclass listCls  = env->FindClass("java/util/ArrayList");
    jclass byteCls  = env->FindClass("java/lang/Byte");
    jmethodID ctor    = env->GetMethodID(listCls, "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(listCls, "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(byteCls, "valueOf", "(B)Ljava/lang/Byte;");
    jobject list = env->NewObject(listCls, ctor, static_cast<jint>(vec.size()));
    for (int8_t v : vec) {
        jobject boxed = env->CallStaticObjectMethod(byteCls, valueOf, static_cast<jbyte>(v));
        env->CallBooleanMethod(list, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(byteCls);
    env->DeleteLocalRef(listCls);
    return list;
}

inline std::vector<int16_t> extract_list_short(JNIEnv* env, jobject list) {
    std::vector<int16_t> out;
    if (!list) return out;
    jclass listCls   = env->FindClass("java/util/List");
    jclass shortCls  = env->FindClass("java/lang/Short");
    jmethodID sizeM  = env->GetMethodID(listCls,  "size",       "()I");
    jmethodID getM   = env->GetMethodID(listCls,  "get",        "(I)Ljava/lang/Object;");
    jmethodID valM   = env->GetMethodID(shortCls, "shortValue", "()S");
    jint len = env->CallIntMethod(list, sizeM);
    out.reserve(static_cast<size_t>(len));
    for (jint i = 0; i < len; ++i) {
        jobject elem = env->CallObjectMethod(list, getM, i);
        out.push_back(static_cast<int16_t>(env->CallShortMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(shortCls);
    env->DeleteLocalRef(listCls);
    return out;
}

inline jobject make_list_short(JNIEnv* env, const std::vector<int16_t>& vec) {
    jclass listCls  = env->FindClass("java/util/ArrayList");
    jclass shortCls = env->FindClass("java/lang/Short");
    jmethodID ctor    = env->GetMethodID(listCls,  "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(listCls,  "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(shortCls, "valueOf", "(S)Ljava/lang/Short;");
    jobject list = env->NewObject(listCls, ctor, static_cast<jint>(vec.size()));
    for (int16_t v : vec) {
        jobject boxed = env->CallStaticObjectMethod(shortCls, valueOf, static_cast<jshort>(v));
        env->CallBooleanMethod(list, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(shortCls);
    env->DeleteLocalRef(listCls);
    return list;
}

// --------------------------------------------------------------------------- //
// Boxed object-array marshalling  Array<Int>, Array<Long>, etc.  (Java -> C++)
// --------------------------------------------------------------------------- //

inline std::vector<int32_t> extract_boxed_int_array(JNIEnv* env, jobjectArray arr) {
    std::vector<int32_t> out;
    if (!arr) return out;
    jclass intCls   = env->FindClass("java/lang/Integer");
    jmethodID valM  = env->GetMethodID(intCls, "intValue", "()I");
    jsize len = env->GetArrayLength(arr);
    out.reserve(static_cast<size_t>(len));
    for (jsize i = 0; i < len; ++i) {
        jobject elem = env->GetObjectArrayElement(arr, i);
        out.push_back(static_cast<int32_t>(env->CallIntMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(intCls);
    return out;
}

inline std::vector<int64_t> extract_boxed_long_array(JNIEnv* env, jobjectArray arr) {
    std::vector<int64_t> out;
    if (!arr) return out;
    jclass longCls  = env->FindClass("java/lang/Long");
    jmethodID valM  = env->GetMethodID(longCls, "longValue", "()J");
    jsize len = env->GetArrayLength(arr);
    out.reserve(static_cast<size_t>(len));
    for (jsize i = 0; i < len; ++i) {
        jobject elem = env->GetObjectArrayElement(arr, i);
        out.push_back(static_cast<int64_t>(env->CallLongMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(longCls);
    return out;
}

inline std::vector<float> extract_boxed_float_array(JNIEnv* env, jobjectArray arr) {
    std::vector<float> out;
    if (!arr) return out;
    jclass floatCls = env->FindClass("java/lang/Float");
    jmethodID valM  = env->GetMethodID(floatCls, "floatValue", "()F");
    jsize len = env->GetArrayLength(arr);
    out.reserve(static_cast<size_t>(len));
    for (jsize i = 0; i < len; ++i) {
        jobject elem = env->GetObjectArrayElement(arr, i);
        out.push_back(static_cast<float>(env->CallFloatMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(floatCls);
    return out;
}

inline std::vector<double> extract_boxed_double_array(JNIEnv* env, jobjectArray arr) {
    std::vector<double> out;
    if (!arr) return out;
    jclass doubleCls = env->FindClass("java/lang/Double");
    jmethodID valM   = env->GetMethodID(doubleCls, "doubleValue", "()D");
    jsize len = env->GetArrayLength(arr);
    out.reserve(static_cast<size_t>(len));
    for (jsize i = 0; i < len; ++i) {
        jobject elem = env->GetObjectArrayElement(arr, i);
        out.push_back(static_cast<double>(env->CallDoubleMethod(elem, valM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(doubleCls);
    return out;
}

// --------------------------------------------------------------------------- //
// Nested-collection marshalling
// --------------------------------------------------------------------------- //

inline std::vector<std::vector<std::string>>
extract_list_list_string(JNIEnv* env, jobject outerList) {
    std::vector<std::vector<std::string>> out;
    if (!outerList) return out;
    jclass listCls  = env->FindClass("java/util/List");
    jmethodID sizeM = env->GetMethodID(listCls, "size", "()I");
    jmethodID getM  = env->GetMethodID(listCls, "get",  "(I)Ljava/lang/Object;");
    jint outerLen = env->CallIntMethod(outerList, sizeM);
    out.reserve(static_cast<size_t>(outerLen));
    for (jint i = 0; i < outerLen; ++i) {
        jobject inner = env->CallObjectMethod(outerList, getM, i);
        out.push_back(extract_list_string(env, inner));
        env->DeleteLocalRef(inner);
    }
    env->DeleteLocalRef(listCls);
    return out;
}

inline jobject make_list_list_string(
        JNIEnv* env,
        const std::vector<std::vector<std::string>>& outer) {
    jclass cls    = env->FindClass("java/util/ArrayList");
    jmethodID ctor = env->GetMethodID(cls, "<init>", "(I)V");
    jmethodID add  = env->GetMethodID(cls, "add",    "(Ljava/lang/Object;)Z");
    jobject result = env->NewObject(cls, ctor, static_cast<jint>(outer.size()));
    for (const auto& inner : outer) {
        jobject innerList = make_list_string(env, inner);
        env->CallBooleanMethod(result, add, innerList);
        env->DeleteLocalRef(innerList);
    }
    env->DeleteLocalRef(cls);
    return result;
}

// --------------------------------------------------------------------------- //
// Set marshalling (java.util.Set <-> C++)
// --------------------------------------------------------------------------- //

inline std::unordered_set<std::string> extract_set_string(JNIEnv* env, jobject set) {
    std::unordered_set<std::string> out;
    if (!set) return out;
    jclass setCls  = env->FindClass("java/util/Set");
    jclass iterCls = env->FindClass("java/util/Iterator");
    jmethodID iterM    = env->GetMethodID(setCls,  "iterator", "()Ljava/util/Iterator;");
    jmethodID hasNextM = env->GetMethodID(iterCls, "hasNext",  "()Z");
    jmethodID nextM    = env->GetMethodID(iterCls, "next",     "()Ljava/lang/Object;");
    jobject iter = env->CallObjectMethod(set, iterM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jstring elem = static_cast<jstring>(env->CallObjectMethod(iter, nextM));
        out.insert(jstring2string(env, elem));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    return out;
}

inline std::unordered_set<int32_t> extract_set_int(JNIEnv* env, jobject set) {
    std::unordered_set<int32_t> out;
    if (!set) return out;
    jclass setCls  = env->FindClass("java/util/Set");
    jclass iterCls = env->FindClass("java/util/Iterator");
    jclass intCls  = env->FindClass("java/lang/Integer");
    jmethodID iterM    = env->GetMethodID(setCls,  "iterator", "()Ljava/util/Iterator;");
    jmethodID hasNextM = env->GetMethodID(iterCls, "hasNext",  "()Z");
    jmethodID nextM    = env->GetMethodID(iterCls, "next",     "()Ljava/lang/Object;");
    jmethodID intValM  = env->GetMethodID(intCls,  "intValue", "()I");
    jobject iter = env->CallObjectMethod(set, iterM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject elem = env->CallObjectMethod(iter, nextM);
        out.insert(static_cast<int32_t>(env->CallIntMethod(elem, intValM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    return out;
}

inline jobject make_set_string(JNIEnv* env, const std::unordered_set<std::string>& set) {
    jclass cls    = env->FindClass("java/util/HashSet");
    jmethodID ctor = env->GetMethodID(cls, "<init>", "(I)V");
    jmethodID add  = env->GetMethodID(cls, "add",    "(Ljava/lang/Object;)Z");
    jobject result = env->NewObject(cls, ctor, static_cast<jint>(set.size()));
    for (const auto& s : set) {
        jstring jstr = env->NewStringUTF(s.c_str());
        env->CallBooleanMethod(result, add, jstr);
        env->DeleteLocalRef(jstr);
    }
    env->DeleteLocalRef(cls);
    return result;
}

inline jobject make_set_int(JNIEnv* env, const std::unordered_set<int32_t>& set) {
    jclass setCls = env->FindClass("java/util/HashSet");
    jclass intCls = env->FindClass("java/lang/Integer");
    jmethodID ctor    = env->GetMethodID(setCls, "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(setCls, "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(intCls, "valueOf", "(I)Ljava/lang/Integer;");
    jobject result = env->NewObject(setCls, ctor, static_cast<jint>(set.size()));
    for (int32_t v : set) {
        jobject boxed = env->CallStaticObjectMethod(intCls, valueOf, static_cast<jint>(v));
        env->CallBooleanMethod(result, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(setCls);
    return result;
}

inline std::unordered_set<int64_t> extract_set_long(JNIEnv* env, jobject set) {
    std::unordered_set<int64_t> out;
    if (!set) return out;
    jclass setCls  = env->FindClass("java/util/Set");
    jclass iterCls = env->FindClass("java/util/Iterator");
    jclass longCls = env->FindClass("java/lang/Long");
    jmethodID iterM    = env->GetMethodID(setCls,  "iterator",  "()Ljava/util/Iterator;");
    jmethodID hasNextM = env->GetMethodID(iterCls, "hasNext",   "()Z");
    jmethodID nextM    = env->GetMethodID(iterCls, "next",      "()Ljava/lang/Object;");
    jmethodID longValM = env->GetMethodID(longCls, "longValue", "()J");
    jobject iter = env->CallObjectMethod(set, iterM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject elem = env->CallObjectMethod(iter, nextM);
        out.insert(static_cast<int64_t>(env->CallLongMethod(elem, longValM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(longCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    return out;
}

inline jobject make_set_long(JNIEnv* env, const std::unordered_set<int64_t>& set) {
    jclass setCls  = env->FindClass("java/util/HashSet");
    jclass longCls = env->FindClass("java/lang/Long");
    jmethodID ctor    = env->GetMethodID(setCls,  "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(setCls,  "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(longCls, "valueOf", "(J)Ljava/lang/Long;");
    jobject result = env->NewObject(setCls, ctor, static_cast<jint>(set.size()));
    for (int64_t v : set) {
        jobject boxed = env->CallStaticObjectMethod(longCls, valueOf, static_cast<jlong>(v));
        env->CallBooleanMethod(result, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(longCls);
    env->DeleteLocalRef(setCls);
    return result;
}

inline std::unordered_set<float> extract_set_float(JNIEnv* env, jobject set) {
    std::unordered_set<float> out;
    if (!set) return out;
    jclass setCls   = env->FindClass("java/util/Set");
    jclass iterCls  = env->FindClass("java/util/Iterator");
    jclass floatCls = env->FindClass("java/lang/Float");
    jmethodID iterM     = env->GetMethodID(setCls,   "iterator",   "()Ljava/util/Iterator;");
    jmethodID hasNextM  = env->GetMethodID(iterCls,  "hasNext",    "()Z");
    jmethodID nextM     = env->GetMethodID(iterCls,  "next",       "()Ljava/lang/Object;");
    jmethodID floatValM = env->GetMethodID(floatCls, "floatValue", "()F");
    jobject iter = env->CallObjectMethod(set, iterM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject elem = env->CallObjectMethod(iter, nextM);
        out.insert(static_cast<float>(env->CallFloatMethod(elem, floatValM)));
        env->DeleteLocalRef(elem);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(floatCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    return out;
}

inline jobject make_set_float(JNIEnv* env, const std::unordered_set<float>& set) {
    jclass setCls   = env->FindClass("java/util/HashSet");
    jclass floatCls = env->FindClass("java/lang/Float");
    jmethodID ctor    = env->GetMethodID(setCls,   "<init>",  "(I)V");
    jmethodID add     = env->GetMethodID(setCls,   "add",     "(Ljava/lang/Object;)Z");
    jmethodID valueOf = env->GetStaticMethodID(floatCls, "valueOf", "(F)Ljava/lang/Float;");
    jobject result = env->NewObject(setCls, ctor, static_cast<jint>(set.size()));
    for (float v : set) {
        jobject boxed = env->CallStaticObjectMethod(floatCls, valueOf, static_cast<jfloat>(v));
        env->CallBooleanMethod(result, add, boxed);
        env->DeleteLocalRef(boxed);
    }
    env->DeleteLocalRef(floatCls);
    env->DeleteLocalRef(setCls);
    return result;
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

inline std::unordered_map<std::string, int32_t>
extract_map_string_int(JNIEnv* env, jobject map) {
    std::unordered_map<std::string, int32_t> out;
    if (!map) return out;
    jclass mapCls   = env->FindClass("java/util/Map");
    jclass setCls   = env->FindClass("java/util/Set");
    jclass iterCls  = env->FindClass("java/util/Iterator");
    jclass entryCls = env->FindClass("java/util/Map$Entry");
    jclass intCls   = env->FindClass("java/lang/Integer");
    jmethodID entrySetM = env->GetMethodID(mapCls,   "entrySet", "()Ljava/util/Set;");
    jmethodID iteratorM = env->GetMethodID(setCls,   "iterator", "()Ljava/util/Iterator;");
    jmethodID hasNextM  = env->GetMethodID(iterCls,  "hasNext",  "()Z");
    jmethodID nextM     = env->GetMethodID(iterCls,  "next",     "()Ljava/lang/Object;");
    jmethodID getKeyM   = env->GetMethodID(entryCls, "getKey",   "()Ljava/lang/Object;");
    jmethodID getValueM = env->GetMethodID(entryCls, "getValue", "()Ljava/lang/Object;");
    jmethodID intValM   = env->GetMethodID(intCls,   "intValue", "()I");
    jobject entrySet = env->CallObjectMethod(map, entrySetM);
    jobject iter     = env->CallObjectMethod(entrySet, iteratorM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject entry = env->CallObjectMethod(iter, nextM);
        jstring k     = static_cast<jstring>(env->CallObjectMethod(entry, getKeyM));
        jobject v     = env->CallObjectMethod(entry, getValueM);
        out[jstring2string(env, k)] = static_cast<int32_t>(env->CallIntMethod(v, intValM));
        env->DeleteLocalRef(v);
        env->DeleteLocalRef(k);
        env->DeleteLocalRef(entry);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(entrySet);
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(entryCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    env->DeleteLocalRef(mapCls);
    return out;
}

inline std::unordered_map<int32_t, std::string>
extract_map_int_string(JNIEnv* env, jobject map) {
    std::unordered_map<int32_t, std::string> out;
    if (!map) return out;
    jclass mapCls   = env->FindClass("java/util/Map");
    jclass setCls   = env->FindClass("java/util/Set");
    jclass iterCls  = env->FindClass("java/util/Iterator");
    jclass entryCls = env->FindClass("java/util/Map$Entry");
    jclass intCls   = env->FindClass("java/lang/Integer");
    jmethodID entrySetM = env->GetMethodID(mapCls,   "entrySet", "()Ljava/util/Set;");
    jmethodID iteratorM = env->GetMethodID(setCls,   "iterator", "()Ljava/util/Iterator;");
    jmethodID hasNextM  = env->GetMethodID(iterCls,  "hasNext",  "()Z");
    jmethodID nextM     = env->GetMethodID(iterCls,  "next",     "()Ljava/lang/Object;");
    jmethodID getKeyM   = env->GetMethodID(entryCls, "getKey",   "()Ljava/lang/Object;");
    jmethodID getValueM = env->GetMethodID(entryCls, "getValue", "()Ljava/lang/Object;");
    jmethodID intValM   = env->GetMethodID(intCls,   "intValue", "()I");
    jobject entrySet = env->CallObjectMethod(map, entrySetM);
    jobject iter     = env->CallObjectMethod(entrySet, iteratorM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject entry = env->CallObjectMethod(iter, nextM);
        jobject k     = env->CallObjectMethod(entry, getKeyM);
        jstring v     = static_cast<jstring>(env->CallObjectMethod(entry, getValueM));
        out[static_cast<int32_t>(env->CallIntMethod(k, intValM))] = jstring2string(env, v);
        env->DeleteLocalRef(v);
        env->DeleteLocalRef(k);
        env->DeleteLocalRef(entry);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(entrySet);
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(entryCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    env->DeleteLocalRef(mapCls);
    return out;
}

inline jobject make_map_string_int(
        JNIEnv* env,
        const std::unordered_map<std::string, int32_t>& map) {
    jclass mapCls  = env->FindClass("java/util/HashMap");
    jclass intCls  = env->FindClass("java/lang/Integer");
    jmethodID ctor    = env->GetMethodID(mapCls, "<init>", "(I)V");
    jmethodID put     = env->GetMethodID(mapCls, "put",
                            "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;");
    jmethodID valueOf = env->GetStaticMethodID(intCls, "valueOf", "(I)Ljava/lang/Integer;");
    jobject result = env->NewObject(mapCls, ctor, static_cast<jint>(map.size()));
    for (const auto& [k, v] : map) {
        jstring jk    = env->NewStringUTF(k.c_str());
        jobject jv    = env->CallStaticObjectMethod(intCls, valueOf, static_cast<jint>(v));
        jobject prev  = env->CallObjectMethod(result, put, jk, jv);
        if (prev) env->DeleteLocalRef(prev);
        env->DeleteLocalRef(jv);
        env->DeleteLocalRef(jk);
    }
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(mapCls);
    return result;
}

inline jobject make_map_int_string(
        JNIEnv* env,
        const std::unordered_map<int32_t, std::string>& map) {
    jclass mapCls  = env->FindClass("java/util/HashMap");
    jclass intCls  = env->FindClass("java/lang/Integer");
    jmethodID ctor    = env->GetMethodID(mapCls, "<init>", "(I)V");
    jmethodID put     = env->GetMethodID(mapCls, "put",
                            "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;");
    jmethodID valueOf = env->GetStaticMethodID(intCls, "valueOf", "(I)Ljava/lang/Integer;");
    jobject result = env->NewObject(mapCls, ctor, static_cast<jint>(map.size()));
    for (const auto& [k, v] : map) {
        jobject jk   = env->CallStaticObjectMethod(intCls, valueOf, static_cast<jint>(k));
        jstring jv   = env->NewStringUTF(v.c_str());
        jobject prev = env->CallObjectMethod(result, put, jk, jv);
        if (prev) env->DeleteLocalRef(prev);
        env->DeleteLocalRef(jv);
        env->DeleteLocalRef(jk);
    }
    env->DeleteLocalRef(intCls);
    env->DeleteLocalRef(mapCls);
    return result;
}

inline std::unordered_map<std::string, int64_t>
extract_map_string_long(JNIEnv* env, jobject map) {
    std::unordered_map<std::string, int64_t> out;
    if (!map) return out;
    jclass mapCls   = env->FindClass("java/util/Map");
    jclass setCls   = env->FindClass("java/util/Set");
    jclass iterCls  = env->FindClass("java/util/Iterator");
    jclass entryCls = env->FindClass("java/util/Map$Entry");
    jclass longCls  = env->FindClass("java/lang/Long");
    jmethodID entrySetM = env->GetMethodID(mapCls,   "entrySet",  "()Ljava/util/Set;");
    jmethodID iteratorM = env->GetMethodID(setCls,   "iterator",  "()Ljava/util/Iterator;");
    jmethodID hasNextM  = env->GetMethodID(iterCls,  "hasNext",   "()Z");
    jmethodID nextM     = env->GetMethodID(iterCls,  "next",      "()Ljava/lang/Object;");
    jmethodID getKeyM   = env->GetMethodID(entryCls, "getKey",    "()Ljava/lang/Object;");
    jmethodID getValueM = env->GetMethodID(entryCls, "getValue",  "()Ljava/lang/Object;");
    jmethodID longValM  = env->GetMethodID(longCls,  "longValue", "()J");
    jobject entrySet = env->CallObjectMethod(map, entrySetM);
    jobject iter     = env->CallObjectMethod(entrySet, iteratorM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject entry = env->CallObjectMethod(iter, nextM);
        jstring k     = static_cast<jstring>(env->CallObjectMethod(entry, getKeyM));
        jobject v     = env->CallObjectMethod(entry, getValueM);
        out[jstring2string(env, k)] = static_cast<int64_t>(env->CallLongMethod(v, longValM));
        env->DeleteLocalRef(v);
        env->DeleteLocalRef(k);
        env->DeleteLocalRef(entry);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(entrySet);
    env->DeleteLocalRef(longCls);
    env->DeleteLocalRef(entryCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    env->DeleteLocalRef(mapCls);
    return out;
}

inline jobject make_map_string_long(
        JNIEnv* env,
        const std::unordered_map<std::string, int64_t>& map) {
    jclass mapCls  = env->FindClass("java/util/HashMap");
    jclass longCls = env->FindClass("java/lang/Long");
    jmethodID ctor    = env->GetMethodID(mapCls, "<init>", "(I)V");
    jmethodID put     = env->GetMethodID(mapCls, "put",
                            "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;");
    jmethodID valueOf = env->GetStaticMethodID(longCls, "valueOf", "(J)Ljava/lang/Long;");
    jobject result = env->NewObject(mapCls, ctor, static_cast<jint>(map.size()));
    for (const auto& [k, v] : map) {
        jstring jk   = env->NewStringUTF(k.c_str());
        jobject jv   = env->CallStaticObjectMethod(longCls, valueOf, static_cast<jlong>(v));
        jobject prev = env->CallObjectMethod(result, put, jk, jv);
        if (prev) env->DeleteLocalRef(prev);
        env->DeleteLocalRef(jv);
        env->DeleteLocalRef(jk);
    }
    env->DeleteLocalRef(longCls);
    env->DeleteLocalRef(mapCls);
    return result;
}

inline std::unordered_map<std::string, float>
extract_map_string_float(JNIEnv* env, jobject map) {
    std::unordered_map<std::string, float> out;
    if (!map) return out;
    jclass mapCls   = env->FindClass("java/util/Map");
    jclass setCls   = env->FindClass("java/util/Set");
    jclass iterCls  = env->FindClass("java/util/Iterator");
    jclass entryCls = env->FindClass("java/util/Map$Entry");
    jclass floatCls = env->FindClass("java/lang/Float");
    jmethodID entrySetM  = env->GetMethodID(mapCls,   "entrySet",   "()Ljava/util/Set;");
    jmethodID iteratorM  = env->GetMethodID(setCls,   "iterator",   "()Ljava/util/Iterator;");
    jmethodID hasNextM   = env->GetMethodID(iterCls,  "hasNext",    "()Z");
    jmethodID nextM      = env->GetMethodID(iterCls,  "next",       "()Ljava/lang/Object;");
    jmethodID getKeyM    = env->GetMethodID(entryCls, "getKey",     "()Ljava/lang/Object;");
    jmethodID getValueM  = env->GetMethodID(entryCls, "getValue",   "()Ljava/lang/Object;");
    jmethodID floatValM  = env->GetMethodID(floatCls, "floatValue", "()F");
    jobject entrySet = env->CallObjectMethod(map, entrySetM);
    jobject iter     = env->CallObjectMethod(entrySet, iteratorM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject entry = env->CallObjectMethod(iter, nextM);
        jstring k     = static_cast<jstring>(env->CallObjectMethod(entry, getKeyM));
        jobject v     = env->CallObjectMethod(entry, getValueM);
        out[jstring2string(env, k)] = static_cast<float>(env->CallFloatMethod(v, floatValM));
        env->DeleteLocalRef(v);
        env->DeleteLocalRef(k);
        env->DeleteLocalRef(entry);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(entrySet);
    env->DeleteLocalRef(floatCls);
    env->DeleteLocalRef(entryCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    env->DeleteLocalRef(mapCls);
    return out;
}

inline jobject make_map_string_float(
        JNIEnv* env,
        const std::unordered_map<std::string, float>& map) {
    jclass mapCls   = env->FindClass("java/util/HashMap");
    jclass floatCls = env->FindClass("java/lang/Float");
    jmethodID ctor    = env->GetMethodID(mapCls, "<init>", "(I)V");
    jmethodID put     = env->GetMethodID(mapCls, "put",
                            "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;");
    jmethodID valueOf = env->GetStaticMethodID(floatCls, "valueOf", "(F)Ljava/lang/Float;");
    jobject result = env->NewObject(mapCls, ctor, static_cast<jint>(map.size()));
    for (const auto& [k, v] : map) {
        jstring jk   = env->NewStringUTF(k.c_str());
        jobject jv   = env->CallStaticObjectMethod(floatCls, valueOf, static_cast<jfloat>(v));
        jobject prev = env->CallObjectMethod(result, put, jk, jv);
        if (prev) env->DeleteLocalRef(prev);
        env->DeleteLocalRef(jv);
        env->DeleteLocalRef(jk);
    }
    env->DeleteLocalRef(floatCls);
    env->DeleteLocalRef(mapCls);
    return result;
}

inline std::unordered_map<std::string, bool>
extract_map_string_bool(JNIEnv* env, jobject map) {
    std::unordered_map<std::string, bool> out;
    if (!map) return out;
    jclass mapCls   = env->FindClass("java/util/Map");
    jclass setCls   = env->FindClass("java/util/Set");
    jclass iterCls  = env->FindClass("java/util/Iterator");
    jclass entryCls = env->FindClass("java/util/Map$Entry");
    jclass boolCls  = env->FindClass("java/lang/Boolean");
    jmethodID entrySetM  = env->GetMethodID(mapCls,   "entrySet",       "()Ljava/util/Set;");
    jmethodID iteratorM  = env->GetMethodID(setCls,   "iterator",       "()Ljava/util/Iterator;");
    jmethodID hasNextM   = env->GetMethodID(iterCls,  "hasNext",        "()Z");
    jmethodID nextM      = env->GetMethodID(iterCls,  "next",           "()Ljava/lang/Object;");
    jmethodID getKeyM    = env->GetMethodID(entryCls, "getKey",         "()Ljava/lang/Object;");
    jmethodID getValueM  = env->GetMethodID(entryCls, "getValue",       "()Ljava/lang/Object;");
    jmethodID boolValM   = env->GetMethodID(boolCls,  "booleanValue",   "()Z");
    jobject entrySet = env->CallObjectMethod(map, entrySetM);
    jobject iter     = env->CallObjectMethod(entrySet, iteratorM);
    while (env->CallBooleanMethod(iter, hasNextM)) {
        jobject entry = env->CallObjectMethod(iter, nextM);
        jstring k     = static_cast<jstring>(env->CallObjectMethod(entry, getKeyM));
        jobject v     = env->CallObjectMethod(entry, getValueM);
        out[jstring2string(env, k)] = (env->CallBooleanMethod(v, boolValM) == JNI_TRUE);
        env->DeleteLocalRef(v);
        env->DeleteLocalRef(k);
        env->DeleteLocalRef(entry);
    }
    env->DeleteLocalRef(iter);
    env->DeleteLocalRef(entrySet);
    env->DeleteLocalRef(boolCls);
    env->DeleteLocalRef(entryCls);
    env->DeleteLocalRef(iterCls);
    env->DeleteLocalRef(setCls);
    env->DeleteLocalRef(mapCls);
    return out;
}

inline jobject make_map_string_bool(
        JNIEnv* env,
        const std::unordered_map<std::string, bool>& map) {
    jclass mapCls  = env->FindClass("java/util/HashMap");
    jclass boolCls = env->FindClass("java/lang/Boolean");
    jmethodID ctor    = env->GetMethodID(mapCls, "<init>", "(I)V");
    jmethodID put     = env->GetMethodID(mapCls, "put",
                            "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;");
    jmethodID valueOf = env->GetStaticMethodID(boolCls, "valueOf", "(Z)Ljava/lang/Boolean;");
    jobject result = env->NewObject(mapCls, ctor, static_cast<jint>(map.size()));
    for (const auto& [k, v] : map) {
        jstring jk   = env->NewStringUTF(k.c_str());
        jobject jv   = env->CallStaticObjectMethod(boolCls, valueOf, v ? JNI_TRUE : JNI_FALSE);
        jobject prev = env->CallObjectMethod(result, put, jk, jv);
        if (prev) env->DeleteLocalRef(prev);
        env->DeleteLocalRef(jv);
        env->DeleteLocalRef(jk);
    }
    env->DeleteLocalRef(boolCls);
    env->DeleteLocalRef(mapCls);
    return result;
}

#endif  // JNI_BINDING_GENERATOR_JNI_UTILS_H
