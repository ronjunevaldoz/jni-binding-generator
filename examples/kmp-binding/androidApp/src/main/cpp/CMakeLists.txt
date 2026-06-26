cmake_minimum_required(VERSION 3.22.1)
project(kmmbinding LANGUAGES CXX)

# Generated JNI stubs — produced by jni-binding-generator.py targeting
# shared/src/androidMain/kotlin.  Run `./gradlew :shared:generateJniAndroid`
# or let preBuild do it automatically.
file(GLOB GENERATED_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/generated/*.gen.cpp")

add_library(kmmbinding SHARED
    native_impl.cpp
    ${GENERATED_SRCS}
)

target_include_directories(kmmbinding PRIVATE
    # Copy jni-utils.h here from scripts/ or adjust the path.
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

target_compile_options(kmmbinding PRIVATE
    -std=c++17
    -Wall
    -Wextra
    -fno-exceptions
    -fno-rtti
)

find_library(log-lib log)
target_link_libraries(kmmbinding ${log-lib})
