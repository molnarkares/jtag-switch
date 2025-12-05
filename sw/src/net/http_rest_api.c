/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * HTTP REST API Endpoints Implementation
 */

#include <zephyr/kernel.h>
#include <zephyr/net/http/server.h>
#include <zephyr/net/http/service.h>
#include <zephyr/net/socket.h>
#include <zephyr/data/json.h>
#include <zephyr/logging/log.h>
#include <string.h>
#include <stdio.h>
#include <zephyr/sys/sys_heap.h>

#include "http_rest_api.h"
#include "../gpio/gpio_control.h"
#include "network_config.h"

LOG_MODULE_REGISTER(http_rest_api, LOG_LEVEL_INF);

/* Kernel heap for runtime statistics */
extern struct k_heap _system_heap;

/* Buffer for building JSON responses */
#define JSON_BUFFER_SIZE 512
static char json_response_buffer[JSON_BUFFER_SIZE];

/* JSON parsing structures */
struct select_request {
	int line;
	int connector;
};

static const struct json_obj_descr select_request_descr[] = {
	JSON_OBJ_DESCR_PRIM(struct select_request, line, JSON_TOK_NUMBER),
	JSON_OBJ_DESCR_PRIM(struct select_request, connector, JSON_TOK_NUMBER),
};

struct toggle_request {
	int line;
};

static const struct json_obj_descr toggle_request_descr[] = {
	JSON_OBJ_DESCR_PRIM(struct toggle_request, line, JSON_TOK_NUMBER),
};

/* ========== JSON Response Structures ========== */

/* Common error response */
struct error_response {
	char *error;
};

static const struct json_obj_descr error_response_descr[] = {
	JSON_OBJ_DESCR_PRIM(struct error_response, error, JSON_TOK_STRING),
};

/* Device info - GET /api/info */
struct info_response {
	char *device;
	char version[16];
	char zephyr[16];
	char *board;
};

static const struct json_obj_descr info_response_descr[] = {
	JSON_OBJ_DESCR_PRIM(struct info_response, device, JSON_TOK_STRING),
	JSON_OBJ_DESCR_PRIM(struct info_response, version, JSON_TOK_STRING_BUF),
	JSON_OBJ_DESCR_PRIM(struct info_response, zephyr, JSON_TOK_STRING_BUF),
	JSON_OBJ_DESCR_PRIM(struct info_response, board, JSON_TOK_STRING),
};

/* GPIO select - POST /api/select */
struct select_response {
	bool success;
	bool select0;
	bool select1;
};

static const struct json_obj_descr select_response_descr[] = {
	JSON_OBJ_DESCR_PRIM(struct select_response, success, JSON_TOK_TRUE),
	JSON_OBJ_DESCR_PRIM(struct select_response, select0, JSON_TOK_TRUE),
	JSON_OBJ_DESCR_PRIM(struct select_response, select1, JSON_TOK_TRUE),
};

/* GPIO toggle - POST /api/toggle */
struct toggle_response {
	bool success;
	int line;
	bool state;
};

static const struct json_obj_descr toggle_response_descr[] = {
	JSON_OBJ_DESCR_PRIM(struct toggle_response, success, JSON_TOK_TRUE),
	JSON_OBJ_DESCR_PRIM(struct toggle_response, line, JSON_TOK_NUMBER),
	JSON_OBJ_DESCR_PRIM(struct toggle_response, state, JSON_TOK_TRUE),
};

/* Network config - POST /api/network/config */
struct success_restart_response {
	bool success;
	bool restart_required;
};

static const struct json_obj_descr success_restart_response_descr[] = {
	JSON_OBJ_DESCR_PRIM(struct success_restart_response, success, JSON_TOK_TRUE),
	JSON_OBJ_DESCR_PRIM(struct success_restart_response, restart_required, JSON_TOK_TRUE),
};

/* Health check endpoint - GET /api/health */
static int health_handler(struct http_client_ctx *client, enum http_data_status status,
			  const struct http_request_ctx *request_ctx,
			  struct http_response_ctx *response_ctx, void *user_data)
{
	if (status == HTTP_SERVER_DATA_FINAL) {
		struct status_response {
			char *status;
		};

		static const struct json_obj_descr status_response_descr[] = {
			JSON_OBJ_DESCR_PRIM(struct status_response, status, JSON_TOK_STRING_BUF),
		};

		const int ret = json_obj_encode_buf(status_response_descr, ARRAY_SIZE(status_response_descr),
					  "ok",
					  json_response_buffer, sizeof(json_response_buffer));
		if (ret == 0) {
			response_ctx->body = (const uint8_t *)json_response_buffer;
			response_ctx->body_len = strlen(json_response_buffer);
			response_ctx->final_chunk = true;
			response_ctx->status = HTTP_200_OK;
		}
	}
	return 0;
}

struct http_resource_detail_dynamic health_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_DYNAMIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_GET),
		.content_type = "application/json",
	},
	.cb = health_handler,
	.user_data = NULL,
};

/* Status endpoint - GET /api/status */
static int status_handler(struct http_client_ctx *client, enum http_data_status status,
			  const struct http_request_ctx *request_ctx,
			  struct http_response_ctx *response_ctx, void *user_data)
{

	int ret = 0;

	struct system_data {
		uint32_t uptime;
		uint32_t heap_used;
	};


	struct system_status_response_str{
		bool select0;
		bool select1;
		struct network_status network;
		struct system_data system;
	} system_status_response;

	const struct json_obj_descr network_descr[] = {
		JSON_OBJ_DESCR_PRIM(struct network_status, ip, JSON_TOK_STRING_BUF),
		JSON_OBJ_DESCR_PRIM(struct network_status, netmask, JSON_TOK_STRING_BUF),
		JSON_OBJ_DESCR_PRIM(struct network_status, gateway, JSON_TOK_STRING_BUF),
		JSON_OBJ_DESCR_PRIM(struct network_status, mac, JSON_TOK_STRING_BUF),
		JSON_OBJ_DESCR_PRIM(struct network_status, link_up, JSON_TOK_TRUE),
		JSON_OBJ_DESCR_PRIM(struct network_status, dhcp_enabled, JSON_TOK_TRUE)
	};

	const struct json_obj_descr system_descr[] = {
		JSON_OBJ_DESCR_PRIM(struct system_data, uptime, JSON_TOK_INT),
		JSON_OBJ_DESCR_PRIM(struct system_data, heap_used, JSON_TOK_INT)
	};

	const struct json_obj_descr system_status_response_descr[] = {
		JSON_OBJ_DESCR_PRIM(struct system_status_response_str, select0, JSON_TOK_TRUE),
		JSON_OBJ_DESCR_PRIM(struct system_status_response_str, select1, JSON_TOK_TRUE),
		JSON_OBJ_DESCR_OBJECT(struct system_status_response_str, network, network_descr),
		JSON_OBJ_DESCR_OBJECT(struct system_status_response_str, system, system_descr)
	};

	if (status == HTTP_SERVER_DATA_FINAL) {
		/* Get GPIO status */
		ret = gpio_control_get_select(0, &system_status_response.select0);
		if (ret < 0) {
			system_status_response.select0 = false;
		}

		ret = gpio_control_get_select(1, &system_status_response.select1);
		if (ret < 0) {
			system_status_response.select1 = false;
		}

		/* Get network status */
		ret = network_get_status(&system_status_response.network);
		if (ret < 0) {
			memset(&system_status_response.network, 0, sizeof(system_status_response.network));
			strcpy(system_status_response.network.ip, "unknown");
		}

		/* Get system uptime */
		const int64_t uptime_ms = k_uptime_get();
		system_status_response.system.uptime = (uint32_t)(uptime_ms / 1000);

		/* Get heap statistics */
		struct sys_memory_stats heap_stats = {0};

		if (sys_heap_runtime_stats_get(&_system_heap.heap, &heap_stats) == 0) {
			system_status_response.system.heap_used = (uint32_t)heap_stats.allocated_bytes;
		}else {
			system_status_response.system.heap_used = 0;
		}

		ret = json_obj_encode_buf(system_status_response_descr, ARRAY_SIZE(system_status_response_descr),
							  &system_status_response,
							  json_response_buffer, sizeof(json_response_buffer));
		if (ret == 0) {
			response_ctx->body = (const uint8_t *)json_response_buffer;
			response_ctx->body_len = strlen(json_response_buffer);
			response_ctx->final_chunk = true;
			response_ctx->status = HTTP_200_OK;
		}
	}
	return ret;
}

struct http_resource_detail_dynamic status_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_DYNAMIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_GET),
		.content_type = "application/json",
	},
	.cb = status_handler,
	.user_data = NULL,
};

/* Info endpoint - GET /api/info */
static int info_handler(struct http_client_ctx *client, enum http_data_status status,
			const struct http_request_ctx *request_ctx,
			struct http_response_ctx *response_ctx, void *user_data)
{
	if (status == HTTP_SERVER_DATA_FINAL) {
		struct info_response info = {
			.device = "JTAG Switch",
			.board = CONFIG_BOARD
		};

		strcpy(info.version, "1.0.0");

		const uint32_t version = sys_kernel_version_get();
		const uint32_t major = SYS_KERNEL_VER_MAJOR(version);
		const uint32_t minor = SYS_KERNEL_VER_MINOR(version);
		const uint32_t patch = SYS_KERNEL_VER_PATCHLEVEL(version);
		snprintf(info.zephyr, sizeof(info.zephyr), "%u.%u.%u", major, minor, patch);

		const int ret = json_obj_encode_buf(info_response_descr,
						   ARRAY_SIZE(info_response_descr),
						   &info,
						   json_response_buffer,
						   sizeof(json_response_buffer));

		if (ret == 0) {
			response_ctx->body = (const uint8_t *)json_response_buffer;
			response_ctx->body_len = strlen(json_response_buffer);
			response_ctx->final_chunk = true;
			response_ctx->status = HTTP_200_OK;
		} else {
			LOG_ERR("Failed to encode info response: %d", ret);
			response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
		}
	}
	return 0;
}

struct http_resource_detail_dynamic info_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_DYNAMIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_GET),
		.content_type = "application/json",
	},
	.cb = info_handler,
	.user_data = NULL,
};

/* Select control endpoint - POST /api/select */
static int select_handler(struct http_client_ctx *client, enum http_data_status status,
			  const struct http_request_ctx *request_ctx,
			  struct http_response_ctx *response_ctx, void *user_data)
{
	static uint8_t request_buffer[128];
	static size_t request_offset = 0;
	struct select_request req = {-1,-1};

	if (status == HTTP_SERVER_DATA_ABORTED) {
		request_offset = 0;
	}else {
		/* Accumulate request data */
		if (request_ctx->data_len > 0) {
			const size_t to_copy = MIN(request_ctx->data_len,
						 sizeof(request_buffer) - request_offset);
			memcpy(request_buffer + request_offset, request_ctx->data, to_copy);
			request_offset += to_copy;
		}
	}

	/* Process when final data arrives */
	if (status == HTTP_SERVER_DATA_FINAL) {
		/* Parse JSON */
		const int64_t parse_ret = json_obj_parse((char *) request_buffer, request_offset,
		                         select_request_descr,
		                         ARRAY_SIZE(select_request_descr),
		                         &req);

		if (parse_ret < 0 || req.line < 0 || req.line > 1 ||
		    req.connector < 0 || req.connector > 3) {
			struct error_response err = { .error = "Invalid request parameters" };
			const int ret = json_obj_encode_buf(error_response_descr,
							   ARRAY_SIZE(error_response_descr),
							   &err, json_response_buffer,
							   sizeof(json_response_buffer));
			if (ret < 0) {
				LOG_ERR("Failed to encode error: %d", ret);
				strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
			}
			response_ctx->status = HTTP_400_BAD_REQUEST;
		} else {
			/* Set the GPIO line */
			const bool value = (req.connector == 1 || req.connector == 3);
			const int ret = gpio_control_set_select(req.line, value);

			if (ret < 0) {
				struct error_response err = { .error = "Failed to set GPIO" };
				const int encode_ret = json_obj_encode_buf(error_response_descr,
								       ARRAY_SIZE(error_response_descr),
								       &err, json_response_buffer,
								       sizeof(json_response_buffer));
				if (encode_ret < 0) {
					LOG_ERR("Failed to encode error: %d", encode_ret);
					strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
				}
				response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
			} else {
				/* Read both GPIO states to return complete status */
				struct select_response resp = { .success = true };
				gpio_control_get_select(0, &resp.select0);
				gpio_control_get_select(1, &resp.select1);

				const int encode_ret = json_obj_encode_buf(select_response_descr,
								       ARRAY_SIZE(select_response_descr),
								       &resp, json_response_buffer,
								       sizeof(json_response_buffer));
				if (encode_ret == 0) {
					response_ctx->status = HTTP_200_OK;
				} else {
					LOG_ERR("Failed to encode select response: %d", encode_ret);
					strcpy(json_response_buffer, "{\"error\":\"Encoding failed\"}");
					response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
				}
			}
		}

		response_ctx->body = (const uint8_t *)json_response_buffer;
		response_ctx->body_len = strlen(json_response_buffer);
		response_ctx->final_chunk = true;
		request_offset = 0;
	}

	return 0;
}

struct http_resource_detail_dynamic select_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_DYNAMIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_POST),
		.content_type = "application/json",
	},
	.cb = select_handler,
	.user_data = NULL,
};

/* Toggle control endpoint - POST /api/toggle */
static int toggle_handler(struct http_client_ctx *client, enum http_data_status status,
			  const struct http_request_ctx *request_ctx,
			  struct http_response_ctx *response_ctx, void *user_data)
{
	static uint8_t request_buffer[128];
	static size_t request_offset = 0;
	struct toggle_request req = {-1};

	if (status == HTTP_SERVER_DATA_ABORTED) {
		request_offset = 0;
	}else {
		/* Accumulate request data */
		if (request_ctx->data_len > 0) {
			const size_t to_copy = MIN(request_ctx->data_len,
						 sizeof(request_buffer) - request_offset);
			memcpy(request_buffer + request_offset, request_ctx->data, to_copy);
			request_offset += to_copy;
		}
	}

	/* Process when final data arrives */
	if (status == HTTP_SERVER_DATA_FINAL) {
		/* Parse JSON */
		const int64_t parse_ret = json_obj_parse((char *)request_buffer, request_offset,
				    toggle_request_descr,
				    ARRAY_SIZE(toggle_request_descr),
				    &req);

		if (parse_ret < 0 || req.line < 0 || req.line > 1) {
			struct error_response err = { .error = "Invalid line parameter" };
			const int ret = json_obj_encode_buf(error_response_descr,
							   ARRAY_SIZE(error_response_descr),
							   &err, json_response_buffer,
							   sizeof(json_response_buffer));
			if (ret < 0) {
				LOG_ERR("Failed to encode error: %d", ret);
				strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
			}
			response_ctx->status = HTTP_400_BAD_REQUEST;
		} else {
			/* Toggle the GPIO line */
			const int ret = gpio_control_toggle_select(req.line);

			if (ret < 0) {
				struct error_response err = { .error = "Failed to toggle GPIO" };
				const int encode_ret = json_obj_encode_buf(error_response_descr,
								       ARRAY_SIZE(error_response_descr),
								       &err, json_response_buffer,
								       sizeof(json_response_buffer));
				if (encode_ret < 0) {
					LOG_ERR("Failed to encode error: %d", encode_ret);
					strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
				}
				response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
			} else {
				struct toggle_response resp = {
					.success = true,
					.line = req.line
				};
				gpio_control_get_select(req.line, &resp.state);

				const int encode_ret = json_obj_encode_buf(toggle_response_descr,
								       ARRAY_SIZE(toggle_response_descr),
								       &resp, json_response_buffer,
								       sizeof(json_response_buffer));
				if (encode_ret == 0) {
					response_ctx->status = HTTP_200_OK;
				} else {
					LOG_ERR("Failed to encode toggle response: %d", encode_ret);
					strcpy(json_response_buffer, "{\"error\":\"Encoding failed\"}");
					response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
				}
			}
		}

		response_ctx->body = (const uint8_t *)json_response_buffer;
		response_ctx->body_len = strlen(json_response_buffer);
		response_ctx->final_chunk = true;
		request_offset = 0;
	}

	return 0;
}

struct http_resource_detail_dynamic toggle_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_DYNAMIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_POST),
		.content_type = "application/json",
	},
	.cb = toggle_handler,
	.user_data = NULL,
};

/* Network configuration endpoint - POST /api/network/config */
static int network_config_handler(struct http_client_ctx *client, enum http_data_status status,
				   const struct http_request_ctx *request_ctx,
				   struct http_response_ctx *response_ctx, void *user_data)
{
	static uint8_t request_buffer[256];
	static size_t request_offset = 0;

	if (status == HTTP_SERVER_DATA_ABORTED) {
		request_offset = 0;
	} else {
		/* Accumulate request data */
		if (request_ctx->data_len > 0) {
			const size_t to_copy = MIN(request_ctx->data_len,
						 sizeof(request_buffer) - request_offset);
			memcpy(request_buffer + request_offset, request_ctx->data, to_copy);
			request_offset += to_copy;
		}
	}

	/* Process when final data arrives */
	if (status == HTTP_SERVER_DATA_FINAL) {
		/* Null-terminate the JSON string */
		if (request_offset < sizeof(request_buffer)) {
			request_buffer[request_offset] = '\0';
		}

		/* Simple parsing - look for "mode":"dhcp" or "mode":"static" */
		const char *mode_ptr = strstr((char *)request_buffer, "\"mode\"");
		if (mode_ptr == NULL) {
			struct error_response err = { .error = "Missing mode parameter" };
			const int ret = json_obj_encode_buf(error_response_descr,
							   ARRAY_SIZE(error_response_descr),
							   &err, json_response_buffer,
							   sizeof(json_response_buffer));
			if (ret < 0) {
				LOG_ERR("Failed to encode error: %d", ret);
				strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
			}
			response_ctx->status = HTTP_400_BAD_REQUEST;
		} else {
			int ret;
			const bool is_dhcp = (strstr(mode_ptr, "dhcp") != NULL);

			if (is_dhcp) {
				/* Enable DHCP */
				ret = network_enable_dhcp();
				if (ret < 0) {
					struct error_response err = { .error = "Failed to enable DHCP" };
					const int encode_ret = json_obj_encode_buf(error_response_descr,
									       ARRAY_SIZE(error_response_descr),
									       &err, json_response_buffer,
									       sizeof(json_response_buffer));
					if (encode_ret < 0) {
						LOG_ERR("Failed to encode error: %d", encode_ret);
						strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
					}
					response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
				} else {
					/* Save configuration */
					network_config_save();

					struct success_restart_response resp = {
						.success = true,
						.restart_required = true
					};
					const int encode_ret = json_obj_encode_buf(success_restart_response_descr,
									       ARRAY_SIZE(success_restart_response_descr),
									       &resp, json_response_buffer,
									       sizeof(json_response_buffer));
					if (encode_ret == 0) {
						response_ctx->status = HTTP_200_OK;
					} else {
						LOG_ERR("Failed to encode response: %d", encode_ret);
						strcpy(json_response_buffer, "{\"error\":\"Encoding failed\"}");
						response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
					}

					/* Schedule network restart */
					network_restart();
				}
			} else {
				/* Parse static IP parameters (simple string search) */
				char ip[16] = {0}, netmask[16] = {0}, gateway[16] = {0};
				const char *ip_ptr = strstr((char *)request_buffer, "\"ip\"");
				const char *nm_ptr = strstr((char *)request_buffer, "\"netmask\"");
				const char *gw_ptr = strstr((char *)request_buffer, "\"gateway\"");

				if (ip_ptr && nm_ptr && gw_ptr) {
					/* Extract IP address */
					sscanf(ip_ptr, "\"ip\":\"%15[0-9.]\"", ip);
					sscanf(nm_ptr, "\"netmask\":\"%15[0-9.]\"", netmask);
					sscanf(gw_ptr, "\"gateway\":\"%15[0-9.]\"", gateway);

					ret = network_set_static_ip(ip, netmask, gateway);
					if (ret < 0) {
						struct error_response err = { .error = "Failed to set static IP" };
						const int encode_ret = json_obj_encode_buf(error_response_descr,
										       ARRAY_SIZE(error_response_descr),
										       &err, json_response_buffer,
										       sizeof(json_response_buffer));
						if (encode_ret < 0) {
							LOG_ERR("Failed to encode error: %d", encode_ret);
							strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
						}
						response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
					} else {
						/* Save configuration */
						network_config_save();

						struct success_restart_response resp = {
							.success = true,
							.restart_required = true
						};
						const int encode_ret = json_obj_encode_buf(success_restart_response_descr,
										       ARRAY_SIZE(success_restart_response_descr),
										       &resp, json_response_buffer,
										       sizeof(json_response_buffer));
						if (encode_ret == 0) {
							response_ctx->status = HTTP_200_OK;
						} else {
							LOG_ERR("Failed to encode response: %d", encode_ret);
							strcpy(json_response_buffer, "{\"error\":\"Encoding failed\"}");
							response_ctx->status = HTTP_500_INTERNAL_SERVER_ERROR;
						}

						/* Schedule network restart */
						network_restart();
					}
				} else {
					struct error_response err = { .error = "Missing IP parameters" };
					const int encode_ret = json_obj_encode_buf(error_response_descr,
									       ARRAY_SIZE(error_response_descr),
									       &err, json_response_buffer,
									       sizeof(json_response_buffer));
					if (encode_ret < 0) {
						LOG_ERR("Failed to encode error: %d", encode_ret);
						strcpy(json_response_buffer, "{\"error\":\"Internal error\"}");
					}
					response_ctx->status = HTTP_400_BAD_REQUEST;
				}
			}
		}

		response_ctx->body = (const uint8_t *)json_response_buffer;
		response_ctx->body_len = strlen(json_response_buffer);
		response_ctx->final_chunk = true;
		request_offset = 0;
	}

	return 0;
}

struct http_resource_detail_dynamic network_config_resource_detail = {
	.common = {
		.type = HTTP_RESOURCE_TYPE_DYNAMIC,
		.bitmask_of_supported_http_methods = BIT(HTTP_POST),
		.content_type = "application/json",
	},
	.cb = network_config_handler,
	.user_data = NULL,
};
