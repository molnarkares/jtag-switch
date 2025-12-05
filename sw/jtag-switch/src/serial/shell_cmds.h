/*
 * Copyright (c) 2025 JTAG Switch Project
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SHELL_CMDS_H
#define SHELL_CMDS_H

/**
 * @brief Initialize shell commands
 *
 * Registers all JTAG switch shell commands with the shell subsystem.
 * Must be called after gpio_control_init().
 *
 * @return 0 on success, negative errno on failure
 */
int shell_cmds_init(void);

#endif /* SHELL_CMDS_H */
