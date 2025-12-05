/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 */

#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>
#include <stdlib.h>
#include "../gpio/gpio_control.h"
#include "shell_cmds.h"

#ifdef CONFIG_NETWORKING
#include "../net/network_config.h"
#endif

/* Shell command: jtag select0 <0|1> */
static int cmd_jtag_select0(const struct shell *sh, size_t argc, char **argv)
{
	int ret;
	bool state;

	if (argc != 2) {
		shell_error(sh, "Usage: jtag select0 <0|1>");
		return -EINVAL;
	}

	int value = atoi(argv[1]);
	if (value != 0 && value != 1) {
		shell_error(sh, "Invalid value. Use 0 or 1");
		return -EINVAL;
	}

	state = (value == 1);
	ret = gpio_control_set_select(0, state);
	if (ret < 0) {
		shell_error(sh, "Failed to set select0: %d", ret);
		return ret;
	}

	shell_print(sh, "select0 set to %d (connector %d)", value, value);
	return 0;
}

/* Shell command: jtag select1 <0|1> */
static int cmd_jtag_select1(const struct shell *sh, size_t argc, char **argv)
{
	int ret;
	bool state;

	if (argc != 2) {
		shell_error(sh, "Usage: jtag select1 <0|1>");
		return -EINVAL;
	}

	int value = atoi(argv[1]);
	if (value != 0 && value != 1) {
		shell_error(sh, "Invalid value. Use 0 or 1");
		return -EINVAL;
	}

	state = (value == 1);
	ret = gpio_control_set_select(1, state);
	if (ret < 0) {
		shell_error(sh, "Failed to set select1: %d", ret);
		return ret;
	}

	shell_print(sh, "select1 set to %d (connector %d)", value, value);
	return 0;
}

/* Shell command: jtag toggle0 */
static int cmd_jtag_toggle0(const struct shell *sh, size_t argc, char **argv)
{
	int ret;
	bool state;

	ret = gpio_control_toggle_select(0);
	if (ret < 0) {
		shell_error(sh, "Failed to toggle select0: %d", ret);
		return ret;
	}

	ret = gpio_control_get_select(0, &state);
	if (ret < 0) {
		shell_error(sh, "Failed to get select0 state: %d", ret);
		return ret;
	}

	shell_print(sh, "select0 toggled to %d (connector %d)", state ? 1 : 0, state ? 1 : 0);
	return 0;
}

/* Shell command: jtag toggle1 */
static int cmd_jtag_toggle1(const struct shell *sh, size_t argc, char **argv)
{
	int ret;
	bool state;

	ret = gpio_control_toggle_select(1);
	if (ret < 0) {
		shell_error(sh, "Failed to toggle select1: %d", ret);
		return ret;
	}

	ret = gpio_control_get_select(1, &state);
	if (ret < 0) {
		shell_error(sh, "Failed to get select1 state: %d", ret);
		return ret;
	}

	shell_print(sh, "select1 toggled to %d (connector %d)", state ? 1 : 0, state ? 1 : 0);
	return 0;
}

/* Shell command: jtag status */
static int cmd_jtag_status(const struct shell *sh, size_t argc, char **argv)
{
	int ret;
	bool state0, state1;

	ret = gpio_control_get_select(0, &state0);
	if (ret < 0) {
		shell_error(sh, "Failed to get select0 state: %d", ret);
		return ret;
	}

	ret = gpio_control_get_select(1, &state1);
	if (ret < 0) {
		shell_error(sh, "Failed to get select1 state: %d", ret);
		return ret;
	}

	shell_print(sh, "JTAG Switch Status:");
	shell_print(sh, "  select0: %d (connector %d)", state0 ? 1 : 0, state0 ? 1 : 0);
	shell_print(sh, "  select1: %d (connector %d)", state1 ? 1 : 0, state1 ? 1 : 0);
	shell_print(sh, "");
	shell_print(sh, "Board: %s", CONFIG_BOARD);

	return 0;
}

/* Register shell commands */
SHELL_STATIC_SUBCMD_SET_CREATE(sub_jtag,
	SHELL_CMD(select0, NULL, "Set select0 line (0|1)", cmd_jtag_select0),
	SHELL_CMD(select1, NULL, "Set select1 line (0|1)", cmd_jtag_select1),
	SHELL_CMD(toggle0, NULL, "Toggle select0 line", cmd_jtag_toggle0),
	SHELL_CMD(toggle1, NULL, "Toggle select1 line", cmd_jtag_toggle1),
	SHELL_CMD(status, NULL, "Show JTAG switch status", cmd_jtag_status),
	SHELL_SUBCMD_SET_END
);

SHELL_CMD_REGISTER(jtag, &sub_jtag, "JTAG switch control commands", NULL);

#ifdef CONFIG_NETWORKING
/* ========================================================================
 * Network Configuration Shell Commands
 * ======================================================================== */

/* Shell command: net status */
static int cmd_net_status(const struct shell *sh, size_t argc, char **argv)
{
	struct network_status status;
	int ret;

	ret = network_get_status(&status);
	if (ret < 0) {
		shell_error(sh, "Failed to get network status: %d", ret);
		return ret;
	}

	shell_print(sh, "Network Status:");
	shell_print(sh, "  Mode: %s", status.dhcp_enabled ? "DHCP" : "Static IP");
	shell_print(sh, "  IP Address: %s", status.ip);
	shell_print(sh, "  Netmask: %s", status.netmask);
	shell_print(sh, "  Gateway: %s", status.gateway);
	shell_print(sh, "  MAC Address: %s", status.mac);
	shell_print(sh, "  Link: %s", status.link_up ? "Up" : "Down");
	shell_print(sh, "  Uptime: %lld seconds", k_uptime_get() / 1000);

	return 0;
}

/* Shell command: net config */
static int cmd_net_config(const struct shell *sh, size_t argc, char **argv)
{
	struct network_config config;
	int ret;

	ret = network_get_config(&config);
	if (ret < 0) {
		shell_error(sh, "Failed to get network config: %d", ret);
		return ret;
	}

	shell_print(sh, "Network Configuration:");
	shell_print(sh, "  Mode: %s", config.dhcp_enabled ? "dhcp" : "static");
	if (!config.dhcp_enabled) {
		shell_print(sh, "  Static IP: %s", config.static_ip);
		shell_print(sh, "  Static Netmask: %s", config.static_netmask);
		shell_print(sh, "  Static Gateway: %s", config.static_gateway);
	}

	return 0;
}

/* Shell command: net set static <ip> <netmask> <gateway> */
static int cmd_net_set_static(const struct shell *sh, size_t argc, char **argv)
{
	int ret;

	if (argc != 4) {
		shell_error(sh, "Usage: net set static <ip> <netmask> <gateway>");
		return -EINVAL;
	}

	const char *ip = argv[1];
	const char *netmask = argv[2];
	const char *gateway = argv[3];

	shell_print(sh, "Setting static IP configuration...");
	shell_print(sh, "  IP Address: %s", ip);
	shell_print(sh, "  Netmask: %s", netmask);
	shell_print(sh, "  Gateway: %s", gateway);

	ret = network_set_static_ip(ip, netmask, gateway);
	if (ret < 0) {
		shell_error(sh, "Failed to set static IP: %d", ret);
		return ret;
	}

	shell_print(sh, "Static IP configuration set successfully.");
	shell_print(sh, "Use 'net save' to persist configuration.");
	shell_print(sh, "Use 'net restart' to apply changes.");

	return 0;
}

/* Shell command: net set dhcp */
static int cmd_net_set_dhcp(const struct shell *sh, size_t argc, char **argv)
{
	int ret;

	shell_print(sh, "Enabling DHCP mode...");

	ret = network_enable_dhcp();
	if (ret < 0) {
		shell_error(sh, "Failed to enable DHCP: %d", ret);
		return ret;
	}

	shell_print(sh, "DHCP mode enabled successfully.");
	shell_print(sh, "Use 'net save' to persist configuration.");
	shell_print(sh, "Use 'net restart' to apply changes.");

	return 0;
}

/* Shell command: net restart */
static int cmd_net_restart(const struct shell *sh, size_t argc, char **argv)
{
	int ret;

	shell_print(sh, "Restarting network interface...");

	ret = network_restart();
	if (ret < 0) {
		shell_error(sh, "Failed to restart network: %d", ret);
		return ret;
	}

	/* Give network time to come up */
	k_sleep(K_SECONDS(2));

	/* Show new status */
	struct network_status status;
	ret = network_get_status(&status);
	if (ret == 0) {
		shell_print(sh, "Network restarted successfully.");
		shell_print(sh, "New IP: %s", status.ip);
	}

	return 0;
}

/* Shell command: net save */
static int cmd_net_save(const struct shell *sh, size_t argc, char **argv)
{
	int ret;

	shell_print(sh, "Saving network configuration to non-volatile storage...");

	ret = network_config_save();
	if (ret < 0) {
		shell_error(sh, "Failed to save configuration: %d", ret);
		return ret;
	}

	shell_print(sh, "Configuration saved successfully.");

	return 0;
}

/* Network set subcommands */
SHELL_STATIC_SUBCMD_SET_CREATE(sub_net_set,
	SHELL_CMD_ARG(static, NULL, "Set static IP <ip> <netmask> <gateway>",
		      cmd_net_set_static, 4, 0),
	SHELL_CMD(dhcp, NULL, "Enable DHCP", cmd_net_set_dhcp),
	SHELL_SUBCMD_SET_END
);

/* Network commands */
SHELL_STATIC_SUBCMD_SET_CREATE(sub_net,
	SHELL_CMD(status, NULL, "Show network status", cmd_net_status),
	SHELL_CMD(config, NULL, "Show network configuration", cmd_net_config),
	SHELL_CMD(set, &sub_net_set, "Set network parameters", NULL),
	SHELL_CMD(restart, NULL, "Restart network interface", cmd_net_restart),
	SHELL_CMD(save, NULL, "Save configuration to flash", cmd_net_save),
	SHELL_SUBCMD_SET_END
);

SHELL_CMD_REGISTER(net, &sub_net, "Network configuration commands", NULL);

#endif /* CONFIG_NETWORKING */

int shell_cmds_init(void)
{
	/* Commands are registered automatically via SHELL_CMD_REGISTER */
	return 0;
}
