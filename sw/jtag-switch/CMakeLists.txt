# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.20.0)

# Add application-specific board root for custom boards (e.g., frdm_k64f_virtual)
list(APPEND BOARD_ROOT ${CMAKE_CURRENT_SOURCE_DIR})

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(jtag_switch)

target_sources(app PRIVATE
    src/main.c
        src/gpio/gpio_control.c
)

# Conditionally compile shell commands when enabled
target_sources_ifdef(CONFIG_SHELL app PRIVATE
        src/serial/shell_cmds.c
)

# Conditionally compile networking when enabled
target_sources_ifdef(CONFIG_NETWORKING app PRIVATE
        src/net/network_config.c
        src/net/http_api.c
        src/net/http_rest_api.c
        src/net/http_web_ui.c
)

# Generate web resources (both compressed and uncompressed for testing)
set(gen_dir ${ZEPHYR_BINARY_DIR}/include/generated/)

foreach(web_resource index.html style.css app.js)
  # Generate gzipped version
  generate_inc_file_for_target(app
    web/${web_resource}
    ${gen_dir}/${web_resource}.gz.inc
    --gzip
  )
  # Generate uncompressed version for browser compatibility testing
  generate_inc_file_for_target(app
    web/${web_resource}
    ${gen_dir}/${web_resource}.inc
  )
endforeach()

# Add custom linker script for HTTP resources
zephyr_linker_sources(SECTIONS app.ld)
zephyr_linker_section_ifdef(CONFIG_HTTP_SERVER NAME
    http_resource_desc_jtag_switch_service
    KVMA RAM_REGION GROUP RODATA_REGION
)
