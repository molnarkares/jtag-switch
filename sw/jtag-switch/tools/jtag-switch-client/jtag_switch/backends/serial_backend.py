"""
Serial backend for JTAG Switch communication.
"""

import re
import serial
from typing import Dict, Any

from .base import Backend
from .serial_utils import find_jtag_switch_device, ShellSession
from ..exceptions import (
    DeviceNotFoundError,
    ConnectionError,
    CommandNotSupportedError,
    CommandExecutionError,
    InvalidResponseError
)


class SerialBackend(Backend):
    """
    Serial backend implementation.

    Communicates with JTAG Switch device via USB serial shell interface.
    """

    # Regex patterns for parsing shell output
    SELECT_PATTERN = re.compile(r'select(\d+):\s*(\d+)')
    BOARD_PATTERN = re.compile(r'Board:\s*(\S+)')
    IP_PATTERN = re.compile(r'IP Address:\s*(\S+)')
    NETMASK_PATTERN = re.compile(r'Netmask:\s*(\S+)')
    GATEWAY_PATTERN = re.compile(r'Gateway:\s*(\S+)')
    MAC_PATTERN = re.compile(r'MAC Address:\s*(\S+)')
    MODE_PATTERN = re.compile(r'Mode:\s*(\S+)')
    LINK_PATTERN = re.compile(r'Link:\s*(\S+)')
    UPTIME_PATTERN = re.compile(r'Uptime:\s*(\d+)')
    SUCCESS_PATTERN = re.compile(r'(set|toggled|enabled|saved|restarted).*successfully', re.IGNORECASE)
    ERROR_PATTERN = re.compile(r'(failed|error|invalid)', re.IGNORECASE)

    def __init__(self, port: str = None):
        """
        Initialize serial backend.

        Args:
            port: Serial port path (e.g., "/dev/ttyACM0").
                  If None, will auto-detect device.
        """
        self.port = port
        self.serial_port = None
        self.shell = None

    def connect(self) -> None:
        """Establish serial connection."""
        try:
            # Find device if port not specified
            if self.port is None:
                self.port = find_jtag_switch_device()
                if self.port is None:
                    raise DeviceNotFoundError(
                        "JTAG Switch device not found. "
                        "Ensure device is connected via USB and enumerated correctly."
                    )

            # Open serial port
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=115200,
                timeout=1
            )

            # Create shell session
            self.shell = ShellSession(self.serial_port)

            # Synchronize with prompt
            if not self.shell.wait_for_prompt(timeout=5.0):
                raise ConnectionError("Failed to synchronize with shell prompt")

        except serial.SerialException as e:
            raise ConnectionError(f"Failed to open serial port {self.port}: {e}")
        except Exception as e:
            if isinstance(e, (DeviceNotFoundError, ConnectionError)):
                raise
            raise ConnectionError(f"Unexpected error during connection: {e}")

    def disconnect(self) -> None:
        """Close serial connection."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        self.shell = None

    def _execute_command(self, command: str) -> list:
        """Execute shell command and return output lines."""
        try:
            return self.shell.execute_command(command)
        except Exception as e:
            raise CommandExecutionError(f"Command '{command}' failed: {e}")

    def _check_for_errors(self, output: list) -> bool:
        """Check if output contains error messages."""
        output_text = ' '.join(output)
        return bool(self.ERROR_PATTERN.search(output_text))

    # JTAG Commands

    def jtag_select(self, line: int, value: int) -> Dict[str, Any]:
        """Set JTAG select line."""
        command = f"jtag select{line} {value}"
        output = self._execute_command(command)

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to set select{line}: {' '.join(output)}")

        message = output[0] if output else f"select{line} set to {value}"

        return {
            'success': True,
            'data': {
                'line': line,
                'value': value
            },
            'message': message
        }

    def jtag_toggle(self, line: int) -> Dict[str, Any]:
        """Toggle JTAG select line."""
        command = f"jtag toggle{line}"
        output = self._execute_command(command)

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to toggle select{line}: {' '.join(output)}")

        # Parse new value from output (e.g., "select0 toggled to 1 (connector 1)")
        message = output[0] if output else f"select{line} toggled"
        new_value = None
        if output:
            match = re.search(r'toggled to (\d+)', output[0])
            if match:
                new_value = int(match.group(1))

        return {
            'success': True,
            'data': {
                'line': line,
                'state': new_value
            },
            'message': message
        }

    def jtag_status(self) -> Dict[str, Any]:
        """Get JTAG GPIO status."""
        output = self._execute_command("jtag status")

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to get status: {' '.join(output)}")

        # Parse output for select0, select1, and board
        data = {}
        output_text = '\n'.join(output)

        # Extract select lines
        for match in self.SELECT_PATTERN.finditer(output_text):
            line_num = int(match.group(1))
            value = int(match.group(2))
            data[f'select{line_num}'] = value

        # Extract board
        board_match = self.BOARD_PATTERN.search(output_text)
        if board_match:
            data['board'] = board_match.group(1)

        return {
            'success': True,
            'data': data,
            'message': '\n'.join(output)
        }

    # Network Commands

    def net_status(self) -> Dict[str, Any]:
        """Get network status."""
        output = self._execute_command("net status")

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to get network status: {' '.join(output)}")

        # Parse output
        data = {}
        output_text = '\n'.join(output)

        mode_match = self.MODE_PATTERN.search(output_text)
        if mode_match:
            data['mode'] = mode_match.group(1)

        ip_match = self.IP_PATTERN.search(output_text)
        if ip_match:
            data['ip'] = ip_match.group(1)

        netmask_match = self.NETMASK_PATTERN.search(output_text)
        if netmask_match:
            data['netmask'] = netmask_match.group(1)

        gateway_match = self.GATEWAY_PATTERN.search(output_text)
        if gateway_match:
            data['gateway'] = gateway_match.group(1)

        mac_match = self.MAC_PATTERN.search(output_text)
        if mac_match:
            data['mac'] = mac_match.group(1)

        link_match = self.LINK_PATTERN.search(output_text)
        if link_match:
            data['link_up'] = link_match.group(1).lower() == 'up'

        uptime_match = self.UPTIME_PATTERN.search(output_text)
        if uptime_match:
            data['uptime'] = int(uptime_match.group(1))

        return {
            'success': True,
            'data': data,
            'message': '\n'.join(output)
        }

    def net_config(self) -> Dict[str, Any]:
        """Get network configuration."""
        output = self._execute_command("net config")

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to get network config: {' '.join(output)}")

        # Parse output
        data = {}
        output_text = '\n'.join(output)

        mode_match = self.MODE_PATTERN.search(output_text)
        if mode_match:
            data['mode'] = mode_match.group(1).lower()

        # Extract static IP settings if present
        ip_match = re.search(r'Static IP:\s*(\S+)', output_text)
        if ip_match:
            data['static_ip'] = ip_match.group(1)

        netmask_match = re.search(r'Static Netmask:\s*(\S+)', output_text)
        if netmask_match:
            data['static_netmask'] = netmask_match.group(1)

        gateway_match = re.search(r'Static Gateway:\s*(\S+)', output_text)
        if gateway_match:
            data['static_gateway'] = gateway_match.group(1)

        return {
            'success': True,
            'data': data,
            'message': '\n'.join(output)
        }

    def net_set_dhcp(self) -> Dict[str, Any]:
        """Enable DHCP mode."""
        output = self._execute_command("net set dhcp")

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to enable DHCP: {' '.join(output)}")

        return {
            'success': True,
            'data': {},
            'message': '\n'.join(output)
        }

    def net_set_static(self, ip: str, netmask: str, gateway: str) -> Dict[str, Any]:
        """Set static IP configuration."""
        command = f"net set static {ip} {netmask} {gateway}"
        output = self._execute_command(command)

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to set static IP: {' '.join(output)}")

        return {
            'success': True,
            'data': {
                'ip': ip,
                'netmask': netmask,
                'gateway': gateway
            },
            'message': '\n'.join(output)
        }

    def net_restart(self) -> Dict[str, Any]:
        """Restart network interface."""
        output = self._execute_command("net restart")

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to restart network: {' '.join(output)}")

        return {
            'success': True,
            'data': {},
            'message': '\n'.join(output)
        }

    def net_save(self) -> Dict[str, Any]:
        """Save network configuration."""
        output = self._execute_command("net save")

        if self._check_for_errors(output):
            raise CommandExecutionError(f"Failed to save network config: {' '.join(output)}")

        return {
            'success': True,
            'data': {},
            'message': '\n'.join(output)
        }

    # Device Information

    def device_info(self) -> Dict[str, Any]:
        """Get device information from status output."""
        # Serial interface doesn't have dedicated device info command
        # Extract board info from jtag status
        status_result = self.jtag_status()

        data = {
            'device': 'JTAG Switch',
            'board': status_result['data'].get('board', 'unknown')
        }

        return {
            'success': True,
            'data': data,
            'message': f"Device: JTAG Switch\nBoard: {data['board']}"
        }

    def health_check(self) -> Dict[str, Any]:
        """Health check - NOT SUPPORTED via serial."""
        raise CommandNotSupportedError(
            "'health' command is only available via REST API interface."
        )
