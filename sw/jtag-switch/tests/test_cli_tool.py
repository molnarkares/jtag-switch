"""
Integration tests for JTAG Switch CLI tool

Tests the jtag-cli.py script including:
- Argument parsing with argparse subparsers
- Command dispatch to client methods
- Exit codes
- Error handling
- Output formatting
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add client library and CLI tool to path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), '../tools/jtag-switch-client')
sys.path.insert(0, CLIENT_DIR)

# Import CLI functions
from jtag_switch import JtagSwitchClient
import importlib.util

# Load jtag-cli.py as a module
cli_path = os.path.join(CLIENT_DIR, 'jtag-cli.py')
spec = importlib.util.spec_from_file_location("jtag_cli", cli_path)
jtag_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jtag_cli)


class TestArgumentParsing(unittest.TestCase):
    """Test CLI argument parsing"""

    def test_interface_required(self):
        """Test that --interface is required"""
        with self.assertRaises(SystemExit):
            with patch('sys.stderr', new=StringIO()):
                parser = jtag_cli.create_parser()
                parser.parse_args(['jtag', 'status'])

    def test_serial_interface_parsing(self):
        """Test parsing serial interface arguments"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args(['--interface', 'serial', 'jtag', 'status'])

        self.assertEqual(args.interface, 'serial')
        self.assertEqual(args.category, 'jtag')
        self.assertEqual(args.command, 'status')

    def test_rest_interface_parsing(self):
        """Test parsing REST interface arguments"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args(['--interface', 'rest', '--ip', '192.168.1.100', 'jtag', 'status'])

        self.assertEqual(args.interface, 'rest')
        self.assertEqual(args.ip, '192.168.1.100')
        self.assertEqual(args.category, 'jtag')
        self.assertEqual(args.command, 'status')

    def test_jtag_select_with_value(self):
        """Test parsing jtag select command with value"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args(['--interface', 'serial', 'jtag', 'select0', '1'])

        self.assertEqual(args.command, 'select0')
        self.assertEqual(args.value, 1)

    def test_jtag_select_invalid_value_rejected(self):
        """Test that invalid select values are rejected"""
        parser = jtag_cli.create_parser()

        with self.assertRaises(SystemExit):
            with patch('sys.stderr', new=StringIO()):
                parser.parse_args(['--interface', 'serial', 'jtag', 'select0', '5'])

    def test_net_set_static_with_arguments(self):
        """Test parsing net set static command"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args([
            '--interface', 'serial',
            'net', 'set', 'static',
            '192.168.1.100', '255.255.255.0', '192.168.1.1'
        ])

        self.assertEqual(args.category, 'net')
        self.assertEqual(args.command, 'set')
        self.assertEqual(args.subcommand, 'static')
        self.assertEqual(args.ip, '192.168.1.100')
        self.assertEqual(args.netmask, '255.255.255.0')
        self.assertEqual(args.gateway, '192.168.1.1')

    def test_verbose_flag_parsing(self):
        """Test parsing verbose flag"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args(['--interface', 'serial', '-v', 'jtag', 'status'])

        self.assertTrue(args.verbose)

    def test_serial_port_optional(self):
        """Test that --serial-port is optional"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args(['--interface', 'serial', 'jtag', 'status'])

        self.assertIsNone(args.serial_port)

    def test_serial_port_specified(self):
        """Test --serial-port parameter"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args([
            '--interface', 'serial',
            '--serial-port', '/dev/ttyACM0',
            'jtag', 'status'
        ])

        self.assertEqual(args.serial_port, '/dev/ttyACM0')

    def test_rest_port_default(self):
        """Test REST port defaults to 80"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args(['--interface', 'rest', '--ip', '192.168.1.100', 'jtag', 'status'])

        self.assertEqual(args.port, 80)

    def test_rest_port_custom(self):
        """Test custom REST port"""
        parser = jtag_cli.create_parser()
        args = parser.parse_args([
            '--interface', 'rest',
            '--ip', '192.168.1.100',
            '--port', '8080',
            'jtag', 'status'
        ])

        self.assertEqual(args.port, 8080)


class TestCommandExecution(unittest.TestCase):
    """Test command execution and dispatch"""

    def setUp(self):
        """Set up mock client"""
        self.mock_client = Mock(spec=JtagSwitchClient)
        parser = jtag_cli.create_parser()
        self.parser = parser

    def test_jtag_status_execution(self):
        """Test jtag status command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'status'])
        expected_result = {
            'success': True,
            'data': {'select0': 0, 'select1': 1},
            'message': 'Status OK'
        }
        self.mock_client.jtag_status.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.jtag_status.assert_called_once()

    def test_jtag_select0_execution(self):
        """Test jtag select0 command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'select0', '1'])
        expected_result = {'success': True, 'data': {}, 'message': 'Selected'}
        self.mock_client.jtag_select.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.jtag_select.assert_called_once_with(0, 1)

    def test_jtag_select1_execution(self):
        """Test jtag select1 command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'select1', '0'])
        expected_result = {'success': True, 'data': {}, 'message': 'Selected'}
        self.mock_client.jtag_select.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.jtag_select.assert_called_once_with(1, 0)

    def test_jtag_toggle0_execution(self):
        """Test jtag toggle0 command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'toggle0'])
        expected_result = {'success': True, 'data': {'state': 1}, 'message': 'Toggled'}
        self.mock_client.jtag_toggle.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.jtag_toggle.assert_called_once_with(0)

    def test_jtag_toggle1_execution(self):
        """Test jtag toggle1 command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'toggle1'])
        expected_result = {'success': True, 'data': {'state': 0}, 'message': 'Toggled'}
        self.mock_client.jtag_toggle.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.jtag_toggle.assert_called_once_with(1)

    def test_net_status_execution(self):
        """Test net status command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'net', 'status'])
        expected_result = {'success': True, 'data': {'mode': 'DHCP'}, 'message': 'Network status'}
        self.mock_client.net_status.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.net_status.assert_called_once()

    def test_net_set_dhcp_execution(self):
        """Test net set dhcp command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'net', 'set', 'dhcp'])
        expected_result = {'success': True, 'data': {}, 'message': 'DHCP enabled'}
        self.mock_client.net_set_dhcp.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.net_set_dhcp.assert_called_once()

    def test_net_set_static_execution(self):
        """Test net set static command execution"""
        args = self.parser.parse_args([
            '--interface', 'serial',
            'net', 'set', 'static',
            '192.168.1.100', '255.255.255.0', '192.168.1.1'
        ])
        expected_result = {'success': True, 'data': {}, 'message': 'Static IP set'}
        self.mock_client.net_set_static.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.net_set_static.assert_called_once_with(
            '192.168.1.100', '255.255.255.0', '192.168.1.1'
        )

    def test_device_info_execution(self):
        """Test device info command execution"""
        args = self.parser.parse_args(['--interface', 'serial', 'device', 'info'])
        # Board name is example mock data - actual device may be frdm_k64f, frdm_mcxc444, etc.
        expected_result = {
            'success': True,
            'data': {'device': 'JTAG Switch', 'board': 'test_board'},
            'message': 'Device info'
        }
        self.mock_client.device_info.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.device_info.assert_called_once()

    def test_health_check_execution(self):
        """Test health command execution"""
        args = self.parser.parse_args(['--interface', 'rest', '--ip', '192.168.1.100', 'health'])
        expected_result = {'success': True, 'data': {'status': 'ok'}, 'message': 'Healthy'}
        self.mock_client.health_check.return_value = expected_result

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)
        self.mock_client.health_check.assert_called_once()


class TestExitCodes(unittest.TestCase):
    """Test CLI exit codes"""

    def setUp(self):
        """Set up mock client and parser"""
        self.mock_client = Mock(spec=JtagSwitchClient)
        self.parser = jtag_cli.create_parser()

    def test_success_exit_code(self):
        """Test EXIT_SUCCESS for successful command"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'status'])
        self.mock_client.jtag_status.return_value = {
            'success': True,
            'data': {},
            'message': 'OK'
        }

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_SUCCESS)

    def test_command_failed_exit_code(self):
        """Test EXIT_COMMAND_FAILED for failed command"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'status'])
        self.mock_client.jtag_status.return_value = {
            'success': False,
            'data': {},
            'message': 'Failed'
        }

        exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_COMMAND_FAILED)

    def test_not_supported_exit_code(self):
        """Test EXIT_NOT_SUPPORTED for unsupported command"""
        from jtag_switch import CommandNotSupportedError

        args = self.parser.parse_args(['--interface', 'rest', '--ip', '192.168.1.100', 'net', 'config'])
        self.mock_client.net_config.side_effect = CommandNotSupportedError("Not supported")

        with patch('sys.stdout', new=StringIO()):
            exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_NOT_SUPPORTED)

    def test_command_execution_error_exit_code(self):
        """Test EXIT_COMMAND_FAILED for execution error"""
        from jtag_switch import CommandExecutionError

        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'status'])
        self.mock_client.jtag_status.side_effect = CommandExecutionError("Execution failed")

        with patch('sys.stdout', new=StringIO()):
            exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_COMMAND_FAILED)

    def test_invalid_usage_exit_code(self):
        """Test EXIT_INVALID_USAGE for invalid arguments"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'select0', '1'])
        self.mock_client.jtag_select.side_effect = ValueError("Invalid value")

        with patch('sys.stdout', new=StringIO()):
            exit_code = jtag_cli.execute_command(self.mock_client, args)

        self.assertEqual(exit_code, jtag_cli.EXIT_INVALID_USAGE)


class TestOutputFormatting(unittest.TestCase):
    """Test output formatting"""

    def setUp(self):
        """Set up mock client and parser"""
        self.mock_client = Mock(spec=JtagSwitchClient)
        self.parser = jtag_cli.create_parser()

    def test_normal_output(self):
        """Test normal output without verbose flag"""
        args = self.parser.parse_args(['--interface', 'serial', 'jtag', 'status'])
        self.mock_client.jtag_status.return_value = {
            'success': True,
            'data': {'select0': 0, 'select1': 1},
            'message': 'Status message'
        }

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            jtag_cli.execute_command(self.mock_client, args)
            output = mock_stdout.getvalue()

        self.assertIn('Status message', output)
        self.assertNotIn('Success:', output)
        self.assertNotIn('Data:', output)

    def test_verbose_output(self):
        """Test verbose output with -v flag"""
        args = self.parser.parse_args(['--interface', 'serial', '-v', 'jtag', 'status'])
        self.mock_client.jtag_status.return_value = {
            'success': True,
            'data': {'select0': 0, 'select1': 1},
            'message': 'Status message'
        }

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            jtag_cli.execute_command(self.mock_client, args)
            output = mock_stdout.getvalue()

        self.assertIn('Success: True', output)
        self.assertIn('Message: Status message', output)
        self.assertIn('Data:', output)
        self.assertIn('select0: 0', output)
        self.assertIn('select1: 1', output)


if __name__ == '__main__':
    unittest.main()
