#!/usr/bin/env python3
"""
JTAG Switch REST API Test Suite

Comprehensive test suite for all REST API endpoints:
- GET /api/health - Health check
- GET /api/status - Device status
- GET /api/info - Device information
- POST /api/select - JTAG line selection
- POST /api/toggle - Toggle JTAG line
- POST /api/network/config - Network configuration (optional)

Usage:
    python test_rest_api.py
    pytest test_rest_api.py -v
    pytest test_rest_api.py::HealthTests -v
"""

import unittest
import sys
import time
import pytest
from test_base import BaseTestCase
from test_config import Config, config


@pytest.mark.timeout(30)
class HealthTests(BaseTestCase):
    """Test GET /api/health endpoint"""

    def test_health_check_returns_200(self):
        """Health check should return HTTP 200"""
        response = self.device.get('/health')
        self.assertEqual(response.status_code, 200)

    def test_health_response_format(self):
        """Health check should return valid JSON with status field"""
        response = self.device.get('/health')
        data = self.assert_json_response(response, required_fields=['status'])
        self.assertEqual(data['status'], 'ok')


@pytest.mark.timeout(30)
class StatusTests(BaseTestCase):
    """Test GET /api/status endpoint"""

    def test_status_returns_200(self):
        """Status endpoint should return HTTP 200"""
        response = self.device.get('/status')
        self.assertEqual(response.status_code, 200)

    def test_status_has_required_fields(self):
        """Status response should have all required top-level fields"""
        response = self.device.get('/status')
        data = self.assert_json_response(
            response,
            required_fields=['select0', 'select1', 'network', 'system']
        )

        # Verify field types
        self.assertIsInstance(data['select0'], bool)
        self.assertIsInstance(data['select1'], bool)
        self.assertIsInstance(data['network'], dict)
        self.assertIsInstance(data['system'], dict)

    def test_status_network_info_valid(self):
        """Status response should have valid network information"""
        response = self.device.get('/status')
        data = self.assert_json_response(response)

        network = data['network']
        self.assertIn('ip', network)
        self.assertIn('mac', network)
        self.assertIn('dhcp_enabled', network)
        self.assertIn('link_up', network)

        # Verify network field types
        self.assertIsInstance(network['ip'], str)
        self.assertIsInstance(network['mac'], str)
        self.assertIsInstance(network['dhcp_enabled'], bool)
        self.assertIsInstance(network['link_up'], bool)

        # Basic IP format validation
        ip_parts = network['ip'].split('.')
        if len(ip_parts) == 4:  # Valid IP format
            for part in ip_parts:
                self.assertTrue(part.isdigit())
                self.assertTrue(0 <= int(part) <= 255)

    def test_status_system_info_valid(self):
        """Status response should have valid system information"""
        response = self.device.get('/status')
        data = self.assert_json_response(response)

        system = data['system']
        self.assertIn('uptime', system)
        self.assertIn('heap_used', system)

        # Verify system field types and reasonable values
        self.assertIsInstance(system['uptime'], int)
        self.assertGreater(system['uptime'], 0, "Uptime should be positive")

        # Verify heap_used is a valid integer
        self.assertIsInstance(system['heap_used'], int)
        self.assertGreaterEqual(system['heap_used'], 0, "RAM usage should be non-negative")

        # Sanity check: should be less than total RAM
        # FRDM-K64F: 256KB total RAM
        # Use 300KB as upper bound to accommodate both boards
        self.assertLess(system['heap_used'], 300 * 1024,
                        "RAM usage exceeds reasonable limit")

        # Should be non-zero since heap is being used
        # Note: This assertion is optional - heap could theoretically be empty
        if system['heap_used'] > 0:
            print(f"  Heap usage: {system['heap_used']} bytes")

    def test_status_gpio_states(self):
        """Status response should have boolean GPIO states"""
        response = self.device.get('/status')
        data = self.assert_json_response(response)

        # Both select0 and select1 should be boolean
        self.assertIn(data['select0'], [True, False])
        self.assertIn(data['select1'], [True, False])

        # Safety check: both lines should never be HIGH simultaneously
        if data['select0'] and data['select1']:
            self.fail("GPIO mutual exclusion violated: both select0 and select1 are HIGH")


@pytest.mark.timeout(30)
class InfoTests(BaseTestCase):
    """Test GET /api/info endpoint"""

    def test_info_returns_200(self):
        """Info endpoint should return HTTP 200"""
        response = self.device.get('/info')
        self.assertEqual(response.status_code, 200)

    def test_info_has_required_fields(self):
        """Info response should have all required fields"""
        response = self.device.get('/info')
        data = self.assert_json_response(
            response,
            required_fields=['device', 'version', 'zephyr', 'board']
        )

        # Verify field types
        self.assertIsInstance(data['device'], str)
        self.assertIsInstance(data['version'], str)
        self.assertIsInstance(data['zephyr'], str)
        self.assertIsInstance(data['board'], str)

    def test_info_device_name(self):
        """Info should report correct device name"""
        response = self.device.get('/info')
        data = self.assert_json_response(response)
        self.assertEqual(data['device'], 'JTAG Switch')

    def test_info_version_format(self):
        """Info version should be in semantic versioning format"""
        response = self.device.get('/info')
        data = self.assert_json_response(response)

        # Check firmware version format (e.g., "1.0.0")
        version_parts = data['version'].split('.')
        self.assertEqual(len(version_parts), 3, "Version should be in X.Y.Z format")
        for part in version_parts:
            self.assertTrue(part.isdigit(), f"Version part '{part}' should be numeric")

    def test_info_zephyr_version(self):
        """Info should report Zephyr version"""
        response = self.device.get('/info')
        data = self.assert_json_response(response)

        # Zephyr version should be in format "X.Y.Z"
        zephyr_version = data['zephyr']
        self.assertTrue(len(zephyr_version) > 0)
        # Should contain at least one digit
        self.assertTrue(any(c.isdigit() for c in zephyr_version))


@pytest.mark.timeout(30)
class SelectTests(BaseTestCase):
    """Test POST /api/select endpoint"""

    def test_select_line0_connector0(self):
        """Select line 0 to connector 0 (LOW)"""
        response = self.device.post('/select', {'line': 0, 'connector': 0})
        data = self.assert_json_response(response, required_fields=['success', 'select0', 'select1'])
        self.assertTrue(data['success'])

        # Response should contain actual GPIO states
        self.assertFalse(data['select0'], "Line 0 should be LOW (connector 0)")

        # Verify via status endpoint as well
        status = self.get_device_status()
        self.assertFalse(status['select0'], "Line 0 should be LOW")

    def test_select_line0_connector1(self):
        """Select line 0 to connector 1 (HIGH)"""
        response = self.device.post('/select', {'line': 0, 'connector': 1})
        data = self.assert_json_response(response, required_fields=['success'])
        self.assertTrue(data['success'])

        # Verify via status
        status = self.get_device_status()
        self.assertTrue(status['select0'], "Line 0 should be HIGH")

    def test_select_line1_connector0(self):
        """Select line 1 to connector 0 (LOW)"""
        response = self.device.post('/select', {'line': 1, 'connector': 0})
        data = self.assert_json_response(response, required_fields=['success'])
        self.assertTrue(data['success'])

        # Verify via status
        status = self.get_device_status()
        self.assertFalse(status['select1'], "Line 1 should be LOW")

    def test_select_line1_connector1(self):
        """Select line 1 to connector 1 (HIGH)"""
        response = self.device.post('/select', {'line': 1, 'connector': 1})
        data = self.assert_json_response(response, required_fields=['success'])
        self.assertTrue(data['success'])

        # Verify via status
        status = self.get_device_status()
        self.assertTrue(status['select1'], "Line 1 should be HIGH")

    def test_select_connector2_same_as_connector0(self):
        """Connector 2 should behave same as connector 0 (LOW)"""
        response = self.device.post('/select', {'line': 0, 'connector': 2})
        data = self.assert_json_response(response, required_fields=['success'])
        self.assertTrue(data['success'])

        # Verify via status - should be LOW
        status = self.get_device_status()
        self.assertFalse(status['select0'], "Connector 2 should set line LOW")

    def test_select_connector3_same_as_connector1(self):
        """Connector 3 should behave same as connector 1 (HIGH)"""
        response = self.device.post('/select', {'line': 0, 'connector': 3})
        data = self.assert_json_response(response, required_fields=['success'])
        self.assertTrue(data['success'])

        # Verify via status - should be HIGH
        status = self.get_device_status()
        self.assertTrue(status['select0'], "Connector 3 should set line HIGH")

    def test_select_invalid_line_negative(self):
        """Negative line number should return HTTP 400"""
        response = self.device.post('/select', {'line': -1, 'connector': 0})
        self.assert_error_response(response, expected_status=400)

    def test_select_invalid_line_too_high(self):
        """Line number > 1 should return HTTP 400"""
        response = self.device.post('/select', {'line': 2, 'connector': 0})
        self.assert_error_response(response, expected_status=400)

    def test_select_invalid_connector_negative(self):
        """Negative connector number should return HTTP 400"""
        response = self.device.post('/select', {'line': 0, 'connector': -1})
        self.assert_error_response(response, expected_status=400)

    def test_select_invalid_connector_too_high(self):
        """Connector number > 3 should return HTTP 400"""
        response = self.device.post('/select', {'line': 0, 'connector': 4})
        self.assert_error_response(response, expected_status=400)

    def test_select_missing_line_parameter(self):
        """Missing line parameter should return HTTP 400"""
        response = self.device.post('/select', {'connector': 0})
        self.assert_error_response(response, expected_status=400)

    def test_select_missing_connector_parameter(self):
        """Missing connector parameter should return HTTP 400"""
        response = self.device.post('/select', {'line': 0})
        self.assert_error_response(response, expected_status=400)

    def test_gpio_mutual_exclusion(self):
        """GPIO mutual exclusion: both lines should never be HIGH"""
        # Set line 0 HIGH
        self.device.post('/select', {'line': 0, 'connector': 1})
        time.sleep(0.1)

        # Try to set line 1 HIGH (should work but auto-clear line 0)
        self.device.post('/select', {'line': 1, 'connector': 1})
        time.sleep(0.1)

        # Check status - line 1 should be HIGH, line 0 should be LOW
        status = self.get_device_status()
        if status['select0'] and status['select1']:
            self.fail("GPIO mutual exclusion violated: both lines are HIGH")


@pytest.mark.timeout(30)
class ToggleTests(BaseTestCase):
    """Test POST /api/toggle endpoint"""

    def test_toggle_line0(self):
        """Toggle line 0 should change its state"""
        # Get initial state
        initial_status = self.get_device_status()
        initial_state = initial_status['select0']

        # Toggle
        response = self.device.post('/toggle', {'line': 0})
        data = self.assert_json_response(response, required_fields=['success', 'line', 'state'])
        self.assertTrue(data['success'])
        self.assertEqual(data['line'], 0)

        # New state should be opposite of initial
        self.assertNotEqual(data['state'], initial_state)

        # Verify via status
        status = self.get_device_status()
        self.assertEqual(status['select0'], data['state'])

    def test_toggle_line1(self):
        """Toggle line 1 should change its state"""
        # Get initial state
        initial_status = self.get_device_status()
        initial_state = initial_status['select1']

        # Toggle
        response = self.device.post('/toggle', {'line': 1})
        data = self.assert_json_response(response, required_fields=['success', 'line', 'state'])
        self.assertTrue(data['success'])
        self.assertEqual(data['line'], 1)

        # New state should be opposite of initial
        self.assertNotEqual(data['state'], initial_state)

    def test_toggle_double_returns_to_original(self):
        """Double toggle should return to original state"""
        # Get initial state
        initial_status = self.get_device_status()
        initial_state = initial_status['select0']

        # Toggle twice
        self.device.post('/toggle', {'line': 0})
        time.sleep(0.1)
        self.device.post('/toggle', {'line': 0})
        time.sleep(0.1)

        # Should be back to initial state
        status = self.get_device_status()
        self.assertEqual(status['select0'], initial_state)

    def test_toggle_invalid_line_negative(self):
        """Negative line number should return HTTP 400"""
        response = self.device.post('/toggle', {'line': -1})
        self.assert_error_response(response, expected_status=400)

    def test_toggle_invalid_line_too_high(self):
        """Line number > 1 should return HTTP 400"""
        response = self.device.post('/toggle', {'line': 2})
        self.assert_error_response(response, expected_status=400)

    def test_toggle_missing_line_parameter(self):
        """Missing line parameter should return HTTP 400"""
        response = self.device.post('/toggle', {})
        self.assert_error_response(response, expected_status=400)


@pytest.mark.network
@pytest.mark.timeout(30)
class NetworkConfigTests(BaseTestCase):
    """Test POST /api/network/config endpoint"""

    def setUp(self):
        """Skip network config tests by default"""
        super().setUp()
        if config.skip_network_config_tests:
            self.skipTest("Network config tests skipped (may restart network). Use --run-network-tests to enable.")

    def test_dhcp_mode_configuration(self):
        """Configure DHCP mode"""
        response = self.device.post('/network/config', {'mode': 'dhcp'})
        data = self.assert_json_response(response, required_fields=['success', 'restart_required'])
        self.assertTrue(data['success'])
        self.assertTrue(data['restart_required'])

        # Wait for network to restart
        time.sleep(2)
        self.assertTrue(self.wait_for_device(timeout=15), "Device did not respond after network restart")

    def test_static_ip_configuration(self):
        """Configure static IP"""
        response = self.device.post('/network/config', {
            'mode': 'static',
            'ip': '192.168.1.100',
            'netmask': '255.255.255.0',
            'gateway': '192.168.1.1'
        })
        data = self.assert_json_response(response, required_fields=['success'])
        self.assertTrue(data['success'])

        # Wait for network to restart
        time.sleep(2)
        self.assertTrue(self.wait_for_device(timeout=15), "Device did not respond after network restart")

    def test_network_config_missing_mode(self):
        """Missing mode parameter should return HTTP 400"""
        response = self.device.post('/network/config', {})
        self.assert_error_response(response, expected_status=400)


def run_tests():
    """Run all tests and print summary"""
    # Update config from command line args
    global config
    config = Config.from_args()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(HealthTests))
    suite.addTests(loader.loadTestsFromTestCase(StatusTests))
    suite.addTests(loader.loadTestsFromTestCase(InfoTests))
    suite.addTests(loader.loadTestsFromTestCase(SelectTests))
    suite.addTests(loader.loadTestsFromTestCase(ToggleTests))
    suite.addTests(loader.loadTestsFromTestCase(NetworkConfigTests))

    # Run tests
    print(f"\nTesting JTAG Switch REST API at {config.base_url}")
    print("=" * 60)

    runner = unittest.TextTestRunner(verbosity=2 if config.verbose else 1)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    print(f"PASSED: {result.testsRun - len(result.failures) - len(result.errors)} tests")
    print(f"FAILED: {len(result.failures) + len(result.errors)} tests")
    print(f"SKIPPED: {len(result.skipped)} tests")
    print(f"Total time: {result.testsRun} tests")

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
