#!/usr/bin/env python3
"""
JTAG Switch Command-Line Interface

Control JTAG Switch device via USB serial or REST API from the command line.
"""

import sys
import argparse
from jtag_switch import (
    JtagSwitchClient,
    DeviceNotFoundError,
    ConnectionError,
    CommandNotSupportedError,
    CommandExecutionError
)


# Exit codes
EXIT_SUCCESS = 0
EXIT_COMMAND_FAILED = 1
EXIT_DEVICE_NOT_FOUND = 2
EXIT_CONNECTION_ERROR = 3
EXIT_NOT_SUPPORTED = 4
EXIT_INVALID_USAGE = 5
EXIT_UNEXPECTED = 99


def create_parser():
    """Create argument parser with command hierarchy."""
    parser = argparse.ArgumentParser(
        description='JTAG Switch CLI - Control JTAG switch device',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Serial interface (auto-detect)
  %(prog)s --interface serial jtag status
  %(prog)s --interface serial jtag select0 1
  %(prog)s --interface serial net status

  # Serial interface (specific port)
  %(prog)s --interface serial --serial-port /dev/ttyACM0 jtag status

  # REST API interface
  %(prog)s --interface rest --ip 192.168.1.100 jtag status
  %(prog)s --interface rest --ip 192.168.1.100 jtag toggle0
  %(prog)s --interface rest --ip 192.168.1.100 net set dhcp
        '''
    )

    # Global options
    parser.add_argument(
        '--interface',
        choices=['serial', 'rest'],
        required=True,
        help='Communication interface (serial or rest)'
    )
    parser.add_argument(
        '--serial-port',
        help='Serial port path (e.g., /dev/ttyACM0). Auto-detect if not specified.'
    )
    parser.add_argument(
        '--ip',
        help='Device IP address (required for REST interface)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=80,
        help='HTTP port (default: 80, for REST interface)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output with full result dictionary'
    )

    # Command subparsers
    subparsers = parser.add_subparsers(dest='category', required=True, help='Command category')

    # JTAG commands
    jtag = subparsers.add_parser('jtag', help='JTAG control commands')
    jtag_cmds = jtag.add_subparsers(dest='command', required=True, help='JTAG command')

    jtag_cmds.add_parser('status', help='Get JTAG GPIO status')
    jtag_cmds.add_parser('toggle0', help='Toggle JTAG select line 0')
    jtag_cmds.add_parser('toggle1', help='Toggle JTAG select line 1')

    select0 = jtag_cmds.add_parser('select0', help='Set JTAG select line 0')
    select0.add_argument('value', type=int, choices=[0, 1], help='Value to set (0 or 1)')

    select1 = jtag_cmds.add_parser('select1', help='Set JTAG select line 1')
    select1.add_argument('value', type=int, choices=[0, 1], help='Value to set (0 or 1)')

    # Network commands
    net = subparsers.add_parser('net', help='Network configuration commands')
    net_cmds = net.add_subparsers(dest='command', required=True, help='Network command')

    net_cmds.add_parser('status', help='Get network status')
    net_cmds.add_parser('config', help='Get network configuration')
    net_cmds.add_parser('restart', help='Restart network interface')
    net_cmds.add_parser('save', help='Save network configuration to NVS')

    # Network set commands
    net_set = net_cmds.add_parser('set', help='Set network configuration')
    net_set_cmds = net_set.add_subparsers(dest='subcommand', required=True, help='Network mode')

    net_set_cmds.add_parser('dhcp', help='Enable DHCP mode')

    static = net_set_cmds.add_parser('static', help='Set static IP configuration')
    static.add_argument('ip', help='IP address (e.g., 192.168.1.100)')
    static.add_argument('netmask', help='Network mask (e.g., 255.255.255.0)')
    static.add_argument('gateway', help='Gateway address (e.g., 192.168.1.1)')

    # Device commands
    device = subparsers.add_parser('device', help='Device information commands')
    device_cmds = device.add_subparsers(dest='command', required=True, help='Device command')
    device_cmds.add_parser('info', help='Get device information')

    # Health command
    subparsers.add_parser('health', help='Check device health (REST only)')

    return parser


def execute_command(client, args):
    """
    Execute command via client.

    Args:
        client: JtagSwitchClient instance
        args: Parsed arguments from argparse

    Returns:
        exit_code: Integer exit code
    """
    try:
        result = None

        # Dispatch based on category
        if args.category == 'jtag':
            if args.command == 'status':
                result = client.jtag_status()
            elif args.command == 'select0':
                result = client.jtag_select(0, args.value)
            elif args.command == 'select1':
                result = client.jtag_select(1, args.value)
            elif args.command == 'toggle0':
                result = client.jtag_toggle(0)
            elif args.command == 'toggle1':
                result = client.jtag_toggle(1)

        elif args.category == 'net':
            if args.command == 'status':
                result = client.net_status()
            elif args.command == 'config':
                result = client.net_config()
            elif args.command == 'set':
                if args.subcommand == 'dhcp':
                    result = client.net_set_dhcp()
                elif args.subcommand == 'static':
                    result = client.net_set_static(args.ip, args.netmask, args.gateway)
            elif args.command == 'restart':
                result = client.net_restart()
            elif args.command == 'save':
                result = client.net_save()

        elif args.category == 'device':
            if args.command == 'info':
                result = client.device_info()

        elif args.category == 'health':
            result = client.health_check()

        # Output result
        if result:
            if args.verbose:
                print(f"Success: {result['success']}")
                print(f"Message: {result['message']}")
                if result.get('data'):
                    print("Data:")
                    for key, value in result['data'].items():
                        print(f"  {key}: {value}")
            else:
                print(result['message'])

            return EXIT_SUCCESS if result['success'] else EXIT_COMMAND_FAILED
        else:
            return EXIT_COMMAND_FAILED

    except ValueError as e:
        print(f"Error: Invalid argument - {e}")
        return EXIT_INVALID_USAGE
    except CommandNotSupportedError as e:
        print(f"Error: {e}")
        return EXIT_NOT_SUPPORTED
    except CommandExecutionError as e:
        print(f"Error: {e}")
        return EXIT_COMMAND_FAILED
    except Exception as e:
        print(f"Unexpected error: {e}")
        return EXIT_UNEXPECTED


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate interface-specific requirements
    if args.interface == 'rest' and not args.ip:
        parser.error('--ip is required when using REST interface')

    try:
        # Build client kwargs based on interface
        client_kwargs = {}
        if args.interface == 'serial':
            if args.serial_port:
                client_kwargs['port'] = args.serial_port
        elif args.interface == 'rest':
            client_kwargs['host'] = args.ip
            client_kwargs['port'] = args.port

        # Connect and execute command
        with JtagSwitchClient(interface=args.interface, **client_kwargs) as client:
            exit_code = execute_command(client, args)
            sys.exit(exit_code)

    except DeviceNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(EXIT_DEVICE_NOT_FOUND)
    except ConnectionError as e:
        print(f"Error: {e}")
        sys.exit(EXIT_CONNECTION_ERROR)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(EXIT_UNEXPECTED)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(EXIT_UNEXPECTED)


if __name__ == '__main__':
    main()
