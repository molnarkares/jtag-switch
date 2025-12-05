/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * HTTP REST API Module
 *
 * Provides REST API endpoints for remote control and monitoring
 * of the JTAG switch via HTTP over Ethernet.
 */

#ifndef HTTP_API_H
#define HTTP_API_H

#include <zephyr/kernel.h>

/**
 * @brief Initialize HTTP API server
 *
 * Starts the HTTP server and registers all REST API endpoints.
 * Network must be initialized before calling this function.
 *
 * Endpoints:
 * - GET  /api/v1/health - Health check
 * - GET  /api/v1/status - Full device status
 * - GET  /api/v1/info - System information
 * - GET  /api/v1/select/{line} - Get select line status
 * - POST /api/v1/select/{line} - Set select line
 * - POST /api/v1/select/{line}/toggle - Toggle select line
 * - POST /api/v1/select/batch - Set both lines
 *
 * @return 0 on success, negative errno on failure
 */
int http_api_init(void);

#endif /* HTTP_API_H */
