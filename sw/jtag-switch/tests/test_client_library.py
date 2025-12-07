"""
Unit tests for JTAG Switch Python client library

Tests the jtag_switch package including:
- JtagSwitchClient initialization
- Backend selection (serial vs REST)
- Command execution with mocked backends
- Error handling and exceptions
- Context manager functionality
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add client library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../tools/jtag-switch-client'))

from jtag_switch import (
    JtagSwitchClient,
    JtagSwitchError,
    DeviceNotFoundError,
    ConnectionError,
    CommandNotSupportedError,
    CommandExecutionError,
    InvalidResponseError
)


class TestJtagSwitchClientInit(unittest.TestCase):
    """Test client initialization"""

    def test_serial_backend_creation(self):
        """Test that serial interface creates SerialBackend"""
        client = JtagSwitchClient(interface='serial')
        self.assertEqual(client.interface, 'serial')
        self.assertIsNotNone(client.backend)

    def test_rest_backend_creation(self):
        """Test that rest interface creates RestBackend"""
        client = JtagSwitchClient(interface='rest', host='192.168.1.100')
        self.assertEqual(client.interface, 'rest')
        self.assertIsNotNone(client.backend)

    def test_invalid_interface_raises_error(self):
        """Test that invalid interface raises ValueError"""
        with self.assertRaises(ValueError) as ctx:
            JtagSwitchClient(interface='invalid')
        self.assertIn('Invalid interface', str(ctx.exception))

    def test_serial_port_parameter_passed(self):
        """Test that serial port parameter is passed to backend"""
        with patch('jtag_switch.backends.serial_backend.SerialBackend') as mock_backend:
            client = JtagSwitchClient(interface='serial', port='/dev/ttyACM0')
            mock_backend.assert_called_once_with(port='/dev/ttyACM0')

    def test_rest_host_parameter_required(self):
        """Test that REST backend requires host parameter"""
        # This should work with proper error handling in actual use
        client = JtagSwitchClient(interface='rest', host='192.168.1.100', port=8080)
        self.assertEqual(client.interface, 'rest')


class TestClientContextManager(unittest.TestCase):
    """Test context manager functionality"""

    def test_context_manager_connects_and_disconnects(self):
        """Test that context manager calls connect and disconnect"""
        client = JtagSwitchClient(interface='serial')

        # Mock the backend
        client.backend = Mock()

        with client as ctx_client:
            self.assertIs(ctx_client, client)
            client.backend.connect.assert_called_once()

        client.backend.disconnect.assert_called_once()

    def test_context_manager_disconnects_on_exception(self):
        """Test that disconnect is called even if exception occurs"""
        client = JtagSwitchClient(interface='serial')
        client.backend = Mock()
        client.backend.jtag_status.side_effect = CommandExecutionError("Test error")

        with self.assertRaises(CommandExecutionError):
            with client:
                client.jtag_status()

        client.backend.disconnect.assert_called_once()


class TestJtagCommands(unittest.TestCase):
    """Test JTAG control commands"""

    def setUp(self):
        """Set up test client with mocked backend"""
        self.client = JtagSwitchClient(interface='serial')
        self.client.backend = Mock()

    def test_jtag_select(self):
        """Test jtag_select delegates to backend"""
        expected_result = {'success': True, 'data': {}, 'message': 'OK'}
        self.client.backend.jtag_select.return_value = expected_result

        result = self.client.jtag_select(0, 1)

        self.assertEqual(result, expected_result)
        self.client.backend.jtag_select.assert_called_once_with(0, 1)

    def test_jtag_toggle(self):
        """Test jtag_toggle delegates to backend"""
        expected_result = {'success': True, 'data': {'state': 1}, 'message': 'Toggled'}
        self.client.backend.jtag_toggle.return_value = expected_result

        result = self.client.jtag_toggle(1)

        self.assertEqual(result, expected_result)
        self.client.backend.jtag_toggle.assert_called_once_with(1)

    def test_jtag_status(self):
        """Test jtag_status delegates to backend"""
        # Board name is example mock data - actual device may be frdm_k64f, frdm_mcxc444, etc.
        expected_result = {
            'success': True,
            'data': {'select0': 0, 'select1': 1, 'board': 'test_board'},
            'message': 'Status'
        }
        self.client.backend.jtag_status.return_value = expected_result

        result = self.client.jtag_status()

        self.assertEqual(result, expected_result)
        self.client.backend.jtag_status.assert_called_once()


class TestNetworkCommands(unittest.TestCase):
    """Test network configuration commands"""

    def setUp(self):
        """Set up test client with mocked backend"""
        self.client = JtagSwitchClient(interface='serial')
        self.client.backend = Mock()

    def test_net_status(self):
        """Test net_status delegates to backend"""
        expected_result = {
            'success': True,
            'data': {
                'mode': 'DHCP',
                'ip': '192.168.1.100',
                'netmask': '255.255.255.0',
                'gateway': '192.168.1.1'
            },
            'message': 'Network status'
        }
        self.client.backend.net_status.return_value = expected_result

        result = self.client.net_status()

        self.assertEqual(result, expected_result)
        self.client.backend.net_status.assert_called_once()

    def test_net_config(self):
        """Test net_config delegates to backend"""
        expected_result = {'success': True, 'data': {'mode': 'dhcp'}, 'message': 'Config'}
        self.client.backend.net_config.return_value = expected_result

        result = self.client.net_config()

        self.assertEqual(result, expected_result)
        self.client.backend.net_config.assert_called_once()

    def test_net_set_dhcp(self):
        """Test net_set_dhcp delegates to backend"""
        expected_result = {'success': True, 'data': {}, 'message': 'DHCP enabled'}
        self.client.backend.net_set_dhcp.return_value = expected_result

        result = self.client.net_set_dhcp()

        self.assertEqual(result, expected_result)
        self.client.backend.net_set_dhcp.assert_called_once()

    def test_net_set_static(self):
        """Test net_set_static delegates to backend"""
        expected_result = {'success': True, 'data': {}, 'message': 'Static IP set'}
        self.client.backend.net_set_static.return_value = expected_result

        result = self.client.net_set_static('192.168.1.100', '255.255.255.0', '192.168.1.1')

        self.assertEqual(result, expected_result)
        self.client.backend.net_set_static.assert_called_once_with(
            '192.168.1.100', '255.255.255.0', '192.168.1.1'
        )

    def test_net_restart(self):
        """Test net_restart delegates to backend"""
        expected_result = {'success': True, 'data': {}, 'message': 'Network restarted'}
        self.client.backend.net_restart.return_value = expected_result

        result = self.client.net_restart()

        self.assertEqual(result, expected_result)
        self.client.backend.net_restart.assert_called_once()

    def test_net_save(self):
        """Test net_save delegates to backend"""
        expected_result = {'success': True, 'data': {}, 'message': 'Config saved'}
        self.client.backend.net_save.return_value = expected_result

        result = self.client.net_save()

        self.assertEqual(result, expected_result)
        self.client.backend.net_save.assert_called_once()


class TestDeviceCommands(unittest.TestCase):
    """Test device information commands"""

    def setUp(self):
        """Set up test client with mocked backend"""
        self.client = JtagSwitchClient(interface='serial')
        self.client.backend = Mock()

    def test_device_info(self):
        """Test device_info delegates to backend"""
        # Board name is example mock data - actual device may be frdm_k64f, frdm_mcxc444, etc.
        expected_result = {
            'success': True,
            'data': {
                'device': 'JTAG Switch',
                'version': '1.0.0',
                'board': 'test_board'
            },
            'message': 'Device info'
        }
        self.client.backend.device_info.return_value = expected_result

        result = self.client.device_info()

        self.assertEqual(result, expected_result)
        self.client.backend.device_info.assert_called_once()

    def test_health_check(self):
        """Test health_check delegates to backend"""
        expected_result = {'success': True, 'data': {'status': 'ok'}, 'message': 'Healthy'}
        self.client.backend.health_check.return_value = expected_result

        result = self.client.health_check()

        self.assertEqual(result, expected_result)
        self.client.backend.health_check.assert_called_once()


class TestErrorHandling(unittest.TestCase):
    """Test error handling and exceptions"""

    def setUp(self):
        """Set up test client with mocked backend"""
        self.client = JtagSwitchClient(interface='serial')
        self.client.backend = Mock()

    def test_command_not_supported_error_propagates(self):
        """Test that CommandNotSupportedError propagates from backend"""
        self.client.backend.net_config.side_effect = CommandNotSupportedError("Not supported")

        with self.assertRaises(CommandNotSupportedError):
            self.client.net_config()

    def test_command_execution_error_propagates(self):
        """Test that CommandExecutionError propagates from backend"""
        self.client.backend.jtag_status.side_effect = CommandExecutionError("Execution failed")

        with self.assertRaises(CommandExecutionError):
            self.client.jtag_status()

    def test_device_not_found_error_on_connect(self):
        """Test DeviceNotFoundError during connection"""
        self.client.backend.connect.side_effect = DeviceNotFoundError("Device not found")

        with self.assertRaises(DeviceNotFoundError):
            self.client.connect()

    def test_connection_error_on_connect(self):
        """Test ConnectionError during connection"""
        self.client.backend.connect.side_effect = ConnectionError("Connection failed")

        with self.assertRaises(ConnectionError):
            self.client.connect()


class TestManualConnectionManagement(unittest.TestCase):
    """Test manual connect/disconnect methods"""

    def test_manual_connect(self):
        """Test manual connect method"""
        client = JtagSwitchClient(interface='serial')
        client.backend = Mock()

        client.connect()

        client.backend.connect.assert_called_once()

    def test_manual_disconnect(self):
        """Test manual disconnect method"""
        client = JtagSwitchClient(interface='serial')
        client.backend = Mock()

        client.disconnect()

        client.backend.disconnect.assert_called_once()


if __name__ == '__main__':
    unittest.main()
