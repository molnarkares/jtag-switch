#!/usr/bin/env python3
"""
Master Test Runner for JTAG Switch Test Suite

Runs all test suites:
- REST API tests (27 tests)
- Serial shell tests (15 tests, auto-skip if hardware unavailable)
- Web UI tests (20 tests, auto-skip if Playwright missing)

Total: 62 tests

Usage:
    python test_all.py                    # Run all tests
    python test_all.py --skip-serial      # Skip serial tests
    python test_all.py --skip-web-ui      # Skip web UI tests
    python test_all.py -v                 # Verbose output
    python test_all.py --headed           # Run web UI tests with visible browser
    pytest test_all.py -v                 # Run via pytest
"""

import sys
import unittest
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_config import Config, config


def run_all_tests():
    """Run all test suites with unified reporting"""

    # Parse config from CLI
    global config
    config = Config.from_args()

    # Create master test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_counts = {
        'rest_api': 0,
        'serial': 0,
        'web_ui': 0,
        'total': 0
    }

    # ========================================================================
    # Load REST API Tests
    # ========================================================================
    print("=" * 70)
    print("LOADING REST API TESTS")
    print("=" * 70)
    try:
        import test_rest_api
        rest_suite = loader.loadTestsFromModule(test_rest_api)
        suite.addTests(rest_suite)
        test_counts['rest_api'] = rest_suite.countTestCases()
        print(f"Loaded {test_counts['rest_api']} REST API tests")
    except ImportError as e:
        print(f"Failed to load REST API tests: {e}")

    # ========================================================================
    # Load Serial Shell Tests
    # ========================================================================
    print("\n" + "=" * 70)
    print("LOADING SERIAL SHELL TESTS")
    print("=" * 70)
    if config.skip_serial_tests:
        print("Serial tests SKIPPED (--skip-serial)")
    else:
        try:
            import test_serial_shell
            serial_suite = loader.loadTestsFromModule(test_serial_shell)
            suite.addTests(serial_suite)
            test_counts['serial'] = serial_suite.countTestCases()
            print(f"Loaded {test_counts['serial']} serial tests")
        except ImportError as e:
            print(f"Serial tests SKIPPED (dependency missing: {e})")

    # ========================================================================
    # Load Web UI Tests
    # ========================================================================
    print("\n" + "=" * 70)
    print("LOADING WEB UI TESTS")
    print("=" * 70)
    if config.skip_web_ui_tests:
        print("Web UI tests SKIPPED (--skip-web-ui)")
    else:
        try:
            import test_web_ui
            web_suite = loader.loadTestsFromModule(test_web_ui)
            suite.addTests(web_suite)
            test_counts['web_ui'] = web_suite.countTestCases()
            print(f"Loaded {test_counts['web_ui']} web UI tests")
        except ImportError as e:
            print(f"Web UI tests SKIPPED (dependency missing: {e})")

    # Calculate total
    test_counts['total'] = suite.countTestCases()

    # ========================================================================
    # Run All Tests
    # ========================================================================
    print("\n" + "=" * 70)
    print(f"RUNNING ALL TESTS ({test_counts['total']} total)")
    print("=" * 70)
    print(f"Device:        {config.base_url}")
    print(f"REST API:      {test_counts['rest_api']} tests")
    print(f"Serial Shell:  {test_counts['serial']} tests")
    print(f"Web UI:        {test_counts['web_ui']} tests")
    if test_counts['web_ui'] > 0:
        print(f"Browser:       {config.browser_type} ({'headed' if not config.browser_headless else 'headless'})")
    print("=" * 70 + "\n")

    # Run tests with appropriate verbosity
    runner = unittest.TextTestRunner(verbosity=2 if config.verbose else 1)
    result = runner.run(suite)

    # ========================================================================
    # Print Summary
    # ========================================================================
    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests:  {result.testsRun}")
    print(f"Passed:       {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed:       {len(result.failures)}")
    print(f"Errors:       {len(result.errors)}")
    print(f"Skipped:      {len(result.skipped)}")
    print("=" * 70)

    # Print breakdown by suite
    print("\nTest Suite Breakdown:")
    print(f"  REST API:      {test_counts['rest_api']} tests loaded")
    print(f"  Serial Shell:  {test_counts['serial']} tests loaded")
    print(f"  Web UI:        {test_counts['web_ui']} tests loaded")

    # Success/failure message
    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        if len(result.failures) > 0:
            print(f"\nFailed Tests ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"  - {test}")
        if len(result.errors) > 0:
            print(f"\nErrors ({len(result.errors)}):")
            for test, traceback in result.errors:
                print(f"  - {test}")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
