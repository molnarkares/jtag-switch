# JTAG Switch Application

A Zephyr RTOS application for controlling JTAG connector multiplexing using two independent GPIO outputs.

## Use Case

The JTAG Switch solves a common challenge in automated hardware testing: efficiently sharing expensive or limited-availability JTAG debuggers across multiple test benches. In CI/CD pipelines running hardware regression tests, purchasing dedicated debuggers for each test bench can be cost-prohibitive, especially when debuggers are scarce or expensive. This switch enables a single JTAG debugger to be dynamically routed between two independent hardware test benches, maximizing hardware utilization while maintaining testing throughput. The programmable switching is controlled via USB serial or network API, making it ideal for integration into automated test frameworks.

## Overview

This application controls two GPIO outputs that independently select between JTAG connectors on an Arduino-compatible hardware interface. The software is designed to run on any microcontroller evaluation board (EVB) with either USB or Ethernet connectivity. The hardware interface uses standard Arduino pinout, allowing direct connection to any EVB with Arduino-compatible headers.

## Features

- **Universal EVB Support**: Runs on any microcontroller board supported by Zephyr RTOS
- **Arduino-Compatible Interface**: Hardware connects directly to Arduino-compatible headers
- **Dual Control Interfaces**: USB serial shell and Ethernet REST API with web UI
- **Independent GPIO Control**: Two select lines (jtag-select0, jtag-select1) for connector switching
- **Device Tree Configuration**: Easy board porting via device tree overlays

## Supported Boards

The application supports any Zephyr-compatible microcontroller EVB. Pre-configured device tree overlays are provided for common development boards:

| Board           | Select0 Pin | Select1 Pin | Notes                                   |
|-----------------|-------------|-------------|-----------------------------------------|
| FRDM-K64F       | PTD2        | PTD0        | Primary development board with Ethernet |
| Nucleo F439ZI   | PA7         | PD14        | STM32F439ZI with Ethernet               |

**Adding New Boards**: Any Zephyr-supported board can be used by creating a simple device tree overlay that maps two GPIO pins. See "Adding Support for New Boards" section below.

## Building

Ensure your Zephyr environment is set up:

```bash
cd /home/kares/working/jtag-switch/sw
source .venv/bin/activate
source zephyr/zephyr-env.sh
```

### Build for FRDM-K64F

```bash
west build -b frdm_k64f jtag-switch
```

### Build for Nucleo F439ZI

```bash
west build -b nucleo_f439zi jtag-switch
```

## Flashing

```bash
west flash
```

## Serial Console

Connect a serial terminal at **115200 baud** to view logs:

```bash
# Linux/macOS
screen /dev/ttyACM0 115200

# Or using minicom
minicom -D /dev/ttyACM0 -b 115200
```

### Expected Output

```
*** Booting Zephyr OS build v4.3.99 ***
[00:00:00.001,000] <inf> jtag_switch: JTAG Switch Application Starting
[00:00:00.001,000] <inf> jtag_switch: Board: frdm_k64f
[00:00:00.002,000] <inf> gpio_control: GPIO control initialized:
[00:00:00.002,000] <inf> gpio_control:   jtag-select0: GPIOD pin 2
[00:00:00.002,000] <inf> gpio_control:   jtag-select1: GPIOD pin 0
[00:00:00.003,000] <inf> jtag_switch: GPIO control initialized successfully
[00:00:00.003,000] <inf> jtag_switch: JTAG Switch ready - Default: Connector 0 selected
```

## GPIO Control

The application initializes both select lines to LOW (connector 0) on startup.

### Select Line States

- **LOW (false)**: Connector 0 selected
- **HIGH (true)**: Connector 1 selected

## API Reference

See `src/gpio_control.h` for the complete API:

- `gpio_control_init()` - Initialize GPIO subsystem
- `gpio_control_set_select(line, state)` - Set select line state
- `gpio_control_get_select(line, &state)` - Query current state
- `gpio_control_toggle_select(line)` - Toggle select line

## Adding Support for New Boards

1. Create a new overlay file: `boards/<board_name>.overlay`
2. Define GPIO aliases and pin mappings:

```dts
/ {
    aliases {
        jtag-select0 = &jtag_select0_gpio;
        jtag-select1 = &jtag_select1_gpio;
    };

    jtag_select_gpios {
        compatible = "gpio-leds";

        jtag_select0_gpio: jtag_select_0 {
            gpios = <&gpio_port PIN_NUMBER GPIO_ACTIVE_HIGH>;
            label = "JTAG Select 0";
        };

        jtag_select1_gpio: jtag_select_1 {
            gpios = <&gpio_port PIN_NUMBER GPIO_ACTIVE_HIGH>;
            label = "JTAG Select 1";
        };
    };
};
```

1. Build with: `west build -b <board_name> jtag-switch`

## Control Interfaces

### USB Serial Shell

Interactive shell commands over USB CDC ACM (115200 baud):
- `jtag select0 <0|1>` - Control select line 0
- `jtag select1 <0|1>` - Control select line 1
- `jtag status` - Display current configuration
- `jtag toggle0/toggle1` - Toggle select lines
- `net status/config/set/save` - Network configuration

### Ethernet REST API

HTTP server with JSON API endpoints (boards with Ethernet):
- `GET /api/status` - Current GPIO state, network info, uptime
- `GET /api/health` - Health check
- `POST /api/select?line=<0|1>&connector=<0|1>` - Set JTAG select line
- `POST /api/toggle?line=<0|1>` - Toggle JTAG select line
- `POST /api/network/config` - Configure DHCP or static IP

### Web UI

Browser-based interface with real-time control:
- Visual GPIO state display with instant feedback
- JTAG line control buttons
- Network configuration
- System status monitoring

Access at: `http://<device-ip>/` (default: 192.168.1.100)

## Architecture

```
jtag-switch/
├── CMakeLists.txt          # Build configuration
├── prj.conf                # Kernel configuration
├── README.md               # This file
├── src/
│   ├── main.c              # Application entry point
│   ├── gpio_control.c/h    # GPIO control module
│   └── shell_cmds.c/h      # Future shell commands
└── boards/
    ├── frdm_k64f.overlay   # FRDM-K64F GPIO mapping
```

## Troubleshooting

### Build Errors

**Error**: `jtag-select0 alias not defined`

Solution: Ensure you have the correct board overlay file in `boards/<board_name>.overlay`

**Error**: `GPIO device not ready`

Solution: Check that the GPIO controller is enabled in your board's device tree

### Runtime Issues

**No output on serial console**

- Verify baud rate is set to 115200
- Check USB cable and driver installation
- Try different serial terminal program

**GPIOs not switching**

- Verify hardware connections to Arduino shield
- Check that correct pins are defined in overlay
- Use oscilloscope/multimeter to verify GPIO output

## License

SPDX-License-Identifier: Apache-2.0

## Resources

- [Zephyr Project Documentation](https://docs.zephyrproject.org)
- [Zephyr GPIO Driver API](https://docs.zephyrproject.org/latest/hardware/peripherals/gpio.html)
- [Device Tree Guide](https://docs.zephyrproject.org/latest/build/dts/index.html)
