# JTAG Switch Test Suite

Comprehensive Python-based test framework for verifying JTAG Switch REST API endpoints, serial shell commands, and web UI functionality.
Limited set of tests can run on simulated node.    

## Features

- **Comprehensive Coverage**: 62 test cases across REST API, serial shell, and web UI
- **HTTP API Testing**: 27 tests for REST API endpoints with JSON validation
- **Serial Shell Testing**: 15 tests for USB CDC ACM serial shell commands
- **Web UI Testing**: 20 tests for browser-based UI with Playwright (headless)
- **Auto-Discovery**: USB device detection by product string
- **Auto-Skip**: Tests gracefully skip when dependencies/hardware unavailable
- **Error Testing**: Tests invalid inputs and edge cases
- **GPIO Safety**: Verifies mutual exclusion constraints
- **Real-Time Updates**: WebSocket synchronization testing
- **Screenshot Capture**: Auto-screenshot on web UI test failures
- **Flexible**: Configurable via environment variables and command-line arguments

## Test Coverage

### HealthTests (2 tests)
- GET /api/health connectivity and response format

### StatusTests (4 tests)
- GET /api/status response structure and validation
- Network information verification
- System information validation
- GPIO state checking

### InfoTests (5 tests)
- GET /api/info device information
- Version format validation
- Zephyr version verification

### SelectTests (13 tests)
- POST /api/select for all valid combinations (line 0-1, connector 0-3)
- Invalid parameter testing (negative, out of range)
- Missing parameter handling
- GPIO mutual exclusion verification

### ToggleTests (6 tests)
- POST /api/toggle for both lines
- State change verification
- Double-toggle testing
- Invalid parameter handling

### NetworkConfigTests (2 tests, skipped by default)
- POST /api/network/config for DHCP and static IP
- **Note**: These tests restart the network and are skipped by default

**HTTP API Total**: 27 test cases (25 run by default, 2 skipped)

### Serial Shell Tests (15 tests, auto-skip if unavailable)

**File:** `test_serial_shell.py`

Tests shell commands via USB CDC ACM serial interface. Automatically skips if device not found or dependencies missing.

#### JtagCommandTests (12 tests)
- `jtag select0 <0|1>` - Set select line 0 (valid values, error cases)
- `jtag select1 <0|1>` - Set select line 1 (valid values, error cases)
- `jtag toggle0` - Toggle select line 0
- `jtag toggle1` - Toggle select line 1
- `jtag status` - Display status (output format, state reflection)
- Error handling: Invalid arguments, missing parameters, invalid subcommands

#### NetworkCommandTests (3 tests)
- `net status` - Network status display (output format, IP validation)
- `net config` - Configuration display
- **Note**: Does NOT test `net set`, `net restart`, `net save` (excluded per requirements)

**Serial Tests Total**: 15 test cases (auto-skip if hardware unavailable)

### Web UI Tests (20 tests, auto-skip if Playwright missing)

**File:** `test_web_ui.py`

Automated browser testing of the web UI using Playwright headless browser. Tests UI interactions, state synchronization, and real-time WebSocket updates.

#### PageLoadTests (4 tests)
- Page loads successfully with correct title
- All main sections present (header, JTAG, network, system)
- WebSocket connects and status shows "Connected"
- Initial JTAG line states displayed

#### JtagControlTests (10 tests) - **HIGH PRIORITY**
- Line 0/1 Enable/Disable/Toggle button functionality
- State updates in UI badges after button clicks
- Both lines controllable independently
- Button clicks trigger REST API requests
- State persists after page refresh

#### WebSocketRealtimeTests (6 tests) - **HIGH PRIORITY**
- WebSocket connection establishes on page load
- Line 0/1 states sync when changed via external REST API
- WebSocket status message format verification
- Connection status indicator accuracy
- Auto-reconnect after disconnection

**Web UI Tests Total**: 20 test cases (auto-skip if Playwright missing)

**Grand Total**: 62 test cases (60 run by default + 2 skipped HTTP network tests)

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager
- Network access to JTAG Switch device (default: 192.168.1.100) for HTTP tests
- USB connection to JTAG Switch for serial tests (optional)

### Full Installation (HTTP + Serial Tests)

```bash
cd sw/jtag-switch/tests

# Install Python dependencies
pip install -r requirements.txt

# Linux: Install system dependencies for USB
sudo apt-get install libusb-1.0-0
sudo usermod -a -G dialout $USER
# Log out and back in for group changes to take effect

# macOS: Install libusb
brew install libusb

# Verify USB device detection
python3 -c "from serial_utils import find_jtag_switch_device; print(find_jtag_switch_device())"
```

### HTTP-Only Installation (No Serial Tests)

```bash
pip install requests pytest pytest-timeout colorama
```

Serial tests will automatically skip if dependencies missing.

### Web UI Testing Installation (Additional)

```bash
# Install Playwright Python package
pip install playwright

# Install browser binaries (~300MB download)
playwright install chromium

# Verify Playwright installation
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

Web UI tests will automatically skip if Playwright is not installed.

### Dependencies

- `requests` - HTTP client library
- `pytest` - Test framework
- `pytest-timeout` - Test timeout support
- `colorama` - Colored terminal output
- `pyserial` - Serial communication for shell tests
- `pyusb` - USB device enumeration for auto-detection
- `playwright` - Headless browser for web UI testing

## Usage

### Running HTTP API Tests

Run all HTTP tests (skips network config tests):
```bash
python test_rest_api.py
# or
pytest test_rest_api.py -v
```

Run specific test class:
```bash
pytest test_rest_api.py::SelectTests -v
```

Run specific test:
```bash
pytest test_rest_api.py::SelectTests::test_select_line0_connector0 -v
```

### Running Serial Shell Tests

Run all serial tests (auto-skips if device unavailable):
```bash
python test_serial_shell.py
# or
pytest test_serial_shell.py -v
```

Run specific serial test class:
```bash
pytest test_serial_shell.py::JtagCommandTests -v
```

Run specific serial test:
```bash
pytest test_serial_shell.py::JtagCommandTests::test_jtag_status_output_format -v
```

### Running Web UI Tests

Run all web UI tests (headless browser):
```bash
python test_web_ui.py
# or
pytest test_web_ui.py -v
```

Run specific web UI test class:
```bash
pytest test_web_ui.py::JtagControlTests -v
pytest test_web_ui.py::WebSocketRealtimeTests -v
```

Run with visible browser (for debugging):
```bash
pytest test_web_ui.py -v --headed
```

Run with slow motion (debugging):
```bash
pytest test_web_ui.py -v --headed --slow-mo 1000
```

Use different browser:
```bash
pytest test_web_ui.py -v --browser firefox
pytest test_web_ui.py -v --browser webkit
```

### Running All Tests Together

**Recommended**: Use the master test runner to run all 62 tests:
```bash
python test_all.py

# With verbose output
python test_all.py -v

# With headed browser for web UI
python test_all.py --headed

# Skip specific test suites
python test_all.py --skip-serial
python test_all.py --skip-web-ui
```

Run both HTTP and serial tests:
```bash
pytest test_rest_api.py test_serial_shell.py -v
```

Skip serial tests explicitly:
```bash
pytest test_rest_api.py test_serial_shell.py -v --skip-serial
```

### Command-Line Options

```bash
# Custom IP address
python test_all.py --ip 192.168.1.200

# Custom port
python test_all.py --port 8080

# Verbose output
python test_all.py -v

# Run network config tests (may restart device network)
python test_rest_api.py --run-network-tests

# Override serial port auto-detection
python test_all.py --serial-port /dev/ttyACM1

# Web UI browser options
python test_all.py --headed              # Show browser window
python test_all.py --browser firefox     # Use Firefox instead of Chromium
python test_all.py --slow-mo 500         # Slow down for debugging

# Skip specific test suites
python test_all.py --skip-serial
python test_all.py --skip-web-ui

# Combine options
python test_all.py --ip 192.168.1.150 -v --headed
```

### Environment Variables

Configure via environment variables (overridden by command-line args):

```bash
export JTAG_DEVICE_IP=192.168.1.100
export JTAG_HTTP_PORT=80
export JTAG_SERIAL_PORT=/dev/ttyACM0

python test_rest_api.py
```

## Test Output

### Sample Output (Success)

```
Testing JTAG Switch REST API at http://192.168.1.100
============================================================

HealthTests
  test_health_check_returns_200 ... ok
  test_health_response_format ... ok

StatusTests
  test_status_returns_200 ... ok
  test_status_has_required_fields ... ok
  test_status_network_info_valid ... ok
  test_status_system_info_valid ... ok
  test_status_gpio_states ... ok

SelectTests
  test_select_line0_connector0 ... ok
  test_select_line0_connector1 ... ok
  ...

============================================================
PASSED: 25 tests
FAILED: 0 tests
SKIPPED: 2 tests
Total time: 25 tests
```

### Sample Output (Failure)

```
FAIL: test_select_line0_connector0 (test_rest_api.SelectTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  ...
AssertionError: Line 0 should be LOW

============================================================
PASSED: 24 tests
FAILED: 1 tests
SKIPPED: 2 tests
```

## File Structure

```
tests/
├── requirements.txt      # Python dependencies
├── pytest.ini            # pytest configuration (timeouts, markers)
├── test_config.py        # Configuration management (HTTP, serial, web UI)
├── test_base.py          # Base classes and utilities (HTTP tests)
├── test_rest_api.py      # HTTP REST API test suite (27 tests)
├── serial_utils.py       # USB discovery and shell interaction utilities
├── test_serial_shell.py  # Serial shell command test suite (15 tests)
├── web_ui_utils.py       # Web UI utilities (browser session, page objects)
├── test_web_ui.py        # Web UI test suite (20 tests)
├── test_all.py           # Master test runner (all 62 tests)
├── screenshots/          # Auto-captured screenshots on failures
│   └── .gitignore       # Ignore screenshot files in git
└── README.md            # This file
```

## Configuration

### test_config.py

Centralized configuration with defaults:

```python
class Config:
    device_ip = '192.168.1.100'
    http_port = 80
    serial_auto_detect = True  # Auto-detect USB device
    serial_port = None  # Override auto-detect if set
    serial_baudrate = 115200
    serial_timeout = 2.0
    connect_timeout = 5
    read_timeout = 10
    skip_network_config_tests = True
    skip_serial_tests = False
```

### test_base.py

Provides base test classes:
- `BaseTestCase`: Common test utilities and assertions
- `DeviceConnection`: HTTP client abstraction
- `SerialTestCase`: Future serial testing support

## Extending the Test Suite

### Adding New REST API Tests

1. Create a new test class inheriting from `BaseTestCase`:

```python
class MyNewTests(BaseTestCase):
    def test_my_endpoint(self):
        response = self.device.get('/my/endpoint')
        data = self.assert_json_response(response)
        # Your assertions here
```

2. Add the class to the test suite in `run_tests()`:

```python
suite.addTests(loader.loadTestsFromTestCase(MyNewTests))
```

### Adding Serial Shell Tests

Serial testing is fully implemented in `test_serial_shell.py`. To add new tests:

```python
from test_serial_shell import SerialShellTestCase

class MySerialTests(SerialShellTestCase):
    def test_my_command(self):
        output = self.shell.execute_command("my command")
        self.assertIn("expected output", " ".join(output))
```

## Troubleshooting

### Device Not Responding

```bash
# Verify device is reachable
ping 192.168.1.100

# Check device is serving HTTP
curl http://192.168.1.100/api/health
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Test Timeouts

Increase timeouts in `test_config.py`:
```python
connect_timeout = 10
read_timeout = 20
```

### Serial Port Access

```bash
# Linux: Grant serial port permissions
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect

# Verify permissions
groups | grep dialout
```

### Serial Device Not Found

```bash
# Check if USB device is connected
lsusb | grep 2fe3:0001

# List available serial ports
ls -l /dev/ttyACM*

# Test USB device detection
python3 -c "from serial_utils import find_jtag_switch_device; print(find_jtag_switch_device())"

# Test manual serial connection
python3 -c "
import serial
s = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
s.write(b'\n')
print(s.read(100))
s.close()
"
```

### PyUSB Backend Not Found

```bash
# Linux
sudo apt-get install libusb-1.0-0

# macOS
brew install libusb

# Verify
python3 -c "import usb.core; print('PyUSB OK' if usb.core.find() is not None or True else 'No USB')"
```

## Timeout Handling

The test suite has comprehensive timeout protection to prevent hanging when devices are not responding:

### Global Timeout Configuration

All tests have a **30-second default timeout** configured in `pytest.ini`. Individual tests can override this using `@pytest.mark.timeout(seconds)`.

### Test-Specific Timeouts

- **REST API tests**: 30 seconds (default)
- **Serial tests**: 30 seconds per test
- **Web UI tests**: 60 seconds (browser operations are slower)

### Timeout Behavior

**When device is not responding:**
- HTTP tests: Fail after 5s connection timeout + 10s read timeout
- Serial tests: Raise `TimeoutError` if command doesn't complete in 2-3 seconds
- Web UI tests: Skip if device health check fails (saves browser startup time)

**When pytest timeout is exceeded:**
- Test is forcefully terminated
- Next test continues (isolation preserved)
- Prevents entire test suite from hanging

### Running Tests with Custom Timeouts

```bash
# Increase timeout for slow networks
pytest test_rest_api.py --timeout 60

# Disable timeout (not recommended)
pytest test_rest_api.py --timeout 0
```

### Debugging Timeout Issues

If tests are timing out:

1. **Verify device connectivity**:
   ```bash
   ping 192.168.1.100
   curl http://192.168.1.100/api/health
   ```

2. **Check serial port** (for serial tests):
   ```bash
   ls -l /dev/ttyACM*
   screen /dev/ttyACM0 115200  # Exit with Ctrl-A, K
   ```

3. **Increase timeouts** in `test_config.py`:
   ```python
   connect_timeout = 10  # Increase from 5
   read_timeout = 20     # Increase from 10
   serial_timeout = 5.0  # Increase from 2.0
   ```

4. **Run with verbose output** to see where it hangs:
   ```bash
   pytest test_serial_shell.py -v -s
   ```

## Best Practices

1. **Run tests after firmware updates**: Verify functionality after changes
2. **Skip network config tests**: Use `--run-network-tests` only when needed
3. **Check GPIO mutual exclusion**: Safety-critical constraint
4. **Use pytest for CI/CD**: Integrates well with continuous integration
5. **Monitor serial console**: Watch for unexpected errors during tests
6. **Timeout protection**: All tests have timeout protection to prevent hanging

## Troubleshooting

### Web UI Tests

**Playwright not installed:**
```bash
pip install playwright
playwright install chromium
```

**Browser binary missing:**
```bash
playwright install --with-deps chromium
```

**Tests timing out:**
- Increase timeouts in `test_config.py`:
  - `page_load_timeout = 30000` (milliseconds)
  - `websocket_timeout = 10.0` (seconds)
- Check network connection to device
- Verify WebSocket is working (check browser developer console)

**Debugging web UI test failures:**
```bash
# Run in headed mode to see what's happening
pytest test_web_ui.py -v --headed

# Add slow motion to observe interactions
pytest test_web_ui.py -v --headed --slow-mo 1000

# Check screenshots in screenshots/ directory
ls -la screenshots/
```

**WebSocket connection failures:**
- Verify device web UI is accessible in browser: `http://192.168.1.100`
- Check that HTTP server has WebSocket support enabled
- Ensure firewall allows WebSocket connections

**Button clicks not working:**
- Verify element selectors match actual HTML structure
- Check web UI hasn't changed (element IDs, classes)
- Run in headed mode to see if elements are visible

### REST API Tests

**Connection refused:**
- Verify device is powered on and connected to network
- Check IP address: `ping 192.168.1.100`
- Verify HTTP server is running on device

**Tests failing intermittently:**
- Network latency issues - increase `read_timeout` in config
- Device may need time to process requests - add delays between tests
- Check device logs for errors

### Serial Tests

**Device not found:**
- Verify USB cable is connected
- Check device appears in USB: `lsusb` (Linux) or System Information (macOS)
- Verify permissions: `sudo usermod -a -G dialout $USER` (Linux)
- Try manual port override: `--serial-port /dev/ttyACM0`

**Serial timeout errors:**
- Increase `serial_timeout` in `test_config.py`
- Check baud rate is correct (115200)
- Verify shell prompt is working: `screen /dev/ttyACM0 115200`

## CI/CD Integration

### GitHub Actions Example

```yaml
name: JTAG Switch Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd tests
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd tests
          pytest test_rest_api.py -v --junitxml=test-results.xml
      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v1
        if: always()
        with:
          files: tests/test-results.xml
```

## Contributing

When adding new tests:
1. Follow existing naming conventions (`test_<feature>_<scenario>`)
2. Add docstrings describing what the test verifies
3. Use assertion helpers from `BaseTestCase`
4. Update this README with new test coverage
5. Ensure tests are deterministic and can run repeatedly

## License

Copyright (c) 2025 JTAG Switch Project
SPDX-License-Identifier: Apache-2.0
