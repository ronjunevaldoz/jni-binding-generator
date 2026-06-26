// Stub implementations for the generated JNI declarations.
// Replace each function body with calls to your actual native library.
#include "generated/NativeBridge_jni.gen.cpp"

// Example: replace these with real calls to your inference engine.
// The generated bindings handle all JNI type conversions; you only
// deal with C++ types here.

jlong NativeBridge_nativeCreate_impl(
    JNIEnv* /*env*/, jobject /*obj*/,
    const std::string& modelPath, int threads, bool useGpu)
{
    (void)modelPath; (void)threads; (void)useGpu;
    return 0; // TODO: return real handle
}

void NativeBridge_nativeDestroy_impl(
    JNIEnv* /*env*/, jobject /*obj*/, jlong handle)
{
    (void)handle; // TODO: destroy real handle
}
