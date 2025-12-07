# JTAG Switch

A hardware and software solution for automatically switching JTAG debuggers between multiple test benches in automated hardware testing environments.

## Overview

The JTAG Switch enables efficient sharing of expensive or limited-availability JTAG debuggers across multiple hardware test benches. Instead of purchasing dedicated debuggers for each test bench in CI/CD pipelines, a single JTAG debugger can be dynamically routed between two independent test targets, maximizing hardware utilization while maintaining testing throughput.

## Project Structure

This repository contains both hardware and software components:

### Hardware (`hw/`)

Arduino shield PCB design for JTAG multiplexing hardware:
- **KiCad Project**: Complete schematic and PCB layout
- **Files**: `jtag_switch.kicad_sch`, `jtag_switch.kicad_pcb`
- **Interface**: Arduino-compatible headers for connection to microcontroller EVBs
- **Switching**: Two independent GPIO-controlled select lines for JTAG routing

The shield plugs into any Arduino-compatible microcontroller evaluation board and provides the physical JTAG switching circuitry.

### Software (`sw/`)

Zephyr RTOS firmware for controlling the JTAG switch hardware:
- **Platform**: Runs on any Zephyr-supported microcontroller with Arduino headers
- **Supported Boards**:
  - FRDM-K64F (NXP Kinetis K64) - primary development board with Ethernet
  - FRDM-MCXC444 (NXP MCX C444) - development board with USB serial only
- **Control Interfaces**:
  - USB serial shell (115200 baud)
  - Ethernet REST API with JSON endpoints
  - Web-based UI with real-time control
- **Safety**: Enforces mutual exclusion - both GPIO select lines never HIGH simultaneously

See [sw/jtag-switch/README.md](sw/jtag-switch/README.md) for complete software documentation including build instructions, API reference, and testing information.

## Quick Start

### Hardware Setup

1. Open the KiCad project in `hw/` to view or manufacture the Arduino shield
2. Assemble the shield and mount it on a compatible microcontroller EVB
3. Connect JTAG debugger and target devices to the shield connectors

### Software Setup

```bash
# Navigate to software directory
cd sw

# Set up Zephyr environment
source .venv/bin/activate
source zephyr/zephyr-env.sh

# Build and flash firmware (FRDM-K64F)
west build -b frdm_k64f jtag-switch
west flash

# Or build and flash firmwarefor FRDM MCXC444
west build -b frdm_mcxc444 jtag-switch
west flash


### Usage

**Via USB Serial:**
```bash
screen /dev/ttyACM0 115200
uart:~$ jtag status
uart:~$ jtag select0 1
```

**Via REST API:**
```bash
# Get current status
curl http://192.168.1.100/api/status

# Switch to connector 1 on select line 0
curl -X POST "http://192.168.1.100/api/select?line=0&connector=1"
```

**Via Web UI:**

Navigate to `http://192.168.1.100/` in a web browser for graphical control.

## Documentation

- **Software Details**: [sw/jtag-switch/README.md](sw/jtag-switch/README.md)
- **Software Development Guide**: [sw/jtag-switch/CLAUDE.md](sw/jtag-switch/CLAUDE.md)
- **Hardware Design**: Open `hw/jtag_switch.kicad_pro` in KiCad

## License

SPDX-License-Identifier: Apache-2.0
