"""
Configuration for JTAG Switch Test Suite

This module centralizes all test configuration parameters including:
- Device network settings (IP, port)
- Serial port configuration (for shell testing)
- Web UI browser settings (headless testing)
- Timeout and retry settings
- Test execution options
"""

import argparse
import os


class Config:
    """Test configuration with sensible defaults"""

    # Network configuration
    device_ip = os.environ.get('JTAG_DEVICE_IP', '192.168.1.100')
    http_port = int(os.environ.get('JTAG_HTTP_PORT', '80'))

    # Serial configuration
    serial_auto_detect = True  # Auto-detect USB device by product string
    serial_port = os.environ.get('JTAG_SERIAL_PORT', None)  # Override auto-detect if set
    serial_baudrate = 115200
    serial_timeout = 2.0  # seconds

    # Web UI configuration
    web_ui_url_override = None  # Override web UI base URL (None = use base_url)
    browser_headless = True  # Run browser in headless mode
    browser_type = 'chromium'  # Browser choice: chromium, firefox, webkit
    browser_slow_mo = 0  # Slow down browser operations by N ms (debugging)
    screenshot_dir = 'screenshots'  # Directory for failure screenshots
    screenshot_on_failure = True  # Auto-screenshot on test failure
    page_load_timeout = 30000  # Page load timeout (milliseconds)
    element_timeout = 5000  # Element wait timeout (milliseconds)
    websocket_timeout = 10.0  # WebSocket connection timeout (seconds)

    # HTTP timeouts
    connect_timeout = 5  # seconds
    read_timeout = 10    # seconds

    # Test execution
    skip_network_config_tests = True  # Skip tests that restart network by default
    skip_serial_tests = False  # Auto-skip if hardware unavailable
    skip_web_ui_tests = False  # Skip web UI tests
    verbose = False

    @property
    def base_url(self):
        """Base URL for REST API"""
        return f"http://{self.device_ip}:{self.http_port}"

    @property
    def api_url(self):
        """API base URL"""
        return f"{self.base_url}/api"

    @property
    def web_ui_url(self):
        """Web UI base URL"""
        return self.web_ui_url_override or self.base_url

    @classmethod
    def from_args(cls, args=None):
        """Create config from command line arguments"""
        parser = argparse.ArgumentParser(
            description='JTAG Switch REST API Test Suite'
        )
        parser.add_argument(
            '--ip',
            default=cls.device_ip,
            help=f'Device IP address (default: {cls.device_ip})'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=cls.http_port,
            help=f'HTTP port (default: {cls.http_port})'
        )
        parser.add_argument(
            '--serial-port',
            default=None,
            help='Override serial port auto-detection (e.g., /dev/ttyACM0, COM3)'
        )
        parser.add_argument(
            '--skip-serial',
            action='store_true',
            help='Skip serial port tests'
        )
        parser.add_argument(
            '-v', '--verbose',
            action='store_true',
            help='Verbose output'
        )
        parser.add_argument(
            '--run-network-tests',
            action='store_true',
            help='Run network configuration tests (may restart device network)'
        )
        parser.add_argument(
            '--browser',
            choices=['chromium', 'firefox', 'webkit'],
            default='chromium',
            help='Browser type for web UI tests (default: chromium)'
        )
        parser.add_argument(
            '--headed',
            action='store_true',
            help='Run browser in headed mode (show UI for debugging)'
        )
        parser.add_argument(
            '--slow-mo',
            type=int,
            default=0,
            help='Slow down browser operations by N milliseconds (debugging)'
        )
        parser.add_argument(
            '--skip-web-ui',
            action='store_true',
            help='Skip web UI tests'
        )

        parsed_args = parser.parse_args(args)

        config = cls()
        config.device_ip = parsed_args.ip
        config.http_port = parsed_args.port
        config.verbose = parsed_args.verbose
        config.skip_network_config_tests = not parsed_args.run_network_tests
        config.skip_serial_tests = parsed_args.skip_serial
        config.skip_web_ui_tests = parsed_args.skip_web_ui

        # Serial port configuration
        if parsed_args.serial_port:
            config.serial_port = parsed_args.serial_port
            config.serial_auto_detect = False  # Disable auto-detect when manual port specified
        else:
            config.serial_auto_detect = True  # Use auto-detection

        # Web UI browser configuration
        config.browser_type = parsed_args.browser
        config.browser_headless = not parsed_args.headed  # --headed disables headless mode
        config.browser_slow_mo = parsed_args.slow_mo

        return config


# Global config instance
config = Config()
