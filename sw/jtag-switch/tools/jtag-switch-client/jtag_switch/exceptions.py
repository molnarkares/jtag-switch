"""
Custom exceptions for JTAG Switch client.
"""


class JtagSwitchError(Exception):
    """Base exception for all JTAG Switch client errors."""
    pass


class DeviceNotFoundError(JtagSwitchError):
    """Raised when USB device cannot be found during auto-detection."""
    pass


class ConnectionError(JtagSwitchError):
    """Raised when connection to device fails."""
    pass


class CommandNotSupportedError(JtagSwitchError):
    """Raised when a command is not supported by the current backend."""
    pass


class CommandExecutionError(JtagSwitchError):
    """Raised when command execution fails on the device."""
    pass


class InvalidResponseError(JtagSwitchError):
    """Raised when device response cannot be parsed."""
    pass
