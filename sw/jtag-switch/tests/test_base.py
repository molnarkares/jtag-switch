"""
Base test classes and utilities for JTAG Switch testing

Provides:
- BaseTestCase: Common test utilities and setup/teardown
- DeviceConnection: Abstraction for device communication
- Helper functions for JSON validation and response checking
"""

import unittest
import requests
import json
import time
from typing import Optional, Dict, Any
from test_config import config


class DeviceConnection:
    """Manages connection to the JTAG Switch device"""

    def __init__(self, base_url: str, timeout: tuple = None):
        self.base_url = base_url
        self.timeout = timeout or (config.connect_timeout, config.read_timeout)
        self.session = requests.Session()

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Perform GET request"""
        url = f"{self.base_url}{endpoint}"
        if config.verbose:
            print(f"GET {url}")
        response = self.session.get(url, timeout=self.timeout, **kwargs)
        if config.verbose:
            print(f"  Status: {response.status_code}")
            if response.headers.get('Content-Type', '').startswith('application/json'):
                print(f"  Response: {response.text}")
        return response

    def post(self, endpoint: str, json_data: Dict[str, Any] = None, **kwargs) -> requests.Response:
        """Perform POST request with JSON data

        Args:
            endpoint: API endpoint path
            json_data: JSON data to send (can also pass as json= kwarg for compatibility)
            **kwargs: Additional arguments passed to requests.post
        """
        url = f"{self.base_url}{endpoint}"

        # Handle both json_data parameter and json= kwarg for compatibility
        payload = kwargs.pop('json', json_data)

        if config.verbose:
            print(f"POST {url}")
            if payload:
                print(f"  Data: {json.dumps(payload, indent=2)}")

        response = self.session.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=self.timeout,
            **kwargs
        )
        if config.verbose:
            print(f"  Status: {response.status_code}")
            if response.headers.get('Content-Type', '').startswith('application/json'):
                print(f"  Response: {response.text}")
        return response

    def close(self):
        """Close the session"""
        self.session.close()


class BaseTestCase(unittest.TestCase):
    """Base class for all JTAG Switch tests"""

    @classmethod
    def setUpClass(cls):
        """Set up test class - create device connection"""
        cls.device = DeviceConnection(config.api_url)
        cls.config = config

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.device.close()

    def setUp(self):
        """Set up individual test"""
        if config.verbose:
            print(f"\n{'='*60}")
            print(f"Running: {self.id()}")
            print(f"{'='*60}")

    def tearDown(self):
        """Clean up after individual test"""
        # Small delay between tests to avoid overwhelming the device
        time.sleep(0.1)

    def assert_json_response(
        self,
        response: requests.Response,
        expected_status: int = 200,
        required_fields: list = None
    ) -> Dict[str, Any]:
        """
        Assert that response is valid JSON with expected status

        Args:
            response: HTTP response object
            expected_status: Expected HTTP status code
            required_fields: List of required field names in JSON

        Returns:
            Parsed JSON data

        Raises:
            AssertionError: If validation fails
        """
        self.assertEqual(
            response.status_code,
            expected_status,
            f"Expected status {expected_status}, got {response.status_code}: {response.text}"
        )

        # Check content type
        content_type = response.headers.get('Content-Type', '')
        self.assertTrue(
            content_type.startswith('application/json'),
            f"Expected JSON content type, got {content_type}"
        )

        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON response: {e}\nResponse text: {response.text}")

        # Check required fields
        if required_fields:
            for field in required_fields:
                self.assertIn(
                    field,
                    data,
                    f"Missing required field '{field}' in response: {data}"
                )

        return data

    def assert_error_response(
        self,
        response: requests.Response,
        expected_status: int = 400
    ) -> Dict[str, Any]:
        """
        Assert that response is an error with expected status

        Args:
            response: HTTP response object
            expected_status: Expected HTTP error status code

        Returns:
            Parsed JSON error data
        """
        data = self.assert_json_response(response, expected_status)
        self.assertIn('error', data, f"Error response missing 'error' field: {data}")
        return data

    def get_device_status(self) -> Dict[str, Any]:
        """
        Get current device status

        Returns:
            Device status as dictionary
        """
        response = self.device.get('/status')
        return self.assert_json_response(
            response,
            required_fields=['select0', 'select1', 'network', 'system']
        )

    def wait_for_device(self, timeout: int = 10) -> bool:
        """
        Wait for device to become responsive

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if device is responsive, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.device.get('/health')
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(0.5)
        return False


class SerialTestCase(BaseTestCase):
    """
    Base class for serial port tests (future use)

    Provides serial communication utilities for testing
    shell commands via USB CDC ACM interface
    """

    serial_port = None

    @classmethod
    def setUpClass(cls):
        """Set up serial connection"""
        super().setUpClass()
        # NOTE: This class is currently unused. Serial tests (test_serial_shell.py)
        # implement their own serial connection handling using serial_utils.py.
        # This class may be removed or updated in the future if a common base is needed.
        # import serial
        # cls.serial_port = serial.Serial(
        #     config.serial_port,
        #     baudrate=config.serial_baudrate,
        #     timeout=2
        # )

    @classmethod
    def tearDownClass(cls):
        """Close serial connection"""
        if cls.serial_port:
            cls.serial_port.close()
        super().tearDownClass()
