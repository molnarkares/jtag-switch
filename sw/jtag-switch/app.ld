/*
 * Custom linker script fragment for HTTP resources
 */

#include <zephyr/linker/iterable_sections.h>

ITERABLE_SECTION_ROM(http_resource_desc_jtag_switch_service, Z_LINK_ITERABLE_SUBALIGN)
