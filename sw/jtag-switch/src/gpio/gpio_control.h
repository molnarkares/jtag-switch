/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef GPIO_CONTROL_H
#define GPIO_CONTROL_H

#include <zephyr/kernel.h>
#include <stdbool.h>

/**
 * @brief Initialize GPIO control subsystem
 *
 * Initializes both JTAG select GPIO outputs from device tree configuration.
 * Must be called before any other gpio_control functions.
 *
 * @return 0 on success, negative errno on failure
 */
int gpio_control_init(void);

/**
 * @brief Set JTAG select line state with mutual exclusion enforcement
 *
 * Controls one of the two JTAG connector select lines.
 * Each line independently selects between connector 0 (low) and connector 1 (high).
 *
 * SAFETY CONSTRAINT: Both GPIO pins must NEVER be HIGH simultaneously.
 * Acceptable states:
 *   - Both LOW (00)
 *   - Select0 HIGH, Select1 LOW (10)
 *   - Select0 LOW, Select1 HIGH (01)
 * Prohibited state:
 *   - Both HIGH (11) - HARDWARE SAFETY VIOLATION
 *
 * When setting a line HIGH while the other is already HIGH, this function will
 * automatically clear the other line first before setting the requested line HIGH.
 * A warning will be logged when this occurs.
 *
 * @param select_line Select line number (0 or 1)
 * @param state false = connector 0 (LOW), true = connector 1 (HIGH)
 * @return 0 on success, negative errno on failure
 */
int gpio_control_set_select(uint8_t select_line, bool state);

/**
 * @brief Get current JTAG select line state
 *
 * Returns the last set state of the select line (not read from hardware).
 *
 * @param select_line Select line number (0 or 1)
 * @param state Pointer to store current state (false = connector 0, true = connector 1)
 * @return 0 on success, negative errno on failure
 */
int gpio_control_get_select(uint8_t select_line, bool *state);

/**
 * @brief Toggle JTAG select line
 *
 * Toggles the specified select line between connector 0 and connector 1.
 *
 * @param select_line Select line number (0 or 1)
 * @return 0 on success, negative errno on failure
 */
int gpio_control_toggle_select(uint8_t select_line);

#endif /* GPIO_CONTROL_H */
