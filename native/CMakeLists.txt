cmake_minimum_required(VERSION 3.24)
project(signallab_native LANGUAGES CXX)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)
find_package(TBB CONFIG REQUIRED)

pybind11_add_module(_native_core MODULE src/native_core.cpp)
target_compile_features(_native_core PRIVATE cxx_std_20)
target_link_libraries(_native_core PRIVATE TBB::tbb)

if(MSVC)
  target_compile_options(_native_core PRIVATE /O2 /Ob3 /GL /arch:AVX2 /EHsc /permissive-)
  target_link_options(_native_core PRIVATE /LTCG)
else()
  target_compile_options(_native_core PRIVATE -O3 -march=native)
endif()

set_target_properties(_native_core PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../backend/app"
  LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/../backend/app"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../backend/app"
  RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/../backend/app"
)

if(WIN32)
  add_custom_command(TARGET _native_core POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "$<TARGET_FILE:TBB::tbb>"
      "${CMAKE_CURRENT_SOURCE_DIR}/../backend/app/$<TARGET_FILE_NAME:TBB::tbb>"
  )
endif()
