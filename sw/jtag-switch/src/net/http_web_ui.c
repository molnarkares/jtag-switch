/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * HTTP Web UI Resources Implementation - STATIC Pattern
 */

#include <zephyr/kernel.h>
#include <zephyr/net/http/service.h>
#include <zephyr/net/http/server.h>
#include <zephyr/logging/log.h>
#include <stdint.h>

#include "http_web_ui.h"

LOG_MODULE_REGISTER(http_web_ui, LOG_LEVEL_INF);

/* Embedded web resources (in FLASH/ROM) - UNCOMPRESSED */
static const uint8_t index_html[] = {
	#include "index.html.gz.inc"
};

static const uint8_t style_css[] = {
	#include "style.css.gz.inc"
};

static const uint8_t app_js[] = {
	#include "app.js.gz.inc"
};

/* STATIC resource definitions - following Zephyr sample pattern */

struct http_resource_detail_static index_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_STATIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_GET),
		.content_type = "text/html",
		.content_encoding = "gzip"
	},
	.static_data = index_html,
	.static_data_len = sizeof(index_html),
};

struct http_resource_detail_static style_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_STATIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_GET),
		.content_type = "text/css",
		.content_encoding = "gzip"
	},
	.static_data = style_css,
	.static_data_len = sizeof(style_css),
};

struct http_resource_detail_static app_js_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_STATIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_GET),
		.content_type = "text/javascript",
		.content_encoding = "gzip"
	},
	.static_data = app_js,
	.static_data_len = sizeof(app_js),
};
