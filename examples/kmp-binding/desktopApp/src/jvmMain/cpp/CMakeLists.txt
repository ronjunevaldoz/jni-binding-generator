cmake_minimum_required(VERSION 3.22)
project(kmmbinding LANGUAGES CXX)

# Generated JNI stubs — produced by jni-binding-generator.py targeting
# shared/src/desktopMain/kotlin.  Run `./gradlew :shared:generateJniDesktop`.
file(GLOB GENERATED_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/generated/*.gen.cpp")

add_library(kmmbinding SHARED
    native_impl.cpp
    ${GENERATED_SRCS}
)

target_include_directories(kmmbinding PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

target_compile_options(kmmbinding PRIVATE -std=c++17 -Wall -Wextra)

# On macOS/Linux link against the JDK's libjvm; on Windows link jvm.lib.
find_package(Java REQUIRED)
find_package(JNI REQUIRED)
target_link_libraries(kmmbinding ${JNI_LIBRARIES})
