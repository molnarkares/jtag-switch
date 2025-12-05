#!/usr/bin/env python3
"""
Serial Shell Command Tests for JTAG Switch

Tests all shell commands via USB CDC ACM serial interface.
Tests automatically skip if hardware is unavailable.

Copyright (c) 2025 JTAG Switch Project
SPDX-License-Identifier: Apache-2.0
"""

import logging
import sys
import time
import unittest
from typing import Optional, List
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try importing serial utilities
try:
    from serial_utils import find_jtag_switch_device, ShellSession
except ImportError:
    logger.error("Failed to import serial_utils - tests will be skipped")
    find_jtag_switch_device = None
    ShellSession = None


class SerialShellTestCase(unittest.TestCase):
    """
    Base class for serial shell command tests.

    Provides:
        - Automatic device discovery
        - Serial port management
        - Shell session handling
        - Auto-skip if device unavailable
    """

    serial_port: Optional[object] = None
    shell: Optional[ShellSession] = None
    device_port: Optional[str] = None

    @classmethod
    def setUpClass(cls):
        """
        Find device and establish serial connection.

        Raises:
            unittest.SkipTest: If device not found or dependencies missing
        """
        # Check for pyserial
        try:
            import serial
        except ImportError:
            raise unittest.SkipTest(
                "pyserial not installed (pip install pyserial)"
            )

        # Check for pyusb (optional, warn if missing)
        try:
            import usb.core
        except ImportError:
            logger.warning(
                "pyusb not installed - using fallback device detection"
            )

        # Find device
        if find_jtag_switch_device is None:
            raise unittest.SkipTest("serial_utils module not available")

        cls.device_port = find_jtag_switch_device()
        if not cls.device_port:
            raise unittest.SkipTest(
                "JTAG Switch device not found (USB not connected)"
            )

        logger.info(f"Found JTAG Switch at {cls.device_port}")

        # Open serial port
        try:
            cls.serial_port = serial.Serial(
                port=cls.device_port,
                baudrate=115200,
                timeout=2.0,
                write_timeout=1.0
            )
        except serial.SerialException as e:
            raise unittest.SkipTest(f"Failed to open serial port: {e}")

        # Create shell session
        cls.shell = ShellSession(cls.serial_port)

        # Wait for initial prompt
        if not cls.shell.wait_for_prompt(timeout=5.0):
            cls.serial_port.close()
            raise unittest.SkipTest(
                "Shell prompt not detected (device not responding)"
            )

        logger.info("Shell session established")

    @classmethod
    def tearDownClass(cls):
        """Close serial connection"""
        if cls.serial_port and cls.serial_port.is_open:
            cls.serial_port.close()
            logger.info("Serial port closed")

    def setUp(self):
        """Prepare for individual test"""
        # Small delay between tests
        time.sleep(0.1)

    def tearDown(self):
        """Cleanup after individual test"""
        # Flush any remaining data
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.reset_input_buffer()


@pytest.mark.serial
@pytest.mark.timeout(30)
class JtagCommandTests(SerialShellTestCase):
    """Test jtag command group (12 tests)"""

    def test_jtag_select0_to_0(self):
        """Test 'jtag select0 0' sets line to connector 0"""
        output = self.shell.execute_command("jtag select0 0")
        output_text = " ".join(output)

        self.assertIn("select0 set to 0", output_text,
                     f"Expected 'select0 set to 0' in output: {output_text}")
        self.assertIn("connector 0", output_text,
                     f"Expected 'connector 0' in output: {output_text}")

    def test_jtag_select0_to_1(self):
        """Test 'jtag select0 1' sets line to connector 1"""
        output = self.shell.execute_command("jtag select0 1")
        output_text = " ".join(output)

        self.assertIn("select0 set to 1", output_text,
                     f"Expected 'select0 set to 1' in output: {output_text}")
        self.assertIn("connector 1", output_text,
                     f"Expected 'connector 1' in output: {output_text}")

    def test_jtag_select1_to_0(self):
        """Test 'jtag select1 0' sets line to connector 0"""
        output = self.shell.execute_command("jtag select1 0")
        output_text = " ".join(output)

        self.assertIn("select1 set to 0", output_text,
                     f"Expected 'select1 set to 0' in output: {output_text}")
        self.assertIn("connector 0", output_text,
                     f"Expected 'connector 0' in output: {output_text}")

    def test_jtag_select1_to_1(self):
        """Test 'jtag select1 1' sets line to connector 1"""
        output = self.shell.execute_command("jtag select1 1")
        output_text = " ".join(output)

        self.assertIn("select1 set to 1", output_text,
                     f"Expected 'select1 set to 1' in output: {output_text}")
        self.assertIn("connector 1", output_text,
                     f"Expected 'connector 1' in output: {output_text}")

    def test_jtag_toggle0(self):
        """Test 'jtag toggle0' toggles select0"""
        # Set to known state first
        self.shell.execute_command("jtag select0 0")
        time.sleep(0.1)

        # Toggle
        output = self.shell.execute_command("jtag toggle0")
        output_text = " ".join(output)

        # Should toggle to 1
        self.assertIn("select0 toggled to 1", output_text,
                     f"Expected 'select0 toggled to 1' in output: {output_text}")

    def test_jtag_toggle1(self):
        """Test 'jtag toggle1' toggles select1"""
        # Set to known state first
        self.shell.execute_command("jtag select1 0")
        time.sleep(0.1)

        # Toggle
        output = self.shell.execute_command("jtag toggle1")
        output_text = " ".join(output)

        # Should toggle to 1
        self.assertIn("select1 toggled to 1", output_text,
                     f"Expected 'select1 toggled to 1' in output: {output_text}")

    def test_jtag_toggle_twice_returns_to_original(self):
        """Test double toggle returns to original state"""
        # Set known state
        self.shell.execute_command("jtag select0 0")
        time.sleep(0.1)

        # Toggle twice
        self.shell.execute_command("jtag toggle0")
        time.sleep(0.1)
        output = self.shell.execute_command("jtag toggle0")
        output_text = " ".join(output)

        # Should be back to 0
        self.assertIn("toggled to 0", output_text,
                     f"Expected 'toggled to 0' in output: {output_text}")

    def test_jtag_status_output_format(self):
        """Test 'jtag status' shows required fields"""
        output = self.shell.execute_command("jtag status")
        output_text = "\n".join(output)

        # Should contain all required fields
        self.assertIn("JTAG Switch Status", output_text,
                     "Expected 'JTAG Switch Status' in output")
        self.assertIn("select0:", output_text,
                     "Expected 'select0:' in output")
        self.assertIn("select1:", output_text,
                     "Expected 'select1:' in output")
        self.assertIn("Board:", output_text,
                     "Expected 'Board:' in output")

    def test_jtag_status_reflects_current_state(self):
        """Test 'jtag status' shows actual GPIO states"""
        # Set known state: select0=1, select1=0
        self.shell.execute_command("jtag select0 1")
        time.sleep(0.1)
        self.shell.execute_command("jtag select1 0")
        time.sleep(0.1)

        # Check status
        output = self.shell.execute_command("jtag status")
        output_text = "\n".join(output)

        # Should show select0=1, select1=0
        self.assertRegex(output_text, r"select0:\s*1",
                        f"Expected 'select0: 1' in output: {output_text}")
        self.assertRegex(output_text, r"select1:\s*0",
                        f"Expected 'select1: 0' in output: {output_text}")

    def test_jtag_select0_invalid_value(self):
        """Test 'jtag select0 2' returns error"""
        output = self.shell.execute_command("jtag select0 2")
        output_text = " ".join(output)

        # Expected: "Invalid value. Use 0 or 1"
        self.assertIn("Invalid value", output_text,
                     f"Expected 'Invalid value' in error: {output_text}")
        self.assertIn("0 or 1", output_text,
                     f"Expected '0 or 1' in error: {output_text}")

    def test_jtag_select0_missing_argument(self):
        """Test 'jtag select0' without arg returns usage"""
        output = self.shell.execute_command("jtag select0")
        output_text = " ".join(output)

        # Expected: "Usage: jtag select0 <0|1>"
        self.assertIn("Usage", output_text,
                     f"Expected 'Usage' in error: {output_text}")
        self.assertIn("jtag select0", output_text,
                     f"Expected 'jtag select0' in error: {output_text}")

    def test_jtag_invalid_subcommand(self):
        """Test 'jtag invalid' returns error"""
        output = self.shell.execute_command("jtag invalid")
        output_text = " ".join(output).lower()

        # Shell should show error or help
        # (exact error depends on shell implementation)
        self.assertTrue(
            "invalid" in output_text or
            "unknown" in output_text or
            "help" in output_text or
            "subcommand" in output_text,
            f"Expected error message in output: {output_text}"
        )


@pytest.mark.serial
@pytest.mark.timeout(30)
class NetworkCommandTests(SerialShellTestCase):
    """Test net command group (3 tests)"""

    def test_net_status_output_format(self):
        """Test 'net status' shows all required fields"""
        output = self.shell.execute_command("net status", timeout=3.0)
        output_text = "\n".join(output)

        # Should contain all required fields
        self.assertIn("Network Status", output_text,
                     "Expected 'Network Status' in output")
        self.assertIn("Mode:", output_text,
                     "Expected 'Mode:' in output")
        self.assertIn("IP Address:", output_text,
                     "Expected 'IP Address:' in output")
        self.assertIn("MAC Address:", output_text,
                     "Expected 'MAC Address:' in output")
        self.assertIn("Link:", output_text,
                     "Expected 'Link:' in output")

    def test_net_status_ip_format_valid(self):
        """Test 'net status' shows valid IP address"""
        output = self.shell.execute_command("net status", timeout=3.0)
        output_text = "\n".join(output)

        # Should contain valid IP format
        # e.g., "IP Address: 192.168.1.100"
        ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        self.assertRegex(output_text, ip_pattern,
                        f"Expected valid IP address in output: {output_text}")

    def test_net_config_output_format(self):
        """Test 'net config' shows configuration"""
        output = self.shell.execute_command("net config", timeout=3.0)
        output_text = "\n".join(output)

        # Should contain configuration info
        self.assertIn("Network Configuration", output_text,
                     "Expected 'Network Configuration' in output")
        self.assertIn("Mode:", output_text,
                     "Expected 'Mode:' in output")

        # Mode should be either "dhcp" or "static"
        self.assertTrue(
            "dhcp" in output_text.lower() or
            "static" in output_text.lower(),
            f"Expected 'dhcp' or 'static' in output: {output_text}"
        )


def run_tests():
    """Run serial shell tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(JtagCommandTests))
    suite.addTests(loader.loadTestsFromTestCase(NetworkCommandTests))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print(f"✓ ALL TESTS PASSED ({result.testsRun} tests)")
    else:
        print(f"✗ TESTS FAILED")
        print(f"  Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"  Failed: {len(result.failures)}")
        print(f"  Errors: {len(result.errors)}")
    print(f"  Skipped: {len(result.skipped)}")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
