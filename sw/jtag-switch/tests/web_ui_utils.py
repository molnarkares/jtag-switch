"""
Web UI Testing Utilities for JTAG Switch

This module provides utilities for automated browser testing of the web UI using Playwright.

Classes:
    WebUISession: Manages Playwright browser lifecycle
    JtagSwitchPage: Page object model for web UI interactions

Usage:
    session = WebUISession(config)
    session.start()
    page_helper = JtagSwitchPage(session.page, config.web_ui_url)
    page_helper.goto()
    page_helper.wait_for_connection()
    # ... interact with page ...
    session.close()
"""

import os
import time
from datetime import datetime


class WebUISession:
    """Manages Playwright browser lifecycle and configuration"""

    def __init__(self, config):
        """
        Initialize WebUISession with configuration

        Args:
            config: Config object with browser settings
        """
        self.config = config
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        """Initialize Playwright and launch browser"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        self.playwright = sync_playwright().start()

        # Select browser based on config
        browser_type = getattr(self.playwright, self.config.browser_type)

        # Launch browser with options
        self.browser = browser_type.launch(
            headless=self.config.browser_headless,
            slow_mo=self.config.browser_slow_mo
        )

        # Create browser context
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='JTAG-Switch-Test/1.0 (Playwright)'
        )

        # Set default timeouts
        self.context.set_default_timeout(self.config.element_timeout)
        self.context.set_default_navigation_timeout(self.config.page_load_timeout)

        # Create page
        self.page = self.context.new_page()

        if self.config.verbose:
            print(f"Browser started: {self.config.browser_type} "
                  f"({'headed' if not self.config.browser_headless else 'headless'})")

    def close(self):
        """Clean up Playwright resources"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def new_page(self):
        """Create a fresh page for testing"""
        if self.page:
            self.page.close()
        self.page = self.context.new_page()
        return self.page

    def screenshot(self, name):
        """
        Take a screenshot with timestamped filename

        Args:
            name: Base name for screenshot file

        Returns:
            Path to saved screenshot file
        """
        if not self.page:
            return None

        # Create screenshots directory if it doesn't exist
        screenshot_dir = self.config.screenshot_dir
        os.makedirs(screenshot_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(screenshot_dir, filename)

        # Capture screenshot
        self.page.screenshot(path=filepath)

        return filepath


class JtagSwitchPage:
    """Page object model for JTAG Switch web UI interactions"""

    def __init__(self, page, base_url):
        """
        Initialize page helper

        Args:
            page: Playwright Page object
            base_url: Base URL of the web UI
        """
        self.page = page
        self.base_url = base_url

    # ========================================================================
    # Navigation
    # ========================================================================

    def goto(self):
        """Navigate to the main page"""
        # Wait for networkidle to ensure all resources are loaded
        # and JavaScript has time to execute
        self.page.goto(self.base_url, wait_until="networkidle")

    def refresh(self):
        """Refresh the page"""
        # Wait for networkidle after reload
        self.page.reload(wait_until="networkidle")

    # ========================================================================
    # Connection Status
    # ========================================================================

    def get_connection_status(self):
        """Get connection status text (e.g., 'Connected', 'Disconnected')"""
        element = self.page.locator('#connection-status')
        return element.text_content().strip()

    def wait_for_connection(self, timeout=5):
        """
        Wait for initial data to load (polling-based approach)

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            TimeoutError: If data not loaded within timeout
        """
        # Wait for connection status to show "Connected" and data to be loaded
        # With polling approach, this happens quickly after page load
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_connection_status()
            if status == "Connected":
                # Verify data is loaded by checking if state badges show valid states
                try:
                    line0_state = self.get_line0_state()
                    if line0_state in ["Enabled", "Disabled"]:
                        return  # Data loaded successfully
                except:
                    pass  # State not yet loaded, continue waiting
            time.sleep(0.1)  # Poll every 100ms

        # Timeout - raise error with diagnostic info
        status = self.get_connection_status()
        raise TimeoutError(
            f"Initial data not loaded after {timeout}s. "
            f"Connection status shows: '{status}'"
        )

    def is_connected(self):
        """Check if connection status shows Connected (polling-based)"""
        status = self.get_connection_status()
        return status == "Connected"

    # ========================================================================
    # JTAG Control - Line States
    # ========================================================================

    def get_line0_state(self):
        """Get Line 0 state badge text (e.g., 'Enabled', 'Disabled')"""
        element = self.page.locator('#line0-state')
        return element.text_content().strip()

    def get_line1_state(self):
        """Get Line 1 state badge text (e.g., 'Enabled', 'Disabled')"""
        element = self.page.locator('#line1-state')
        return element.text_content().strip()

    # ========================================================================
    # JTAG Control - Line 0 Buttons
    # ========================================================================

    def click_line0_enable(self):
        """Click the Enable button for Line 0"""
        # Find the button with text "Enable" in the Line 0 control block
        button = self.page.locator('text=Line 0').locator('..').locator('button:has-text("Enable")')
        button.click()

    def click_line0_disable(self):
        """Click the Disable button for Line 0"""
        button = self.page.locator('text=Line 0').locator('..').locator('button:has-text("Disable")')
        button.click()

    def click_line0_toggle(self):
        """Click the Toggle button for Line 0"""
        button = self.page.locator('text=Line 0').locator('..').locator('button:has-text("Toggle")')
        button.click()

    # ========================================================================
    # JTAG Control - Line 1 Buttons
    # ========================================================================

    def click_line1_enable(self):
        """Click the Enable button for Line 1"""
        button = self.page.locator('text=Line 1').locator('..').locator('button:has-text("Enable")')
        button.click()

    def click_line1_disable(self):
        """Click the Disable button for Line 1"""
        button = self.page.locator('text=Line 1').locator('..').locator('button:has-text("Disable")')
        button.click()

    def click_line1_toggle(self):
        """Click the Toggle button for Line 1"""
        button = self.page.locator('text=Line 1').locator('..').locator('button:has-text("Toggle")')
        button.click()

    # ========================================================================
    # Network Information
    # ========================================================================

    def get_network_ip(self):
        """Get displayed IP address"""
        element = self.page.locator('#net-ip')
        return element.text_content().strip()

    def get_network_mac(self):
        """Get displayed MAC address"""
        element = self.page.locator('#net-mac')
        return element.text_content().strip()

    def get_network_mode(self):
        """Get network mode (e.g., 'DHCP', 'Static')"""
        element = self.page.locator('#net-mode')
        return element.text_content().strip()

    def get_link_status_class(self):
        """
        Get link status LED class ('on' or 'off')

        Returns:
            'on' if link is up, 'off' if link is down
        """
        element = self.page.locator('#net-link')
        classes = element.get_attribute('class')
        if 'on' in classes:
            return 'on'
        elif 'off' in classes:
            return 'off'
        return None

    # ========================================================================
    # System Information
    # ========================================================================

    def get_device_name(self):
        """Get device name"""
        element = self.page.locator('#sys-device')
        return element.text_content().strip()

    def get_version(self):
        """Get firmware version"""
        element = self.page.locator('#sys-version')
        return element.text_content().strip()

    def get_uptime(self):
        """Get uptime string (e.g., '0d 0h 5m')"""
        element = self.page.locator('#sys-uptime')
        return element.text_content().strip()

    def get_ram_usage(self):
        """Get RAM usage string (e.g., '45.2 KB')"""
        element = self.page.locator('#sys-ram')
        return element.text_content().strip()

    # ========================================================================
    # Network Configuration Modal
    # ========================================================================

    def open_network_config(self):
        """Click Configure button to open network configuration modal"""
        button = self.page.locator('button:has-text("Configure")')
        button.click()

    def is_modal_visible(self):
        """Check if network configuration modal is visible"""
        modal = self.page.locator('#config-modal')
        return modal.is_visible()

    def close_modal(self):
        """Click Cancel button to close modal"""
        button = self.page.locator('#config-modal button:has-text("Cancel")')
        button.click()

    def select_dhcp_mode(self):
        """Select DHCP radio button"""
        radio = self.page.locator('input[name="mode"][value="dhcp"]')
        radio.check()

    def select_static_mode(self):
        """Select Static IP radio button"""
        radio = self.page.locator('input[name="mode"][value="static"]')
        radio.check()

    def are_static_fields_visible(self):
        """Check if static IP fields are visible"""
        fields = self.page.locator('#static-fields')
        return fields.is_visible()

    def set_static_ip(self, ip, netmask, gateway):
        """
        Fill static IP configuration fields

        Args:
            ip: IP address (e.g., '192.168.1.100')
            netmask: Netmask (e.g., '255.255.255.0')
            gateway: Gateway (e.g., '192.168.1.1')
        """
        self.page.locator('#ip').fill(ip)
        self.page.locator('#netmask').fill(netmask)
        self.page.locator('#gateway').fill(gateway)

    def submit_network_config(self):
        """Submit network configuration form"""
        button = self.page.locator('#config-modal button:has-text("Save")')
        button.click()

    # ========================================================================
    # Alert Handling
    # ========================================================================

    def wait_for_alert(self, timeout=5):
        """
        Wait for and capture alert dialog

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Alert message text, or None if no alert

        Note: This sets up a one-time dialog handler
        """
        alert_message = None

        def handle_dialog(dialog):
            nonlocal alert_message
            alert_message = dialog.message
            dialog.accept()

        self.page.once('dialog', handle_dialog)

        # Wait a bit for dialog to appear
        time.sleep(timeout)

        return alert_message

    # ========================================================================
    # Section Visibility
    # ========================================================================

    def has_header(self):
        """Check if page has header section"""
        header = self.page.locator('h1:has-text("JTAG Switch Control")')
        return header.is_visible()

    def has_jtag_section(self):
        """Check if page has JTAG control section"""
        section = self.page.locator('text=Line 0')
        return section.is_visible()

    def has_network_section(self):
        """Check if page has network information section"""
        section = self.page.locator('#net-ip')
        return section.is_visible()

    def has_system_section(self):
        """Check if page has system information section"""
        section = self.page.locator('#sys-device')
        return section.is_visible()
