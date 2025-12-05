/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * Network Configuration Module
 *
 * Handles Ethernet initialization, IP configuration (static/DHCP),
 * runtime reconfiguration, and persistent storage of network settings.
 */

#ifndef NETWORK_CONFIG_H
#define NETWORK_CONFIG_H

#include <zephyr/kernel.h>
#include <stdbool.h>

/**
 * @brief Network status structure
 *
 * Contains current network state including IP configuration,
 * MAC address, link status, and DHCP mode.
 */
struct network_status {
	char ip[16];          /* IPv4 address string (e.g., "192.168.1.100") */
	char netmask[16];     /* Netmask string (e.g., "255.255.255.0") */
	char gateway[16];     /* Gateway string (e.g., "192.168.1.1") */
	char mac[18];         /* MAC address string (e.g., "00:04:9f:05:a3:7e") */
	bool link_up;         /* Ethernet link status (true = up) */
	bool dhcp_enabled;    /* DHCP mode active (true = DHCP, false = static) */
};

/**
 * @brief Network configuration structure
 *
 * Contains network configuration that can be saved/loaded from
 * non-volatile storage.
 */
struct network_config {
	bool dhcp_enabled;       /* DHCP mode enabled */
	char static_ip[16];      /* Static IP address */
	char static_netmask[16]; /* Static netmask */
	char static_gateway[16]; /* Static gateway */
};

/**
 * @brief Initialize network subsystem
 *
 * Initializes Ethernet interface, loads configuration from NVS,
 * and configures network based on saved settings or Kconfig defaults.
 *
 * @return 0 on success, negative errno on failure
 */
int network_init(void);

/**
 * @brief Get current network status
 *
 * Retrieves current network state including IP address, link status,
 * and DHCP mode.
 *
 * @param status Pointer to network_status structure to fill
 * @return 0 on success, negative errno on failure
 */
int network_get_status(struct network_status *status);

/**
 * @brief Get network configuration
 *
 * Retrieves current network configuration including saved static IP
 * settings and DHCP mode.
 *
 * @param config Pointer to network_config structure to fill
 * @return 0 on success, negative errno on failure
 */
int network_get_config(struct network_config *config);

/**
 * @brief Set static IP configuration
 *
 * Configures network to use static IP addressing. Does not apply
 * immediately - call network_restart() to apply changes.
 *
 * @param ip IPv4 address string (e.g., "192.168.1.100")
 * @param netmask Netmask string (e.g., "255.255.255.0")
 * @param gateway Gateway string (e.g., "192.168.1.1")
 * @return 0 on success, negative errno on failure
 */
int network_set_static_ip(const char *ip, const char *netmask, const char *gateway);

/**
 * @brief Enable DHCP mode
 *
 * Configures network to use DHCP for IP addressing. Does not apply
 * immediately - call network_restart() to apply changes.
 *
 * @return 0 on success, negative errno on failure
 */
int network_enable_dhcp(void);

/**
 * @brief Restart network interface
 *
 * Stops and restarts the network interface with current configuration.
 * This applies any pending configuration changes.
 *
 * @return 0 on success, negative errno on failure
 */
int network_restart(void);

/**
 * @brief Save network configuration to NVS
 *
 * Saves current network configuration to non-volatile storage.
 * Configuration will be loaded automatically on next boot.
 *
 * @return 0 on success, negative errno on failure
 */
int network_config_save(void);

/**
 * @brief Load network configuration from NVS
 *
 * Loads network configuration from non-volatile storage.
 * Called automatically during network_init().
 *
 * @return 0 on success, negative errno on failure
 */
int network_config_load(void);

#endif /* NETWORK_CONFIG_H */
