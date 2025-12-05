/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * HTTP Service Configuration and Registration
 */

#include <zephyr/kernel.h>
#include <zephyr/net/http/server.h>
#include <zephyr/net/http/service.h>
#include <zephyr/logging/log.h>

#include "http_api.h"
#include "http_rest_api.h"
#include "http_web_ui.h"

LOG_MODULE_REGISTER(http_api, LOG_LEVEL_INF);

/* Resource registration - must be defined before HTTP_SERVICE_DEFINE */

/* Root path serves gzipped index.html using STATIC resource */
HTTP_RESOURCE_DEFINE(index_resource, jtag_switch_service, "/", &index_resource_detail);
/* Alternate path for direct access */
HTTP_RESOURCE_DEFINE(index_alt_resource, jtag_switch_service, "/index.html", &index_resource_detail);
HTTP_RESOURCE_DEFINE(style_resource, jtag_switch_service, "/style.css", &style_resource_detail);
HTTP_RESOURCE_DEFINE(app_js_resource, jtag_switch_service, "/app.js", &app_js_resource_detail);

/* REST API endpoints */
HTTP_RESOURCE_DEFINE(health_resource, jtag_switch_service, "/api/health",
		     &health_resource_detail);
HTTP_RESOURCE_DEFINE(status_resource, jtag_switch_service, "/api/status",
		     &status_resource_detail);
HTTP_RESOURCE_DEFINE(info_resource, jtag_switch_service, "/api/info",
		     &info_resource_detail);
HTTP_RESOURCE_DEFINE(select_resource, jtag_switch_service, "/api/select",
		     &select_resource_detail);
HTTP_RESOURCE_DEFINE(toggle_resource, jtag_switch_service, "/api/toggle",
		     &toggle_resource_detail);
HTTP_RESOURCE_DEFINE(network_config_resource, jtag_switch_service, "/api/network/config",
		     &network_config_resource_detail);

/* HTTP service definition - must be after resource definitions */
static uint16_t http_port = 80;
HTTP_SERVICE_DEFINE(jtag_switch_service, NULL, &http_port,
		    CONFIG_HTTP_SERVER_MAX_CLIENTS, 10, NULL, NULL, NULL);

int http_api_init(void)
{
	int ret;

	LOG_INF("Initializing HTTP API server...");

	/* Start the HTTP server */
	ret = http_server_start();
	if (ret < 0) {
		LOG_ERR("Failed to start HTTP server: %d", ret);
		return ret;
	}

	LOG_INF("HTTP API server started on port %d", http_port);
	LOG_INF("Web UI available at http://192.168.1.x/");
	LOG_INF("API endpoints:");
	LOG_INF("  GET  /api/health        - Health check");
	LOG_INF("  GET  /api/status        - Get device status");
	LOG_INF("  GET  /api/info          - Get device information");
	LOG_INF("  POST /api/select        - Set select line");
	LOG_INF("  POST /api/toggle        - Toggle select line");
	LOG_INF("  POST /api/network/config - Configure network");

	return 0;
}
