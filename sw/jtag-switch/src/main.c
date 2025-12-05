/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>
#include "gpio/gpio_control.h"

#if defined(CONFIG_SHELL)
#include "serial/shell_cmds.h"
#endif

#if defined(CONFIG_NETWORKING)
#include "net/network_config.h"
#include "net/http_api.h"
#endif


LOG_MODULE_REGISTER(jtag_switch, LOG_LEVEL_INF);

int main(void)
{
	LOG_INF("JTAG Switch Application Starting");
	LOG_INF("Board: %s", CONFIG_BOARD);

	/* Initialize GPIO control */
	int ret = gpio_control_init();
	if (ret < 0) {
		LOG_ERR("Failed to initialize GPIO control: %d", ret);
		return ret;
	}

	LOG_INF("GPIO control initialized successfully");

	/* Set default configuration (both to connector 0) */
	ret = gpio_control_set_select(0, false);
	if (ret < 0) {
		LOG_ERR("Failed to set jtag-select0: %d", ret);
	}

	ret = gpio_control_set_select(1, false);
	if (ret < 0) {
		LOG_ERR("Failed to set jtag-select1: %d", ret);
	}

	/* USB device is automatically initialized when CONFIG_CDC_ACM_SERIAL_INITIALIZE_AT_BOOT=y */

#if defined(CONFIG_NETWORKING)
	/* Initialize network subsystem */
	ret = network_init();
	if (ret < 0) {
		LOG_ERR("Failed to initialize network: %d", ret);
		return ret;
	}

	LOG_INF("Network initialized successfully");

	/* Initialize HTTP API server */
	ret = http_api_init();
	if (ret < 0) {
		LOG_ERR("Failed to initialize HTTP API: %d", ret);
		return ret;
	}

	LOG_INF("HTTP API initialized successfully");

	/* Display network status */
	struct network_status net_status;
	ret = network_get_status(&net_status);
	if (ret == 0) {
		LOG_INF("Network Status:");
		LOG_INF("  Mode: %s", net_status.dhcp_enabled ? "DHCP" : "Static IP");
		LOG_INF("  IP Address: %s", net_status.ip);
		LOG_INF("  MAC Address: %s", net_status.mac);
		LOG_INF("Web UI available at: http://%s/", net_status.ip);
		LOG_INF("REST API available at: http://%s/api/", net_status.ip);
	}
#endif

#if defined(CONFIG_SHELL)
	/* Initialize shell commands */
	ret = shell_cmds_init();
	if (ret < 0) {
		LOG_ERR("Failed to initialize shell commands: %d", ret);
		return ret;
	}

	LOG_INF("Shell commands initialized");
#endif

	LOG_INF("JTAG Switch ready - Default: Connector 0 selected");
#if defined(CONFIG_SHELL)
	LOG_INF("Type 'jtag help' or 'net help' for available commands");
#endif

	/* Main loop - application is idle, shell/API handles user interaction */
	while (1) {
		k_sleep(K_SECONDS(10));
	}

	return 0;
}
