"""
High-level client interface for JTAG Switch device.
"""

from typing import Dict, Any


class JtagSwitchClient:
    """
    Unified client for JTAG Switch device.

    Provides a consistent interface for controlling the device via either
    USB serial or REST API backend. Supports context manager for automatic
    connection management.

    Examples:
        # Serial interface with auto-detect
        with JtagSwitchClient(interface='serial') as client:
            status = client.jtag_status()
            client.jtag_select(0, 1)

        # REST API interface
        with JtagSwitchClient(interface='rest', host='192.168.1.100') as client:
            client.jtag_toggle(0)
            info = client.device_info()
    """

    def __init__(self, interface: str, **kwargs):
        """
        Initialize JTAG Switch client.

        Args:
            interface: Communication interface - 'serial' or 'rest'

            For serial interface:
                port: str (optional) - Serial port path (e.g., "/dev/ttyACM0")
                                      If not provided, device will be auto-detected

            For rest interface:
                host: str (required) - Device IP address (e.g., "192.168.1.100")
                port: int (optional) - HTTP port (default: 80)

        Raises:
            ValueError: If interface is invalid
            DeviceNotFoundError: If device cannot be found (serial auto-detect)
            ConnectionError: If connection fails
        """
        if interface == 'serial':
            from .backends.serial_backend import SerialBackend
            self.backend = SerialBackend(**kwargs)
        elif interface == 'rest':
            from .backends.rest_backend import RestBackend
            self.backend = RestBackend(**kwargs)
        else:
            raise ValueError(f"Invalid interface: '{interface}'. Must be 'serial' or 'rest'.")

        self.interface = interface

    # Context manager support

    def __enter__(self):
        """Connect to device when entering context."""
        self.backend.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from device when exiting context."""
        self.backend.disconnect()
        return False

    # Manual connection management

    def connect(self) -> None:
        """
        Manually connect to device.

        Not needed when using context manager (with statement).
        """
        self.backend.connect()

    def disconnect(self) -> None:
        """
        Manually disconnect from device.

        Not needed when using context manager (with statement).
        """
        self.backend.disconnect()

    # JTAG Control Commands

    def jtag_select(self, line: int, value: int) -> Dict[str, Any]:
        """
        Set JTAG select line to specified value.

        Args:
            line: Select line number (0 or 1)
            value: Value to set (0 or 1)

        Returns:
            Result dictionary with keys:
                - success: bool
                - data: dict with command-specific data
                - message: str with human-readable message

        Raises:
            CommandExecutionError: If command fails
        """
        return self.backend.jtag_select(line, value)

    def jtag_toggle(self, line: int) -> Dict[str, Any]:
        """
        Toggle JTAG select line.

        Args:
            line: Select line number (0 or 1)

        Returns:
            Result dictionary

        Raises:
            CommandExecutionError: If command fails
        """
        return self.backend.jtag_toggle(line)

    def jtag_status(self) -> Dict[str, Any]:
        """
        Get current JTAG GPIO status.

        Returns:
            Result dictionary with data containing:
                - select0: int (0 or 1)
                - select1: int (0 or 1)
                - board: str (board name)

        Raises:
            CommandExecutionError: If command fails
        """
        return self.backend.jtag_status()

    # Network Commands

    def net_status(self) -> Dict[str, Any]:
        """
        Get network status.

        Returns:
            Result dictionary with data containing:
                - mode: str (DHCP or Static IP)
                - ip: str
                - netmask: str
                - gateway: str
                - mac: str
                - link_up: bool
                - uptime: int (seconds)

        Raises:
            CommandExecutionError: If command fails
        """
        return self.backend.net_status()

    def net_config(self) -> Dict[str, Any]:
        """
        Get network configuration.

        Note: Only available via serial interface.

        Returns:
            Result dictionary

        Raises:
            CommandNotSupportedError: If using REST interface
            CommandExecutionError: If command fails
        """
        return self.backend.net_config()

    def net_set_dhcp(self) -> Dict[str, Any]:
        """
        Enable DHCP mode for network configuration.

        Returns:
            Result dictionary

        Raises:
            CommandExecutionError: If command fails
        """
        return self.backend.net_set_dhcp()

    def net_set_static(self, ip: str, netmask: str, gateway: str) -> Dict[str, Any]:
        """
        Set static IP configuration.

        Args:
            ip: IP address (e.g., "192.168.1.100")
            netmask: Network mask (e.g., "255.255.255.0")
            gateway: Gateway address (e.g., "192.168.1.1")

        Returns:
            Result dictionary

        Raises:
            CommandExecutionError: If command fails
        """
        return self.backend.net_set_static(ip, netmask, gateway)

    def net_restart(self) -> Dict[str, Any]:
        """
        Restart network interface.

        Note: Only available via serial interface.
              REST API restarts network automatically after config changes.

        Returns:
            Result dictionary

        Raises:
            CommandNotSupportedError: If using REST interface
            CommandExecutionError: If command fails
        """
        return self.backend.net_restart()

    def net_save(self) -> Dict[str, Any]:
        """
        Save network configuration to non-volatile storage.

        Note: Only available via serial interface.
              REST API saves configuration automatically.

        Returns:
            Result dictionary

        Raises:
            CommandNotSupportedError: If using REST interface
            CommandExecutionError: If command fails
        """
        return self.backend.net_save()

    # Device Information

    def device_info(self) -> Dict[str, Any]:
        """
        Get device information.

        Returns:
            Result dictionary with data containing:
                - device: str (device name)
                - version: str (firmware version, REST only)
                - zephyr: str (Zephyr version, REST only)
                - board: str (board name)

        Raises:
            CommandExecutionError: If command fails
        """
        return self.backend.device_info()

    def health_check(self) -> Dict[str, Any]:
        """
        Check device health/connectivity.

        Note: Only available via REST interface.

        Returns:
            Result dictionary with data containing:
                - status: str ("ok" if healthy)

        Raises:
            CommandNotSupportedError: If using serial interface
            CommandExecutionError: If command fails
        """
        return self.backend.health_check()
