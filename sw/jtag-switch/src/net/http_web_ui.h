/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * HTTP Web UI Resources
 */

#ifndef HTTP_WEB_UI_H
#define HTTP_WEB_UI_H

#include <zephyr/net/http/service.h>

/**
 * @brief Web UI STATIC resource details
 *
 * Serves web interface files (HTML, CSS, JS) as static resources.
 * Following Zephyr HTTP server best practices for static content.
 */
extern struct http_resource_detail_static index_resource_detail;
extern struct http_resource_detail_static style_resource_detail;
extern struct http_resource_detail_static app_js_resource_detail;

#endif /* HTTP_WEB_UI_H */
