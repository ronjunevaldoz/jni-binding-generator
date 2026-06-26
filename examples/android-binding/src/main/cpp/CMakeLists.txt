cmake_minimum_required(VERSION 3.22.1)
project(myapp LANGUAGES CXX)

# All generated bindings land here after running jni-binding-generator.py.
file(GLOB GENERATED_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/generated/*.gen.cpp")

add_library(myapp SHARED
    native_impl.cpp
    ${GENERATED_SRCS}
)

target_include_directories(myapp PRIVATE
    # jni-utils.h ships with the generator; copy it here or adjust the path.
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

target_compile_options(myapp PRIVATE
    -std=c++17
    -Wall
    -Wextra
    -fno-exceptions
    -fno-rtti
)

find_library(log-lib log)
target_link_libraries(myapp ${log-lib})
