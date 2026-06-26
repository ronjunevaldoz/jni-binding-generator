cmake_minimum_required(VERSION 3.22)
project(image_classifier)

# Path to the jni-utils.h header (adjust relative to your project root).
set(JNI_UTILS_DIR "${CMAKE_SOURCE_DIR}/../../scripts")

add_library(
    image_classifier
    SHARED
    # Generated JNI entry-point stub — do not edit by hand.
    generated/ImageClassifier_jni.gen.cpp
    # Hand-written native implementation (not included in this example).
    # src/main/cpp/image_classifier_impl.cpp
)

target_include_directories(image_classifier PRIVATE
    ${JNI_UTILS_DIR}           # for jni-utils.h
    ${CMAKE_SOURCE_DIR}/include # your own native headers
)

# Standard Android log library (used by jni-utils.h throw helpers).
find_library(log-lib log)
target_link_libraries(image_classifier ${log-lib})
