cmake_minimum_required(VERSION 3.13.1)

include(zeta.cmake NO_POLICY_SCOPE)
find_package(Zephyr HINTS $ENV{ZEPHYR_BASE})
project(project_name)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

list(APPEND HEADERS "${CMAKE_CURRENT_LIST_DIR}/include/")

include_directories(${HEADERS})
target_sources(app PRIVATE ${SOURCES})
