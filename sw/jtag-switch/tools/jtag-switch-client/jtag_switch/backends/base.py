"""
Abstract base class for JTAG Switch communication backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Backend(ABC):
    """
    Abstract base class for JTAG Switch communication backends.

    All backend implementations must provide a uniform interface
    for controlling the JTAG Switch device, regardless of the
    underlying communication method (USB serial or REST API).

    All command methods return a dict with the following structure:
        {
            'success': bool,     # True if command succeeded
            'data': dict,        # Command-specific data
            'message': str       # Human-readable message
        }
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the device.

        Raises:
            ConnectionError: If connection fails
            DeviceNotFoundError: If device cannot be found (serial only)
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the device."""
        pass

    # JTAG Control Commands

    @abstractmethod
    def jtag_select(self, line: int, value: int) -> Dict[str, Any]:
        """
        Set JTAG select line to specified value.

        Args:
            line: Select line number (0 or 1)
            value: Value to set (0 or 1)

        Returns:
            Result dict with success, data, and message

        Raises:
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def jtag_toggle(self, line: int) -> Dict[str, Any]:
        """
        Toggle JTAG select line.

        Args:
            line: Select line number (0 or 1)

        Returns:
            Result dict with success, data, and message

        Raises:
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def jtag_status(self) -> Dict[str, Any]:
        """
        Get current JTAG GPIO status.

        Returns:
            Result dict with success, data (select0, select1, board), and message

        Raises:
            CommandExecutionError: If command fails
        """
        pass

    # Network Commands

    @abstractmethod
    def net_status(self) -> Dict[str, Any]:
        """
        Get network status.

        Returns:
            Result dict with success, data (ip, netmask, gateway, etc.), and message

        Raises:
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def net_config(self) -> Dict[str, Any]:
        """
        Get network configuration.

        Returns:
            Result dict with success, data (mode, static IP settings), and message

        Raises:
            CommandNotSupportedError: If not supported by backend (REST)
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def net_set_dhcp(self) -> Dict[str, Any]:
        """
        Enable DHCP mode for network configuration.

        Returns:
            Result dict with success, data, and message

        Raises:
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def net_set_static(self, ip: str, netmask: str, gateway: str) -> Dict[str, Any]:
        """
        Set static IP configuration.

        Args:
            ip: IP address (e.g., "192.168.1.100")
            netmask: Network mask (e.g., "255.255.255.0")
            gateway: Gateway address (e.g., "192.168.1.1")

        Returns:
            Result dict with success, data, and message

        Raises:
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def net_restart(self) -> Dict[str, Any]:
        """
        Restart network interface.

        Returns:
            Result dict with success, data, and message

        Raises:
            CommandNotSupportedError: If not supported by backend (REST)
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def net_save(self) -> Dict[str, Any]:
        """
        Save network configuration to non-volatile storage.

        Returns:
            Result dict with success, data, and message

        Raises:
            CommandNotSupportedError: If not supported by backend (REST)
            CommandExecutionError: If command fails
        """
        pass

    # Device Information

    @abstractmethod
    def device_info(self) -> Dict[str, Any]:
        """
        Get device information (version, board, etc.).

        Returns:
            Result dict with success, data (device, version, board), and message

        Raises:
            CommandExecutionError: If command fails
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check device health/connectivity.

        Returns:
            Result dict with success, data, and message

        Raises:
            CommandNotSupportedError: If not supported by backend (serial)
            CommandExecutionError: If command fails
        """
        pass
