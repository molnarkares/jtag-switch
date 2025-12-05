/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * Network Configuration Module Implementation
 */

#include <zephyr/kernel.h>
#include <zephyr/net/net_if.h>
#include <zephyr/net/net_core.h>
#include <zephyr/net/net_context.h>
#include <zephyr/net/net_mgmt.h>
#include <zephyr/net/ethernet.h>
#include <zephyr/net/dhcpv4.h>
#include <zephyr/settings/settings.h>
#include <zephyr/logging/log.h>
#include <string.h>
#include <stdlib.h>

#include "network_config.h"

LOG_MODULE_REGISTER(network_config, LOG_LEVEL_INF);

/* NVS Settings keys */
#define SETTINGS_NAME "network"
#define SETTINGS_KEY_DHCP "network/dhcp"
#define SETTINGS_KEY_IP "network/ip"
#define SETTINGS_KEY_NETMASK "network/netmask"
#define SETTINGS_KEY_GATEWAY "network/gateway"

/* Network configuration state */
static struct network_config current_config = {
	.dhcp_enabled = false,
	.static_ip = "",
	.static_netmask = "",
	.static_gateway = ""
};

static struct net_if *iface = NULL;
static bool network_initialized = false;

/* Network management event handler */
static struct net_mgmt_event_callback net_mgmt_cb;

/**
 * @brief Network management event handler
 */
static void net_mgmt_event_handler(struct net_mgmt_event_callback *cb,
				   uint64_t mgmt_event, struct net_if *iface)
{
	if (mgmt_event == NET_EVENT_IPV4_ADDR_ADD) {
		LOG_INF("IPv4 address added");
	} else if (mgmt_event == NET_EVENT_IPV4_DHCP_BOUND) {
		LOG_INF("DHCP bound");
	} else if (mgmt_event == NET_EVENT_IF_UP) {
		LOG_INF("Network interface up");
	} else if (mgmt_event == NET_EVENT_IF_DOWN) {
		LOG_INF("Network interface down");
	}
}

/**
 * @brief Validate IPv4 address format
 */
static bool is_valid_ipv4(const char *ip)
{
	int a, b, c, d;
	if (sscanf(ip, "%d.%d.%d.%d", &a, &b, &c, &d) != 4) {
		return false;
	}
	if (a < 0 || a > 255 || b < 0 || b > 255 ||
	    c < 0 || c > 255 || d < 0 || d > 255) {
		return false;
	}
	return true;
}

/**
 * @brief Configure static IP address
 */
static int configure_static_ip(struct net_if *iface,
			       const char *ip,
			       const char *netmask,
			       const char *gateway)
{
	struct in_addr addr, mask, gw;
	struct net_if_addr *ifaddr;
	struct net_if_ipv4 *ipv4;

	/* Convert IP address string to binary */
	if (net_addr_pton(AF_INET, ip, &addr) < 0) {
		LOG_ERR("Invalid IP address: %s", ip);
		return -EINVAL;
	}

	/* Convert netmask string to binary */
	if (net_addr_pton(AF_INET, netmask, &mask) < 0) {
		LOG_ERR("Invalid netmask: %s", netmask);
		return -EINVAL;
	}

	/* Convert gateway string to binary */
	if (net_addr_pton(AF_INET, gateway, &gw) < 0) {
		LOG_ERR("Invalid gateway: %s", gateway);
		return -EINVAL;
	}

	/* Remove any existing IPv4 addresses first */
	ipv4 = iface->config.ip.ipv4;
	if (ipv4) {
		for (int i = 0; i < NET_IF_MAX_IPV4_ADDR; i++) {
			if (ipv4->unicast[i].ipv4.is_used) {
				LOG_INF("Removing existing IPv4 address from slot %d", i);
				net_if_ipv4_addr_rm(iface, &ipv4->unicast[i].ipv4.address.in_addr);
			}
		}
	}

	/* Add IPv4 address to interface */
	ifaddr = net_if_ipv4_addr_add(iface, &addr, NET_ADDR_MANUAL, 0);
	if (!ifaddr) {
		LOG_ERR("Failed to add IPv4 address");
		return -ENOMEM;
	}

	/* Set netmask for this address */
	if (!net_if_ipv4_set_netmask_by_addr(iface, &addr, &mask)) {
		LOG_WRN("Failed to set netmask, continuing anyway");
	}

	/* Set gateway */
	net_if_ipv4_set_gw(iface, &gw);

	LOG_INF("Static IP configured:");
	LOG_INF("  IP: %s", ip);
	LOG_INF("  Netmask: %s", netmask);
	LOG_INF("  Gateway: %s", gateway);

	return 0;
}

/**
 * @brief Start DHCP client
 */
static int start_dhcp(struct net_if *iface)
{
#ifdef CONFIG_NET_DHCPV4
	LOG_INF("Starting DHCP client...");
	net_dhcpv4_start(iface);
	return 0;
#else
	LOG_ERR("DHCP not enabled in Kconfig");
	return -ENOTSUP;
#endif
}

/**
 * @brief Stop DHCP client
 */
static void stop_dhcp(struct net_if *iface)
{
#ifdef CONFIG_NET_DHCPV4
	net_dhcpv4_stop(iface);
	LOG_INF("DHCP client stopped");
#endif
}

/**
 * @brief Settings load callback
 */
static int network_settings_load(const char *key, size_t len,
				 settings_read_cb read_cb, void *cb_arg)
{
	int rc;

	if (strcmp(key, "dhcp") == 0) {
		rc = read_cb(cb_arg, &current_config.dhcp_enabled,
			     sizeof(current_config.dhcp_enabled));
		if (rc >= 0) {
			LOG_INF("Loaded DHCP setting: %d", current_config.dhcp_enabled);
			return 0;
		}
		return rc;
	}

	if (strcmp(key, "ip") == 0) {
		rc = read_cb(cb_arg, current_config.static_ip,
			     sizeof(current_config.static_ip));
		if (rc >= 0) {
			LOG_INF("Loaded IP: %s", current_config.static_ip);
			return 0;
		}
		return rc;
	}

	if (strcmp(key, "netmask") == 0) {
		rc = read_cb(cb_arg, current_config.static_netmask,
			     sizeof(current_config.static_netmask));
		if (rc >= 0) {
			LOG_INF("Loaded netmask: %s", current_config.static_netmask);
			return 0;
		}
		return rc;
	}

	if (strcmp(key, "gateway") == 0) {
		rc = read_cb(cb_arg, current_config.static_gateway,
			     sizeof(current_config.static_gateway));
		if (rc >= 0) {
			LOG_INF("Loaded gateway: %s", current_config.static_gateway);
			return 0;
		}
		return rc;
	}

	return -ENOENT;
}

SETTINGS_STATIC_HANDLER_DEFINE(network, SETTINGS_NAME, NULL,
			       network_settings_load, NULL, NULL);

int network_config_load(void)
{
	int ret;

#ifdef CONFIG_SETTINGS
	/* Initialize settings subsystem */
	ret = settings_subsys_init();
	if (ret < 0) {
		LOG_ERR("Failed to initialize settings subsystem: %d", ret);
		return ret;
	}

	LOG_INF("Settings subsystem initialized");

	ret = settings_load_subtree(SETTINGS_NAME);
	if (ret < 0) {
		LOG_WRN("Failed to load network settings: %d", ret);
		/* Not a fatal error - use defaults */
		return 0;
	}

	LOG_INF("Network configuration loaded from NVS");
#else
	LOG_WRN("Settings subsystem not enabled");
	ret = 0;
#endif

	return ret;
}

int network_config_save(void)
{
	int ret;

#ifdef CONFIG_SETTINGS
	ret = settings_save_one(SETTINGS_KEY_DHCP,
				&current_config.dhcp_enabled,
				sizeof(current_config.dhcp_enabled));
	if (ret < 0) {
		LOG_ERR("Failed to save DHCP setting: %d", ret);
		return ret;
	}

	ret = settings_save_one(SETTINGS_KEY_IP,
				current_config.static_ip,
				strlen(current_config.static_ip) + 1);
	if (ret < 0) {
		LOG_ERR("Failed to save IP: %d", ret);
		return ret;
	}

	ret = settings_save_one(SETTINGS_KEY_NETMASK,
				current_config.static_netmask,
				strlen(current_config.static_netmask) + 1);
	if (ret < 0) {
		LOG_ERR("Failed to save netmask: %d", ret);
		return ret;
	}

	ret = settings_save_one(SETTINGS_KEY_GATEWAY,
				current_config.static_gateway,
				strlen(current_config.static_gateway) + 1);
	if (ret < 0) {
		LOG_ERR("Failed to save gateway: %d", ret);
		return ret;
	}

	LOG_INF("Network configuration saved to NVS");
#else
	LOG_WRN("Settings subsystem not enabled");
	ret = -ENOTSUP;
#endif

	return ret;
}

int network_init(void)
{
	int ret;

	LOG_INF("Initializing network subsystem...");

	/* Get default network interface (Ethernet) */
	iface = net_if_get_default();
	if (!iface) {
		LOG_ERR("No default network interface found");
		return -ENODEV;
	}

	LOG_INF("Network interface: %s", net_if_get_device(iface)->name);

	/* Register network management event handler */
	net_mgmt_init_event_callback(&net_mgmt_cb, net_mgmt_event_handler,
				     NET_EVENT_IPV4_ADDR_ADD |
				     NET_EVENT_IPV4_DHCP_BOUND |
				     NET_EVENT_IF_UP |
				     NET_EVENT_IF_DOWN);
	net_mgmt_add_event_callback(&net_mgmt_cb);

	/* Load configuration from NVS */
	ret = network_config_load();
	if (ret < 0) {
		LOG_WRN("Failed to load network config, using defaults");
	}

	/* Apply configuration based on loaded settings or Kconfig */
	bool use_dhcp = false;

#ifdef CONFIG_NET_DHCPV4
	/* Use saved DHCP preference if available */
	if (current_config.dhcp_enabled) {
		use_dhcp = true;
	} else if (strlen(current_config.static_ip) == 0) {
		/* No saved config - prefer static IP from Kconfig if available */
		#ifdef CONFIG_NET_CONFIG_MY_IPV4_ADDR
			use_dhcp = false;  /* Use Kconfig static IP */
		#else
			use_dhcp = true;   /* No static IP in Kconfig, use DHCP */
		#endif
	}
#endif

	if (use_dhcp) {
		current_config.dhcp_enabled = true;
		ret = start_dhcp(iface);
		if (ret < 0) {
			LOG_ERR("Failed to start DHCP: %d", ret);
			return ret;
		}
	} else {
		/* Use static IP from NVS or Kconfig */
		const char *ip = current_config.static_ip;
		const char *netmask = current_config.static_netmask;
		const char *gateway = current_config.static_gateway;

		/* If no saved config, use Kconfig defaults */
		if (strlen(ip) == 0) {
#ifdef CONFIG_NET_CONFIG_MY_IPV4_ADDR
			ip = CONFIG_NET_CONFIG_MY_IPV4_ADDR;
			netmask = CONFIG_NET_CONFIG_MY_IPV4_NETMASK;
			gateway = CONFIG_NET_CONFIG_MY_IPV4_GW;

			/* Save defaults to config */
			strncpy(current_config.static_ip, ip, sizeof(current_config.static_ip) - 1);
			strncpy(current_config.static_netmask, netmask, sizeof(current_config.static_netmask) - 1);
			strncpy(current_config.static_gateway, gateway, sizeof(current_config.static_gateway) - 1);
#else
			LOG_ERR("No static IP configuration available");
			return -EINVAL;
#endif
		}

		current_config.dhcp_enabled = false;
		ret = configure_static_ip(iface, ip, netmask, gateway);
		if (ret < 0) {
			LOG_ERR("Failed to configure static IP: %d", ret);
			return ret;
		}
	}

	/* Bring interface up */
	net_if_up(iface);

	network_initialized = true;
	LOG_INF("Network subsystem initialized successfully");

	return 0;
}

int network_get_status(struct network_status *status)
{
	struct net_if_ipv4 *ipv4;
	const struct net_linkaddr *link_addr;

	if (!status || !network_initialized) {
		return -EINVAL;
	}

	memset(status, 0, sizeof(*status));

	/* Get IPv4 configuration */
	ipv4 = iface->config.ip.ipv4;
	if (ipv4) {
		/* Get first unicast address */
		for (int i = 0; i < NET_IF_MAX_IPV4_ADDR; i++) {
			if (ipv4->unicast[i].ipv4.is_used) {
				net_addr_ntop(AF_INET, &ipv4->unicast[i].ipv4.address.in_addr,
					      status->ip, sizeof(status->ip));
				break;
			}
		}

		/* Get gateway */
		net_addr_ntop(AF_INET, &ipv4->gw,
			      status->gateway, sizeof(status->gateway));

		/* For netmask, we'll use a default based on typical subnet */
		strcpy(status->netmask, "255.255.255.0");
	}

	/* Get MAC address */
	link_addr = net_if_get_link_addr(iface);
	if (link_addr && link_addr->len == 6) {
		snprintf(status->mac, sizeof(status->mac),
			 "%02x:%02x:%02x:%02x:%02x:%02x",
			 link_addr->addr[0], link_addr->addr[1], link_addr->addr[2],
			 link_addr->addr[3], link_addr->addr[4], link_addr->addr[5]);
	}

	/* Get link status */
	status->link_up = net_if_is_up(iface);

	/* Get DHCP status */
	status->dhcp_enabled = current_config.dhcp_enabled;

	return 0;
}

int network_get_config(struct network_config *config)
{
	if (!config || !network_initialized) {
		return -EINVAL;
	}

	memcpy(config, &current_config, sizeof(*config));
	return 0;
}

int network_set_static_ip(const char *ip, const char *netmask, const char *gateway)
{
	if (!ip || !netmask || !gateway || !network_initialized) {
		return -EINVAL;
	}

	/* Validate IP addresses */
	if (!is_valid_ipv4(ip)) {
		LOG_ERR("Invalid IP address: %s", ip);
		return -EINVAL;
	}

	if (!is_valid_ipv4(netmask)) {
		LOG_ERR("Invalid netmask: %s", netmask);
		return -EINVAL;
	}

	if (!is_valid_ipv4(gateway)) {
		LOG_ERR("Invalid gateway: %s", gateway);
		return -EINVAL;
	}

	/* Update configuration */
	strncpy(current_config.static_ip, ip, sizeof(current_config.static_ip) - 1);
	strncpy(current_config.static_netmask, netmask, sizeof(current_config.static_netmask) - 1);
	strncpy(current_config.static_gateway, gateway, sizeof(current_config.static_gateway) - 1);
	current_config.dhcp_enabled = false;

	LOG_INF("Static IP configuration updated (not applied yet):");
	LOG_INF("  IP: %s", ip);
	LOG_INF("  Netmask: %s", netmask);
	LOG_INF("  Gateway: %s", gateway);
	LOG_INF("Call network_restart() to apply changes");

	return 0;
}

int network_enable_dhcp(void)
{
	if (!network_initialized) {
		return -EINVAL;
	}

#ifndef CONFIG_NET_DHCPV4
	LOG_ERR("DHCP not enabled in Kconfig");
	return -ENOTSUP;
#endif

	current_config.dhcp_enabled = true;

	LOG_INF("DHCP mode enabled (not applied yet)");
	LOG_INF("Call network_restart() to apply changes");

	return 0;
}

int network_restart(void)
{
	int ret;

	if (!network_initialized) {
		return -EINVAL;
	}

	LOG_INF("Restarting network interface...");

	/* Bring interface down */
	net_if_down(iface);

	/* Stop DHCP if running */
	stop_dhcp(iface);

	/* Clear existing IP addresses */
	struct net_if_ipv4 *ipv4 = iface->config.ip.ipv4;
	if (ipv4) {
		for (int i = 0; i < NET_IF_MAX_IPV4_ADDR; i++) {
			if (ipv4->unicast[i].ipv4.is_used) {
				net_if_ipv4_addr_rm(iface, &ipv4->unicast[i].ipv4.address.in_addr);
			}
		}
	}

	/* Apply new configuration */
	if (current_config.dhcp_enabled) {
		ret = start_dhcp(iface);
		if (ret < 0) {
			LOG_ERR("Failed to start DHCP: %d", ret);
			return ret;
		}
	} else {
		ret = configure_static_ip(iface,
					 current_config.static_ip,
					 current_config.static_netmask,
					 current_config.static_gateway);
		if (ret < 0) {
			LOG_ERR("Failed to configure static IP: %d", ret);
			return ret;
		}
	}

	/* Bring interface up */
	net_if_up(iface);

	LOG_INF("Network interface restarted successfully");

	return 0;
}
