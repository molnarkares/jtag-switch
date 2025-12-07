/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * GPIO Control Module - JTAG Multiplexer Select Lines
 *
 * CRITICAL SAFETY CONSTRAINT:
 * The two JTAG select GPIO pins must NEVER be HIGH simultaneously.
 * This module enforces mutual exclusion to prevent hardware damage.
 *
 * Valid states: 00 (both low), 01, 10
 * Invalid state: 11 (both high) - PROHIBITED
 */

#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>
#include "gpio_control.h"

LOG_MODULE_REGISTER(gpio_control, LOG_LEVEL_DBG);

/* Device tree aliases */
#define JTAG_SELECT0_NODE DT_ALIAS(jtag_select0)
#define JTAG_SELECT1_NODE DT_ALIAS(jtag_select1)

/* Compile-time validation */
#if !DT_NODE_HAS_STATUS(JTAG_SELECT0_NODE, okay)
#error "jtag-select0 alias not defined or not enabled in device tree"
#endif

#if !DT_NODE_HAS_STATUS(JTAG_SELECT1_NODE, okay)
#error "jtag-select1 alias not defined or not enabled in device tree"
#endif

/* GPIO specifications from device tree */
static const struct gpio_dt_spec jtag_select0 =
	GPIO_DT_SPEC_GET(JTAG_SELECT0_NODE, gpios);
static const struct gpio_dt_spec jtag_select1 =
	GPIO_DT_SPEC_GET(JTAG_SELECT1_NODE, gpios);

/* State tracking */
static bool select0_state = false;
static bool select1_state = false;
static bool initialized = false;

/* Mutex for thread-safe access to shared state */
static K_MUTEX_DEFINE(gpio_control_mutex);

/* Scoped lock helper for automatic mutex cleanup */
static inline void mutex_unlock_cleanup(struct k_mutex **mutex_ptr)
{
	if (mutex_ptr && *mutex_ptr) {
		k_mutex_unlock(*mutex_ptr);
	}
}

#define SCOPED_LOCK(mutex) \
	__attribute__((cleanup(mutex_unlock_cleanup))) \
	struct k_mutex *_scoped_lock __unused = &mutex; \
	k_mutex_lock(_scoped_lock, K_FOREVER)

/**
 * @brief Verify GPIO pin state matches expected value
 * @param spec GPIO device tree spec
 * @param expected Expected state (0 or 1)
 * @param line_name Name for logging (e.g., "select0")
 * @return 0 if matches, -EIO if mismatch
 *
 * Note: GPIO emulation (CONFIG_GPIO_EMUL) may not support readback correctly,
 * so verification is skipped in simulation builds.
 */
static int verify_gpio_state(const struct gpio_dt_spec *spec,
                             int expected, const char *line_name)
{
#ifdef CONFIG_GPIO_EMUL
	/* Skip readback verification in simulation - gpio_emul doesn't support it */
	ARG_UNUSED(spec);
	ARG_UNUSED(expected);
	ARG_UNUSED(line_name);
	return 0;
#else
	int actual = gpio_pin_get_dt(spec);

	if (actual < 0) {
		LOG_ERR("Failed to read %s: %d", line_name, actual);
		return -EIO;
	}
	if (actual != expected) {
		LOG_ERR("GPIO %s readback mismatch: expected %d, got %d",
		        line_name, expected, actual);
		return -EIO;
	}
	return 0;
#endif
}

int gpio_control_init(void)
{
	int ret = 0;

	SCOPED_LOCK(gpio_control_mutex);  /* Auto-unlocks on return */

	if (initialized) {
		LOG_WRN("GPIO already initialized");
		return 0;
	}

	/* Check device readiness */
	if (!gpio_is_ready_dt(&jtag_select0)) {
		LOG_ERR("jtag-select0 GPIO device not ready");
		return -ENODEV;
	}

	if (!gpio_is_ready_dt(&jtag_select1)) {
		LOG_ERR("jtag-select1 GPIO device not ready");
		return -ENODEV;
	}

	/*
	 * Configure both pins as outputs, initially LOW (safe state).
	 * Both LOW (00) satisfies the mutual exclusion constraint.
	 */
	ret = gpio_pin_configure_dt(&jtag_select0, GPIO_OUTPUT_INACTIVE);
	if (ret < 0) {
		LOG_ERR("Failed to configure jtag-select0: %d", ret);
		return ret;
	}

	/* Verify select0 configured correctly */
	ret = verify_gpio_state(&jtag_select0, 0, "select0");
	if (ret < 0) {
		return ret;
	}

	ret = gpio_pin_configure_dt(&jtag_select1, GPIO_OUTPUT_INACTIVE);
	if (ret < 0) {
		LOG_ERR("Failed to configure jtag-select1: %d", ret);
		return ret;
	}

	/* Verify select1 configured correctly */
	ret = verify_gpio_state(&jtag_select1, 0, "select1");
	if (ret < 0) {
		return ret;
	}

	select0_state = false;
	select1_state = false;
	initialized = true;

	LOG_INF("GPIO control initialized:");
	LOG_INF("  jtag-select0: %s pin %d",
		jtag_select0.port->name, jtag_select0.pin);
	LOG_INF("  jtag-select1: %s pin %d",
		jtag_select1.port->name, jtag_select1.pin);

	return 0;  /* Mutex auto-unlocks here */
}

int gpio_control_set_select(uint8_t select_line, bool state)
{
	int ret = 0;
	const struct gpio_dt_spec *gpio_spec;
	const struct gpio_dt_spec *other_gpio_spec;
	bool *state_var;
	bool *other_state_var;
	uint8_t other_line;
	bool other_pin_cleared = false;
	bool original_other_state;

	SCOPED_LOCK(gpio_control_mutex);  /* Auto-unlocks on return */

	if (!initialized) {
		LOG_ERR("GPIO control not initialized");
		return -EINVAL;
	}

	switch (select_line) {
	case 0:
		gpio_spec = &jtag_select0;
		state_var = &select0_state;
		other_gpio_spec = &jtag_select1;
		other_state_var = &select1_state;
		other_line = 1;
		break;
	case 1:
		gpio_spec = &jtag_select1;
		state_var = &select1_state;
		other_gpio_spec = &jtag_select0;
		other_state_var = &select0_state;
		other_line = 0;
		break;
	default:
		LOG_ERR("Invalid select line: %d", select_line);
		return -EINVAL;
	}

	/*
	 * SAFETY: Enforce mutual exclusion constraint
	 * Both GPIO pins must NEVER be HIGH simultaneously.
	 * If setting this line HIGH while other is HIGH, clear other first.
	 */
	if (state == true && *other_state_var == true) {
		LOG_WRN("Mutual exclusion: clearing select%d before setting select%d HIGH",
		        other_line, select_line);

		original_other_state = *other_state_var;

		ret = gpio_pin_set_dt(other_gpio_spec, 0);
		if (ret < 0) {
			LOG_ERR("Failed to clear jtag-select%d: %d", other_line, ret);
			return ret;
		}

		/* Verify other pin cleared */
		ret = verify_gpio_state(other_gpio_spec, 0,
		                        select_line == 0 ? "select1" : "select0");
		if (ret < 0) {
			return ret;
		}

		*other_state_var = false;
		other_pin_cleared = true;
		LOG_DBG("jtag-select%d cleared to LOW", other_line);
	}

	/* Set the requested line to desired state */
	ret = gpio_pin_set_dt(gpio_spec, state ? 1 : 0);
	if (ret < 0) {
		LOG_ERR("Failed to set jtag-select%d: %d", select_line, ret);

		/* ROLLBACK: Restore other pin if we cleared it */
		if (other_pin_cleared) {
			int rollback_ret = gpio_pin_set_dt(other_gpio_spec,
			                                   original_other_state ? 1 : 0);
			if (rollback_ret == 0) {
				*other_state_var = original_other_state;
				LOG_WRN("Rolled back select%d to original state", other_line);
			} else {
				LOG_ERR("CRITICAL: Rollback failed for select%d: %d",
				        other_line, rollback_ret);
			}
		}
		return ret;
	}

	/* Verify target pin set correctly */
	ret = verify_gpio_state(gpio_spec, state ? 1 : 0,
	                        select_line == 0 ? "select0" : "select1");
	if (ret < 0) {
		/* ROLLBACK: Restore other pin if we cleared it */
		if (other_pin_cleared) {
			int rollback_ret = gpio_pin_set_dt(other_gpio_spec,
			                                   original_other_state ? 1 : 0);
			if (rollback_ret == 0) {
				*other_state_var = original_other_state;
				LOG_WRN("Rolled back select%d after verification failure", other_line);
			}
		}
		return ret;
	}

	*state_var = state;
	LOG_DBG("jtag-select%d set to %s (connector %d)",
	        select_line, state ? "HIGH" : "LOW", state ? 1 : 0);

	return 0;  /* Mutex auto-unlocks here */
}

int gpio_control_get_select(uint8_t select_line, bool *state)
{
	SCOPED_LOCK(gpio_control_mutex);  /* Auto-unlocks on return */

	if (!initialized || state == NULL) {
		return -EINVAL;
	}

	switch (select_line) {
	case 0:
		*state = select0_state;
		break;
	case 1:
		*state = select1_state;
		break;
	default:
		return -EINVAL;
	}

	return 0;
}

int gpio_control_toggle_select(uint8_t select_line)
{
	bool current_state;
	int ret;

	ret = gpio_control_get_select(select_line, &current_state);
	if (ret < 0) {
		return ret;
	}

	return gpio_control_set_select(select_line, !current_state);
}
