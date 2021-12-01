cmake_minimum_required(VERSION 3.9)

project (testbench)

execute_process(COMMAND yosys-config --datdir OUTPUT_VARIABLE YOSYS_DATADIR OUTPUT_STRIP_TRAILING_WHITESPACE)

include_directories(${YOSYS_DATADIR}/include ${CMAKE_BINARY_DIR})

add_custom_command(OUTPUT blink.hpp COMMAND yosys -p "write_cxxrtl blink.hpp" ${CMAKE_SOURCE_DIR}/blink.v DEPENDS blink.v)

add_library(testbench SHARED main.cpp blink.hpp)
add_executable(standalone main.cpp blink.hpp)