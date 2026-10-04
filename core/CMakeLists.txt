cmake_minimum_required(VERSION 3.16)
project(scheduler_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(scheduler_core
    src/bindings.cpp
    src/genetic_algorithm.cpp
    src/backtracking.cpp
    src/fitness.cpp
)

target_include_directories(scheduler_core PRIVATE include)
