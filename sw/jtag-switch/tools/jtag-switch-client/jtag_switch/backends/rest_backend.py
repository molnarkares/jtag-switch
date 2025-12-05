"""
REST API backend for JTAG Switch communication.
"""

import requests
from typing import Dict, Any

from .base import Backend
from ..exceptions import (
    ConnectionError,
    CommandNotSupportedError,
    CommandExecutionError
)


class RestBackend(Backend):
    """
    REST API backend implementation.

    Communicates with JTAG Switch device via HTTP REST API endpoints.
    """

    def __init__(self, host: str, port: int = 80):
        """
        Initialize REST backend.

        Args:
            host: Device IP address (e.g., "192.168.1.100")
            port: HTTP port (default: 80)
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api"
        self.timeout = (5, 10)  # (connect_timeout, read_timeout)
        self.session = None

    def connect(self) -> None:
        """Establish HTTP session."""
        try:
            self.session = requests.Session()
            # Verify connectivity with health check
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

    def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            self.session.close()
            self.session = None

    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Perform GET request."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise CommandExecutionError(f"GET {endpoint} failed: {e}")

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform POST request."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise CommandExecutionError(f"POST {endpoint} failed: {e}")

    # JTAG Commands

    def jtag_select(self, line: int, value: int) -> Dict[str, Any]:
        """Set JTAG select line."""
        result = self._post("/select", {"line": line, "connector": value})

        return {
            'success': result.get('success', True),
            'data': {
                'line': line,
                'value': value,
                'select0': result.get('select0'),
                'select1': result.get('select1')
            },
            'message': f"select{line} set to {value} (connector {value})"
        }

    def jtag_toggle(self, line: int) -> Dict[str, Any]:
        """Toggle JTAG select line."""
        result = self._post("/toggle", {"line": line})

        new_state = result.get('state')
        return {
            'success': result.get('success', True),
            'data': {
                'line': line,
                'state': new_state
            },
            'message': f"select{line} toggled to {1 if new_state else 0} (connector {1 if new_state else 0})"
        }

    def jtag_status(self) -> Dict[str, Any]:
        """Get JTAG GPIO status."""
        result = self._get("/status")

        select0_val = 1 if result.get('select0') else 0
        select1_val = 1 if result.get('select1') else 0

        # Try to get board info from device info endpoint
        board = "unknown"
        try:
            info = self._get("/info")
            board = info.get('board', 'unknown')
        except:
            pass

        return {
            'success': True,
            'data': {
                'select0': select0_val,
                'select1': select1_val,
                'board': board
            },
            'message': f"JTAG Switch Status:\n  select0: {select0_val} (connector {select0_val})\n  select1: {select1_val} (connector {select1_val})\n\nBoard: {board}"
        }

    # Network Commands

    def net_status(self) -> Dict[str, Any]:
        """Get network status."""
        result = self._get("/status")
        network = result.get('network', {})

        mode = "DHCP" if network.get('dhcp_enabled') else "Static IP"
        link_up = network.get('link_up', False)

        # Get uptime from system section
        system = result.get('system', {})
        uptime = system.get('uptime', 0)

        return {
            'success': True,
            'data': {
                'mode': mode,
                'ip': network.get('ip'),
                'netmask': network.get('netmask'),
                'gateway': network.get('gateway'),
                'mac': network.get('mac'),
                'link_up': link_up,
                'uptime': uptime
            },
            'message': f"Network Status:\n  Mode: {mode}\n  IP Address: {network.get('ip')}\n  Netmask: {network.get('netmask')}\n  Gateway: {network.get('gateway')}\n  MAC Address: {network.get('mac')}\n  Link: {'Up' if link_up else 'Down'}\n  Uptime: {uptime} seconds"
        }

    def net_config(self) -> Dict[str, Any]:
        """Get network configuration - NOT SUPPORTED via REST."""
        raise CommandNotSupportedError(
            "'net config' command is only available via serial interface. "
            "Use 'net status' instead for REST API."
        )

    def net_set_dhcp(self) -> Dict[str, Any]:
        """Enable DHCP mode."""
        result = self._post("/network/config", {"mode": "dhcp"})

        return {
            'success': result.get('success', True),
            'data': {'restart_required': result.get('restart_required', False)},
            'message': "Enabling DHCP mode...\nDHCP mode enabled successfully.\nNetwork will restart automatically."
        }

    def net_set_static(self, ip: str, netmask: str, gateway: str) -> Dict[str, Any]:
        """Set static IP configuration."""
        result = self._post("/network/config", {
            "mode": "static",
            "ip": ip,
            "netmask": netmask,
            "gateway": gateway
        })

        return {
            'success': result.get('success', True),
            'data': {
                'ip': ip,
                'netmask': netmask,
                'gateway': gateway,
                'restart_required': result.get('restart_required', False)
            },
            'message': f"Setting static IP configuration...\n  IP Address: {ip}\n  Netmask: {netmask}\n  Gateway: {gateway}\nStatic IP configuration set successfully.\nNetwork will restart automatically."
        }

    def net_restart(self) -> Dict[str, Any]:
        """Restart network - NOT SUPPORTED via REST."""
        raise CommandNotSupportedError(
            "'net restart' command is only available via serial interface. "
            "Network restarts automatically after configuration changes via REST API."
        )

    def net_save(self) -> Dict[str, Any]:
        """Save network config - NOT SUPPORTED via REST."""
        raise CommandNotSupportedError(
            "'net save' command is only available via serial interface. "
            "Configuration is saved automatically via REST API."
        )

    # Device Information

    def device_info(self) -> Dict[str, Any]:
        """Get device information."""
        result = self._get("/info")

        return {
            'success': True,
            'data': {
                'device': result.get('device'),
                'version': result.get('version'),
                'zephyr': result.get('zephyr'),
                'board': result.get('board')
            },
            'message': f"Device: {result.get('device')}\nVersion: {result.get('version')}\nZephyr: {result.get('zephyr')}\nBoard: {result.get('board')}"
        }

    def health_check(self) -> Dict[str, Any]:
        """Check device health."""
        result = self._get("/health")

        status = result.get('status')
        return {
            'success': status == 'ok',
            'data': {'status': status},
            'message': f"Health: {status}"
        }
