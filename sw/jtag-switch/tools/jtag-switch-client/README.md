# JTAG Switch Python Client

Python library and CLI tool for controlling JTAG Switch device via USB serial or REST API.

## Features

- **Dual Backend Support**: USB serial and REST API with uniform interface
- **Library API**: Importable Python package for automation scripts
- **CLI Tool**: Command-line interface for manual control
- **Auto-Detection**: Automatic USB device discovery for serial interface
- **Context Manager**: Clean resource management with `with` statement
- **Comprehensive Error Handling**: Clear error messages and exit codes

## Installation

```bash
# Navigate to the client directory
cd jtag-switch/tools/jtag-switch-client

# Install dependencies
pip install -r requirements.txt

# For USB device enumeration (improves auto-detection)
# Linux: may require udev rules or running as root
# macOS: should work out of the box
# Windows: may require libusb drivers
```

## Library Usage

The library provides a clean Python API for automation scripts.

### Basic Example

```python
from jtag_switch import JtagSwitchClient

# Serial interface with auto-detect
with JtagSwitchClient(interface='serial') as client:
    # Get status
    status = client.jtag_status()
    print(f"Select0: {status['data']['select0']}")
    print(f"Select1: {status['data']['select1']}")

    # Control JTAG lines
    client.jtag_select(0, 1)  # Set line 0 to connector 1
    client.jtag_toggle(1)     # Toggle line 1

    # Network configuration
    client.net_set_dhcp()
    client.net_save()
```

### REST API Example

```python
from jtag_switch import JtagSwitchClient

# REST API interface
with JtagSwitchClient(interface='rest', host='192.168.1.100') as client:
    # Get device info
    info = client.device_info()
    print(f"Device: {info['data']['device']}")
    print(f"Board: {info['data']['board']}")

    # Control JTAG
    client.jtag_select(0, 1)
    client.jtag_toggle(0)

    # Network configuration
    client.net_set_static('192.168.1.100', '255.255.255.0', '192.168.1.1')
```

### Manual Connection Management

```python
from jtag_switch import JtagSwitchClient

# Without context manager
client = JtagSwitchClient(interface='serial', port='/dev/ttyACM0')
client.connect()

try:
    result = client.jtag_status()
    print(result['message'])
finally:
    client.disconnect()
```

### Error Handling

```python
from jtag_switch import (
    JtagSwitchClient,
    DeviceNotFoundError,
    ConnectionError,
    CommandNotSupportedError,
    CommandExecutionError
)

try:
    with JtagSwitchClient(interface='serial') as client:
        result = client.jtag_select(0, 1)
except DeviceNotFoundError:
    print("Device not found - check USB connection")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except CommandNotSupportedError as e:
    print(f"Command not supported: {e}")
except CommandExecutionError as e:
    print(f"Command failed: {e}")
```

### Available Methods

All methods return a dictionary with:
- `success`: bool - True if command succeeded
- `data`: dict - Command-specific data
- `message`: str - Human-readable message

**JTAG Commands**:
- `jtag_select(line, value)` - Set select line (0-1) to value (0-1)
- `jtag_toggle(line)` - Toggle select line (0-1)
- `jtag_status()` - Get GPIO status

**Network Commands**:
- `net_status()` - Get network status
- `net_config()` - Get network configuration (serial only)
- `net_set_dhcp()` - Enable DHCP mode
- `net_set_static(ip, netmask, gateway)` - Set static IP
- `net_restart()` - Restart network (serial only)
- `net_save()` - Save configuration (serial only)

**Device Commands**:
- `device_info()` - Get device information
- `health_check()` - Check connectivity (REST only)

## CLI Usage

The CLI tool mirrors device shell commands for ease of use.

### Basic Syntax

```bash
jtag-cli.py --interface {serial|rest} [options] <command> [args...]
```

### Serial Interface Examples

```bash
# Auto-detect USB device
./jtag-cli.py --interface serial jtag status
./jtag-cli.py --interface serial jtag select0 1
./jtag-cli.py --interface serial jtag select1 0
./jtag-cli.py --interface serial jtag toggle0
./jtag-cli.py --interface serial jtag toggle1

# Specify serial port
./jtag-cli.py --interface serial --serial-port /dev/ttyACM0 jtag status

# Network configuration
./jtag-cli.py --interface serial net status
./jtag-cli.py --interface serial net config
./jtag-cli.py --interface serial net set dhcp
./jtag-cli.py --interface serial net set static 192.168.1.100 255.255.255.0 192.168.1.1
./jtag-cli.py --interface serial net save
./jtag-cli.py --interface serial net restart

# Device info
./jtag-cli.py --interface serial device info
```

### REST API Examples

```bash
# JTAG control
./jtag-cli.py --interface rest --ip 192.168.1.100 jtag status
./jtag-cli.py --interface rest --ip 192.168.1.100 jtag select0 1
./jtag-cli.py --interface rest --ip 192.168.1.100 jtag toggle0

# Network configuration
./jtag-cli.py --interface rest --ip 192.168.1.100 net status
./jtag-cli.py --interface rest --ip 192.168.1.100 net set dhcp
./jtag-cli.py --interface rest --ip 192.168.1.100 net set static 192.168.1.100 255.255.255.0 192.168.1.1

# Device info and health
./jtag-cli.py --interface rest --ip 192.168.1.100 device info
./jtag-cli.py --interface rest --ip 192.168.1.100 health

# Custom port
./jtag-cli.py --interface rest --ip 192.168.1.100 --port 8080 jtag status
```

### Verbose Output

```bash
# Verbose mode shows full result dictionary
./jtag-cli.py --interface serial -v jtag status

# Output:
# Success: True
# Message: JTAG Switch Status:
#   select0: 0 (connector 0)
#   select1: 1 (connector 1)
#
# Board: frdm_k64f
# Data:
#   select0: 0
#   select1: 1
#   board: frdm_k64f
```

### Exit Codes

- `0` - Success
- `1` - Command failed
- `2` - Device not found
- `3` - Connection error
- `4` - Command not supported by backend
- `5` - Invalid usage/arguments
- `99` - Unexpected error

## Backend Feature Comparison

| Command | Serial | REST | Notes |
|---------|--------|------|-------|
| **JTAG Commands** | | | |
| `jtag select0/1` | ✓ | ✓ | Full parity |
| `jtag toggle0/1` | ✓ | ✓ | Full parity |
| `jtag status` | ✓ | ✓ | Full parity |
| **Network Commands** | | | |
| `net status` | ✓ | ✓ | Full parity |
| `net config` | ✓ | ✗ | Serial only - use `net status` for REST |
| `net set dhcp` | ✓ | ✓ | Full parity |
| `net set static` | ✓ | ✓ | Full parity |
| `net restart` | ✓ | ✗ | Serial only - REST auto-restarts |
| `net save` | ✓ | ✗ | Serial only - REST auto-saves |
| **Device Commands** | | | |
| `device info` | ✓ | ✓ | Full parity |
| `health` | ✗ | ✓ | REST only |

Commands marked with ✗ raise `CommandNotSupportedError` with helpful messages.

## Architecture

```
jtag-switch/tools/jtag-switch-client/
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── jtag_switch/                     # Library package
│   ├── __init__.py                  # Package exports
│   ├── client.py                    # JtagSwitchClient class
│   ├── exceptions.py                # Custom exceptions
│   └── backends/
│       ├── __init__.py
│       ├── base.py                  # Abstract backend interface
│       ├── serial_backend.py        # USB serial implementation
│       ├── rest_backend.py          # REST API implementation
│       └── serial_utils.py          # Serial communication utilities
└── jtag-cli.py                      # CLI entry point
```

## Troubleshooting

### Serial Interface Issues

**Device not found (auto-detect fails)**:
- Verify device is connected via USB
- Check `dmesg` (Linux) for USB enumeration
- Verify VID:PID (0x1FC9:0x4520)
- Try specifying port manually: `--serial-port /dev/ttyACM0`
- May need udev rules or root privileges on Linux

**Permission denied**:
- Linux: Add user to `dialout` group: `sudo usermod -a -G dialout $USER`
- Or run with sudo (not recommended)
- Set udev rules for device

**Connection timeout**:
- Device may be in use by another program (screen, minicom, etc.)
- Try power-cycling the device
- Check serial port settings (115200 baud)

### REST API Issues

**Connection refused**:
- Verify device is on network
- Check IP address: `ping 192.168.1.100`
- Verify HTTP server is running on device
- Check firewall settings

**Timeout**:
- Network connectivity issues
- Device may be rebooting
- Increase timeout in code if needed

**HTTP errors**:
- 400: Invalid request parameters
- 500: Device operation failed
- Check device logs via serial console

### USB Device Enumeration

On Linux, create udev rule for non-root access:

```bash
# /etc/udev/rules.d/99-jtag-switch.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="1fc9", ATTR{idProduct}=="0001", MODE="0666"

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Development

### Running Tests

```bash
# Test serial interface (requires device)
./jtag-cli.py --interface serial jtag status

# Test REST API (requires device on network)
./jtag-cli.py --interface rest --ip 192.168.1.100 jtag status

# Test library in Python
python3 -c "
from jtag_switch import JtagSwitchClient
with JtagSwitchClient(interface='serial') as client:
    print(client.jtag_status())
"
```

### Extending

To add new commands:

1. Add method to `Backend` abstract base class (backends/base.py)
2. Implement in both `SerialBackend` and `RestBackend`
3. Add method to `JtagSwitchClient` (client.py)
4. Add CLI command handler (jtag-cli.py)

## License

SPDX-License-Identifier: Apache-2.0

## Related Documentation

- [JTAG Switch Firmware](../../README.md)
- [Test Suite](../../tests/)
- [CLAUDE.md](../../../CLAUDE.md) - Project documentation
