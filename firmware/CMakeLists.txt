cmake_minimum_required(VERSION 3.16)

# Register project-local components
set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/components/hal"
    "${CMAKE_CURRENT_LIST_DIR}/components/avionics"
    "${CMAKE_CURRENT_LIST_DIR}/components/networking"
    "${CMAKE_CURRENT_LIST_DIR}/components/web_ui"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(copperpilot_drone_firmware)
