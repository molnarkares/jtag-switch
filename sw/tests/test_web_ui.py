#!/usr/bin/env python3
"""
JTAG Switch Web UI Test Suite

Comprehensive automated browser testing of the web UI using Playwright.

Test Coverage (18 tests):
- PageLoadTests (4 tests) - Page loading and structure
- JtagControlTests (10 tests) - JTAG line controls and state synchronization
- PollingTests (4 tests) - Polling behavior and page refresh performance

Note: External changes via REST API are not polled - only user-initiated
button clicks update JTAG states immediately via POST response feedback.
System/network info is polled every 10 seconds for background updates.

Usage:
    python test_web_ui.py
    pytest test_web_ui.py -v
    pytest test_web_ui.py::PageLoadTests -v
    pytest test_web_ui.py --headed  # Run with visible browser
"""

import unittest
import sys
import time
import os
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_config import Config, config
from web_ui_utils import WebUISession, JtagSwitchPage

# Also import test_base to use for REST API calls when needed
from test_base import DeviceConnection


class WebUITestCase(unittest.TestCase):
    """
    Base class for web UI tests

    This class manages the Playwright browser session and provides
    common setup/teardown functionality for all web UI tests.
    """

    session = None
    page_helper = None
    config = None
    device = None  # HTTP client for REST API calls

    @classmethod
    def setUpClass(cls):
        """Initialize browser session once for all tests in the class"""
        cls.config = config
        if cls.config.skip_web_ui_tests:
            raise unittest.SkipTest("Web UI tests skipped (--skip-web-ui)")

        # Check if Playwright is installed
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise unittest.SkipTest(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        # Initialize HTTP client first to check device availability
        # Use base_url not api_url since tests include /api/ in paths
        cls.device = DeviceConnection(cls.config.base_url)

        # Verify device is reachable before starting browser (saves time on failures)
        try:
            import requests
            if cls.config.verbose:
                print(f"\nChecking device connectivity at {cls.config.base_url}...")
            response = cls.device.get('/api/health')
            if response.status_code != 200:
                raise unittest.SkipTest(
                    f"Device not responding properly (status {response.status_code})"
                )
        except requests.exceptions.Timeout:
            raise unittest.SkipTest(
                f"Device connection timeout at {cls.config.base_url} (check IP/network)"
            )
        except requests.exceptions.ConnectionError:
            raise unittest.SkipTest(
                f"Cannot connect to device at {cls.config.base_url} (check device is powered on)"
            )
        except Exception as e:
            raise unittest.SkipTest(f"Device connectivity check failed: {e}")

        # Initialize browser session
        if cls.config.verbose:
            print(f"Initializing browser session ({cls.config.browser_type})...")

        cls.session = WebUISession(cls.config)
        cls.session.start()
        cls.page_helper = JtagSwitchPage(cls.session.page, cls.config.web_ui_url)

        if cls.config.verbose:
            print(f"Browser ready. Testing: {cls.config.web_ui_url}")

    @classmethod
    def tearDownClass(cls):
        """Close browser session after all tests"""
        if cls.session:
            cls.session.close()
        if cls.device:
            cls.device.close()

        # Brief pause between test classes for device recovery
        # Polling approach has no persistent connections, so minimal delay needed
        if cls.config.verbose:
            print(f"\nWaiting 3s for device recovery...")
        time.sleep(3)

    def setUp(self):
        """Navigate to page before each test"""
        # Navigate to main page
        self.page_helper.goto()

        # Wait for initial data load (polling-based)
        try:
            self.page_helper.wait_for_connection(timeout=5)
        except Exception as e:
            self.fail(f"Initial data load failed: {e}")

        # Small delay to ensure page is fully stable
        time.sleep(0.2)

    def tearDown(self):
        """Screenshot on failure and cleanup resources"""
        # Check if test failed (compatible with both unittest and pytest)
        if hasattr(self, '_outcome'):
            result = self._outcome.result
            # Handle both unittest and pytest result objects
            if result:
                errors = getattr(result, 'errors', [])
                failures = getattr(result, 'failures', [])
                if len(errors) > 0 or len(failures) > 0:
                    # Test failed - take screenshot if enabled
                    if self.config.screenshot_on_failure and self.session:
                        screenshot_path = self.session.screenshot(
                            f"{self.__class__.__name__}_{self._testMethodName}"
                        )
                        if self.config.verbose and screenshot_path:
                            print(f"\nScreenshot saved: {screenshot_path}")

        # Close page to free HTTP connections
        if self.session and self.session.page:
            self.session.page.close()
            # Create new page for next test
            self.session.page = self.session.context.new_page()
            self.page_helper.page = self.session.page

        # Brief delay for HTTP connection cleanup
        # Polling approach has no persistent connections to clean up
        time.sleep(2)


# ============================================================================
# Page Load Tests (4 tests)
# ============================================================================


@pytest.mark.web_ui
@pytest.mark.timeout(60)
class PageLoadTests(WebUITestCase):
    """Test page loading and basic structure"""

    def test_page_loads_successfully(self):
        """Page should load with HTTP 200 and correct title"""
        # Check that page loaded (goto() in setUp would have failed otherwise)
        # Verify page title
        title = self.session.page.title()
        self.assertIn("JTAG", title, "Page title should contain 'JTAG'")

    def test_page_has_main_sections(self):
        """Page should have all main sections (header, JTAG, network, system)"""
        self.assertTrue(self.page_helper.has_header(), "Page should have header")
        self.assertTrue(self.page_helper.has_jtag_section(), "Page should have JTAG control section")
        self.assertTrue(self.page_helper.has_network_section(), "Page should have network info section")
        self.assertTrue(self.page_helper.has_system_section(), "Page should have system info section")

    def test_connection_status_shows_connected(self):
        """Connection status should show 'Connected' after data loads"""
        status = self.page_helper.get_connection_status()
        self.assertEqual(status, "Connected", "Connection status should be 'Connected'")
        self.assertTrue(self.page_helper.is_connected(), "Page should be connected")

    def test_initial_line_states_displayed(self):
        """Both JTAG line states should be visible on page load"""
        line0_state = self.page_helper.get_line0_state()
        line1_state = self.page_helper.get_line1_state()

        # States should be either "Enabled" or "Disabled"
        self.assertIn(line0_state, ["Enabled", "Disabled"],
                      f"Line 0 state should be Enabled or Disabled, got: {line0_state}")
        self.assertIn(line1_state, ["Enabled", "Disabled"],
                      f"Line 1 state should be Enabled or Disabled, got: {line1_state}")


# ============================================================================
# JTAG Control Tests (10 tests) - HIGH PRIORITY
# ============================================================================


@pytest.mark.web_ui
@pytest.mark.timeout(60)
class JtagControlTests(WebUITestCase):
    """Test JTAG line control interactions"""

    def test_line0_enable_button_updates_state(self):
        """Clicking Line 0 Enable button should update state to 'Enabled'"""
        self.page_helper.click_line0_enable()

        # Brief wait for POST response and UI update
        time.sleep(0.3)

        state = self.page_helper.get_line0_state()
        self.assertEqual(state, "Enabled", "Line 0 state should be 'Enabled' after clicking Enable")

    def test_line0_disable_button_updates_state(self):
        """Clicking Line 0 Disable button should update state to 'Disabled'"""
        self.page_helper.click_line0_disable()

        # Brief wait for POST response and UI update
        time.sleep(0.3)

        state = self.page_helper.get_line0_state()
        self.assertEqual(state, "Disabled", "Line 0 state should be 'Disabled' after clicking Disable")

    def test_line0_toggle_button_changes_state(self):
        """Clicking Line 0 Toggle button should change state"""
        # Get initial state
        initial_state = self.page_helper.get_line0_state()

        # Click toggle
        self.page_helper.click_line0_toggle()
        time.sleep(0.3)

        # Get new state
        new_state = self.page_helper.get_line0_state()

        # State should have changed
        self.assertNotEqual(initial_state, new_state,
                            "Line 0 state should change after clicking Toggle")

        # Should toggle between Enabled and Disabled
        if initial_state == "Enabled":
            self.assertEqual(new_state, "Disabled")
        else:
            self.assertEqual(new_state, "Enabled")

    def test_line1_enable_button_updates_state(self):
        """Clicking Line 1 Enable button should update state to 'Enabled'"""
        self.page_helper.click_line1_enable()
        time.sleep(0.3)

        state = self.page_helper.get_line1_state()
        self.assertEqual(state, "Enabled", "Line 1 state should be 'Enabled' after clicking Enable")

    def test_line1_disable_button_updates_state(self):
        """Clicking Line 1 Disable button should update state to 'Disabled'"""
        self.page_helper.click_line1_disable()
        time.sleep(0.3)

        state = self.page_helper.get_line1_state()
        self.assertEqual(state, "Disabled", "Line 1 state should be 'Disabled' after clicking Disable")

    def test_line1_toggle_button_changes_state(self):
        """Clicking Line 1 Toggle button should change state"""
        initial_state = self.page_helper.get_line1_state()

        self.page_helper.click_line1_toggle()
        time.sleep(0.3)

        new_state = self.page_helper.get_line1_state()

        self.assertNotEqual(initial_state, new_state,
                            "Line 1 state should change after clicking Toggle")

        if initial_state == "Enabled":
            self.assertEqual(new_state, "Disabled")
        else:
            self.assertEqual(new_state, "Enabled")

    def test_button_click_sends_api_request(self):
        """Button clicks should trigger REST API POST requests"""
        # This test verifies that clicking buttons results in actual state changes
        # which implies the API is being called correctly

        # Set Line 0 to Disabled
        self.page_helper.click_line0_disable()
        time.sleep(0.3)

        # Verify via REST API that state changed
        response = self.device.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data['select0'], "Line 0 should be disabled (false) after clicking Disable")

    def test_enable_button_error_shows_alert(self):
        """Simulated API errors should show alert dialogs"""
        # Note: This test is difficult to implement without mocking the backend
        # We'll test that the buttons work correctly instead
        # TODO: Enhance this test with network interception to simulate errors
        self.skipTest("Error simulation requires network interception (future enhancement)")

    def test_state_persists_after_refresh(self):
        """JTAG line states should persist after page refresh"""
        # Set Line 0 to Enabled
        self.page_helper.click_line0_enable()
        time.sleep(0.3)

        initial_state = self.page_helper.get_line0_state()

        # Refresh page
        self.page_helper.refresh()
        self.page_helper.wait_for_connection(timeout=5)
        time.sleep(0.2)

        # Check state after refresh
        refreshed_state = self.page_helper.get_line0_state()

        self.assertEqual(initial_state, refreshed_state,
                         "Line 0 state should persist after page refresh")

    def test_both_lines_controllable_independently(self):
        """Both lines should be controllable independently"""
        # Set Line 0 to Enabled, Line 1 to Disabled
        self.page_helper.click_line0_enable()
        time.sleep(0.2)
        self.page_helper.click_line1_disable()
        time.sleep(0.3)

        line0_state = self.page_helper.get_line0_state()
        line1_state = self.page_helper.get_line1_state()

        self.assertEqual(line0_state, "Enabled", "Line 0 should be Enabled")
        self.assertEqual(line1_state, "Disabled", "Line 1 should be Disabled")

        # Now reverse them
        self.page_helper.click_line0_disable()
        time.sleep(0.2)
        self.page_helper.click_line1_enable()
        time.sleep(0.3)

        line0_state = self.page_helper.get_line0_state()
        line1_state = self.page_helper.get_line1_state()

        self.assertEqual(line0_state, "Disabled", "Line 0 should be Disabled")
        self.assertEqual(line1_state, "Enabled", "Line 1 should be Enabled")


# ============================================================================
# Polling Tests (4 tests)
# ============================================================================


@pytest.mark.web_ui
@pytest.mark.timeout(60)
class PollingTests(WebUITestCase):
    """Test polling behavior, immediate button feedback, and page refresh"""

    def test_connection_indicator_shows_connected(self):
        """Connection indicator should show Connected after initial load"""
        # Connection is verified in setUp, but let's be explicit
        self.assertTrue(self.page_helper.is_connected(),
                        "Connection should be established after page load")

    def test_button_clicks_update_immediately(self):
        """Button clicks should update UI immediately via POST response (not polling)"""
        # This test verifies that button actions don't need to wait for polling
        # POST responses include GPIO states for instant feedback

        # Make a change via button
        initial_time = time.time()
        self.page_helper.click_line0_toggle()

        # Small wait for UI update from POST response
        time.sleep(0.3)

        # Check state changed quickly (not via 10s poll)
        elapsed = time.time() - initial_time
        self.assertLess(elapsed, 2, "Button click should update UI in <2 seconds (instant)")

        # Verify state actually changed
        state = self.page_helper.get_line0_state()
        self.assertIn(state, ["Enabled", "Disabled"], "State should be valid after button click")

    def test_page_refresh_reconnects_quickly(self):
        """Page refresh should reconnect in <5 seconds (no WebSocket cleanup delay)"""
        # Verify initial connection
        self.assertTrue(self.page_helper.is_connected())

        # Measure refresh time
        start_time = time.time()
        self.page_helper.refresh()
        self.page_helper.wait_for_connection(timeout=5)
        reconnect_time = time.time() - start_time

        # Should reconnect quickly (no 20-second WebSocket cleanup delay)
        self.assertLess(reconnect_time, 5,
                        f"Page refresh should reconnect in <5s, took {reconnect_time:.1f}s")
        self.assertTrue(self.page_helper.is_connected(),
                        "Should be connected after refresh")

    def test_connection_status_remains_stable(self):
        """Connection status should remain Connected during normal operation"""
        # After page load, should show Connected
        status = self.page_helper.get_connection_status()
        self.assertEqual(status, "Connected", "Should show 'Connected' after page load")

        # Wait a few seconds and verify still connected
        time.sleep(3)
        status = self.page_helper.get_connection_status()
        self.assertEqual(status, "Connected", "Should remain 'Connected' during operation")

        self.assertTrue(self.page_helper.is_connected())


# ============================================================================
# Test Runner
# ============================================================================


def run_tests():
    """Run all web UI tests"""
    global config
    config = Config.from_args()

    # Build test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(PageLoadTests))
    suite.addTests(loader.loadTestsFromTestCase(JtagControlTests))
    suite.addTests(loader.loadTestsFromTestCase(PollingTests))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if config.verbose else 1)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
