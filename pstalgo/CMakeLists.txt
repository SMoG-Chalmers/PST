cmake_minimum_required(VERSION 2.8.9)
project(pstalgo)

set(CMAKE_BUILD_TYPE Release)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../bin)

# Mac: Set architectures to build for both x86_64 and arm64
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")

# We need C++11
include(CheckCXXCompilerFlag)
CHECK_CXX_COMPILER_FLAG("-std=c++14" COMPILER_SUPPORTS_CXX14)
CHECK_CXX_COMPILER_FLAG("-std=c++11" COMPILER_SUPPORTS_CXX11)
CHECK_CXX_COMPILER_FLAG("-std=c++0x" COMPILER_SUPPORTS_CXX0X)
if(COMPILER_SUPPORTS_CXX14)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14")
elseif(COMPILER_SUPPORTS_CXX11)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
elseif(COMPILER_SUPPORTS_CXX0X)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")
else()
        message(STATUS "The compiler ${CMAKE_CXX_COMPILER} has no C++11 support. Please use a different C++ compiler.")
endif()

# Include files
include_directories(include)

# Source files
file(GLOB_RECURSE SOURCES "src/*.cpp")

# Generate the shared library from the sources
add_library(pstalgo SHARED ${SOURCES})

# Set the location for library installation -- i.e., /usr/lib in this case
# install(TARGETS testStudent DESTINATION /usr/lib)
