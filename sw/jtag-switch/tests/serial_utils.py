#!/usr/bin/env python3
"""
Serial Utilities for JTAG Switch Testing

Provides USB device discovery and shell interaction utilities for testing
JTAG Switch via USB CDC ACM serial interface.

Copyright (c) 2025 JTAG Switch Project
SPDX-License-Identifier: Apache-2.0
"""

import logging
import re
import sys
import time
from typing import Optional, List

logger = logging.getLogger(__name__)

# JTAG Switch USB identifiers (from prj.conf)
JTAG_SWITCH_VID = 0x1209
JTAG_SWITCH_PID = 0x4520
JTAG_SWITCH_PRODUCT = "JTAG Switch"


def find_jtag_switch_device() -> Optional[str]:
    """
    Find JTAG Switch USB CDC ACM device by product string.

    Returns:
        Serial port path (e.g., '/dev/ttyACM0') or None if not found

    Strategy:
        1. Try PyUSB enumeration (most reliable, cross-platform)
        2. Fallback to PySerial list_ports (simpler but less accurate)
        3. Return None if device not found
    """
    # Try Method 1: PyUSB enumeration (primary)
    try:
        device_port = _find_via_pyusb()
        if device_port:
            return device_port
    except ImportError:
        logger.warning("pyusb not available, using fallback method")
    except Exception as e:
        logger.warning(f"PyUSB enumeration failed: {e}, using fallback")

    # Try Method 2: PySerial list_ports (fallback)
    try:
        device_port = _find_via_list_ports()
        if device_port:
            return device_port
    except Exception as e:
        logger.warning(f"list_ports enumeration failed: {e}")

    return None


def _find_via_pyusb() -> Optional[str]:
    """Find device using PyUSB (cross-platform)"""
    try:
        import usb.core
        import usb.util
    except ImportError:
        raise ImportError("pyusb not installed")

    # Check for libusb backend
    try:
        backend = usb.core.find(find_all=False)  # Test backend
    except usb.core.NoBackendError:
        logger.warning("libusb backend not found")
        raise

    # Find all matching VID:PID devices
    devices = usb.core.find(
        find_all=True,
        idVendor=JTAG_SWITCH_VID,
        idProduct=JTAG_SWITCH_PID
    )

    for dev in devices:
        try:
            # Verify product string
            product = usb.util.get_string(dev, dev.iProduct)
            if JTAG_SWITCH_PRODUCT in product:
                # Device found - now map to serial port
                port = _usb_device_to_serial_port(dev)
                if port:
                    logger.info(f"Found {JTAG_SWITCH_PRODUCT} at {port} (via PyUSB)")
                    return port
        except (usb.core.USBError, ValueError) as e:
            logger.debug(f"Could not read device info: {e}")
            continue

    return None


def _usb_device_to_serial_port(device) -> Optional[str]:
    """Map USB device to serial port path (platform-specific)"""
    try:
        import serial.tools.list_ports
    except ImportError:
        logger.warning("pyserial not installed")
        return None

    # Get device location (bus, address)
    bus = device.bus
    address = device.address

    # List all serial ports
    ports = serial.tools.list_ports.comports()

    # Find matching port
    for port in ports:
        # Platform-specific matching
        if sys.platform.startswith('linux'):
            # Linux: match by bus-address in hwid or location
            hwid_str = port.hwid or ""
            location_str = port.location or ""
            if (f"{bus}-{address}" in hwid_str or
                f"{bus}-{address}" in location_str):
                return port.device
        elif sys.platform == 'darwin':
            # macOS: match by location
            if port.location and f"{bus}-{address}" in port.location:
                return port.device
        elif sys.platform == 'win32':
            # Windows: match by VID:PID (less precise)
            if (hasattr(port, 'vid') and hasattr(port, 'pid') and
                port.vid == device.idVendor and port.pid == device.idProduct):
                return port.device

    # Fallback: return first port with matching VID:PID
    for port in ports:
        if (hasattr(port, 'vid') and hasattr(port, 'pid') and
            port.vid == device.idVendor and port.pid == device.idProduct):
            logger.warning(f"Using inexact match for serial port: {port.device}")
            return port.device

    return None


def _find_via_list_ports() -> Optional[str]:
    """Find device using pyserial list_ports (fallback)"""
    try:
        import serial.tools.list_ports
    except ImportError:
        raise ImportError("pyserial not installed")

    ports = serial.tools.list_ports.comports()

    for port in ports:
        # Check VID:PID match
        if (hasattr(port, 'vid') and hasattr(port, 'pid') and
            port.vid == JTAG_SWITCH_VID and port.pid == JTAG_SWITCH_PID):
            logger.info(f"Found JTAG Switch at {port.device} (via list_ports)")
            return port.device

    return None


class ShellSession:
    """
    Manages interaction with Zephyr shell via serial port.

    Handles:
        - Prompt detection ("jtag:~$ ")
        - Command execution
        - Response parsing
        - VT100 escape sequence filtering
    """

    PROMPT = "jtag:~$ "
    VT100_PATTERN = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

    def __init__(self, serial_port):
        """
        Initialize shell session.

        Args:
            serial_port: Opened serial.Serial object
        """
        self.serial = serial_port
        self.prompt = self.PROMPT

    def wait_for_prompt(self, timeout: float = 5.0) -> bool:
        """
        Synchronize with shell by waiting for prompt.

        Strategy:
            1. Clear receive buffer
            2. Send newline every 0.5s
            3. Read response, strip VT100 codes
            4. Check for prompt string
            5. Return True if found, False on timeout

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            True if prompt detected, False on timeout
        """
        end_time = time.time() + timeout
        self.serial.reset_input_buffer()

        while time.time() < end_time:
            # Send newline to trigger prompt
            self.serial.write(b'\n')
            time.sleep(0.1)  # Give shell time to respond

            try:
                # Read with short timeout
                data = self.serial.read(256)
                if not data:
                    time.sleep(0.3)
                    continue

                # Decode and strip VT100
                text = data.decode('utf-8', errors='replace')
                clean_text = self.strip_vt100(text)

                # Check for prompt
                if self.PROMPT in clean_text:
                    logger.debug("Shell prompt detected")
                    return True

            except Exception as e:
                logger.debug(f"Read error: {e}")

            time.sleep(0.5)

        logger.warning(f"Shell prompt not detected after {timeout}s")
        return False

    def execute_command(self, command: str, timeout: float = 2.0) -> List[str]:
        """
        Execute shell command and return output lines.

        Args:
            command: Shell command to execute
            timeout: Maximum time to wait for response

        Returns:
            List of output lines (stripped of prompt and VT100 codes)

        Raises:
            TimeoutError: If command doesn't complete in time
        """
        # Clear input buffer
        self.serial.reset_input_buffer()

        # Send command
        cmd_bytes = (command + '\n').encode('utf-8')
        self.serial.write(cmd_bytes)
        time.sleep(0.05)  # Give shell time to process

        # Collect output
        lines = []
        end_time = time.time() + timeout

        # Read echo (command itself) and discard
        try:
            echo = self._read_until('\n', timeout=0.5)
            logger.debug(f"Echo discarded: {echo.strip()}")
        except:
            pass  # Echo not always present

        # Read output until prompt
        buffer = ""
        while time.time() < end_time:
            try:
                # Read available data
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    buffer += data.decode('utf-8', errors='replace')
                else:
                    time.sleep(0.05)
                    continue

                # Check if we have the prompt (end of output)
                if self.PROMPT in buffer:
                    # Process all accumulated data
                    lines_raw = buffer.split('\n')
                    for line in lines_raw:
                        line_clean = self.strip_vt100(line).strip()

                        # Skip if contains prompt
                        if self.PROMPT in line_clean:
                            # Remove prompt and add if not empty
                            line_clean = line_clean.replace(self.PROMPT, '').strip()
                            if line_clean:
                                lines.append(line_clean)
                            break

                        # Skip empty lines
                        if line_clean:
                            lines.append(line_clean)
                    break

            except Exception as e:
                logger.warning(f"Read error: {e}")
                break

        if time.time() >= end_time and self.PROMPT not in buffer:
            error_msg = f"Command timeout after {timeout}s: {command}"
            logger.error(error_msg)
            raise TimeoutError(error_msg)

        logger.debug(f"Command '{command}' returned {len(lines)} lines")
        return lines

    def _read_until(self, terminator: str, timeout: float = 1.0) -> str:
        """
        Helper: read until terminator or timeout.

        Args:
            terminator: String to read until
            timeout: Maximum time to wait

        Returns:
            Data read as string
        """
        term_bytes = terminator.encode('utf-8')
        old_timeout = self.serial.timeout
        try:
            self.serial.timeout = timeout
            data = self.serial.read_until(term_bytes)
            return data.decode('utf-8', errors='replace')
        finally:
            self.serial.timeout = old_timeout

    @staticmethod
    def strip_vt100(text: str) -> str:
        """
        Remove VT100/ANSI escape sequences from text.

        Handles:
            - Color codes (CONFIG_SHELL_VT100_COLORS=y)
            - Cursor positioning
            - Terminal control sequences

        Args:
            text: Text with VT100 codes

        Returns:
            Clean text without escape codes
        """
        return ShellSession.VT100_PATTERN.sub('', text)


class SerialConnection:
    """
    Context manager for serial port connections with automatic cleanup.

    Features:
        - Automatic open/close
        - Buffer flushing
        - Timeout configuration
        - Error recovery

    Example:
        with SerialConnection('/dev/ttyACM0') as ser:
            shell = ShellSession(ser)
            output = shell.execute_command('jtag status')
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        """
        Initialize serial connection parameters.

        Args:
            port: Serial port path (e.g., '/dev/ttyACM0')
            baudrate: Baud rate (default: 115200)
            timeout: Read timeout in seconds (default: 2.0)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def __enter__(self):
        """Open serial port and flush buffers"""
        try:
            import serial
        except ImportError:
            raise ImportError("pyserial not installed")

        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=1.0
        )

        # Flush buffers
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

        logger.info(f"Serial port {self.port} opened")
        return self.serial

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close serial port gracefully"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info(f"Serial port {self.port} closed")
        return False  # Don't suppress exceptions
