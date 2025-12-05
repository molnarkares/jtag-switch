/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * HTTP REST API Endpoints
 */

#ifndef HTTP_REST_API_H
#define HTTP_REST_API_H

#include <zephyr/net/http/service.h>

/**
 * @brief REST API endpoint resource details
 *
 * These resource details are registered with the HTTP service
 * and define the handlers for each REST API endpoint.
 */
extern struct http_resource_detail_dynamic health_resource_detail;
extern struct http_resource_detail_dynamic status_resource_detail;
extern struct http_resource_detail_dynamic info_resource_detail;
extern struct http_resource_detail_dynamic select_resource_detail;
extern struct http_resource_detail_dynamic toggle_resource_detail;
extern struct http_resource_detail_dynamic network_config_resource_detail;

#endif /* HTTP_REST_API_H */
