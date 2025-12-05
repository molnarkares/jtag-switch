"""
JTAG Switch Python Client Library

Provides a unified interface for controlling JTAG Switch device via
USB serial or REST API.

Example usage:
    from jtag_switch import JtagSwitchClient

    # Serial interface
    with JtagSwitchClient(interface='serial') as client:
        status = client.jtag_status()
        client.jtag_select(0, 1)

    # REST API
    with JtagSwitchClient(interface='rest', host='192.168.1.100') as client:
        client.jtag_toggle(0)
        info = client.device_info()
"""

from .client import JtagSwitchClient
from .exceptions import (
    JtagSwitchError,
    DeviceNotFoundError,
    ConnectionError,
    CommandNotSupportedError,
    CommandExecutionError,
    InvalidResponseError
)

__version__ = '1.0.0'

__all__ = [
    'JtagSwitchClient',
    'JtagSwitchError',
    'DeviceNotFoundError',
    'ConnectionError',
    'CommandNotSupportedError',
    'CommandExecutionError',
    'InvalidResponseError',
]
