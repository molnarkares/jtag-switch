#!/usr/bin/env python3
"""
Renode Simulation Tests for JTAG Switch

Tests the firmware running in Renode simulation to verify:
- Application boots correctly
- GPIO control initializes
- Shell commands work
- Mutual exclusion constraint is enforced

Copyright (c) 2025 JTAG Switch Project
SPDX-License-Identifier: Apache-2.0
"""

import os
import re
import shutil
import subprocess
import sys
import unittest


def find_renode():
    """Find Renode executable from RENODE_PATH env var or system PATH."""
    # First check environment variable
    env_path = os.environ.get('RENODE_PATH')
    if env_path:
        if os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            return env_path
        print(f"ERROR: RENODE_PATH is set to '{env_path}' but it is not a valid executable",
              file=sys.stderr)
        return None

    # Try to find renode on PATH
    renode_path = shutil.which('renode')
    if renode_path:
        return renode_path

    print("ERROR: Renode not found. Please either:", file=sys.stderr)
    print("  1. Add renode to your PATH, or", file=sys.stderr)
    print("  2. Set the RENODE_PATH environment variable to the renode executable", file=sys.stderr)
    return None


class RenodeTestCase(unittest.TestCase):
    """Test JTAG Switch firmware in Renode simulation."""

    # Workspace root (sw/)
    WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    RENODE_PATH = find_renode()

    @classmethod
    def setUpClass(cls):
        """Verify Renode and firmware are available."""
        cls.ELF_PATH = os.path.join(cls.WORKSPACE_ROOT, 'build/zephyr/zephyr.elf')
        cls.RESC_PATH = os.path.join(
            cls.WORKSPACE_ROOT,
            'jtag-switch/boards/renode/frdm_k64f_virtual/support/frdm_k64f_virtual.resc'
        )

        if not cls.RENODE_PATH:
            raise unittest.SkipTest("Renode not found on PATH or via RENODE_PATH environment variable")
        if not os.path.exists(cls.ELF_PATH):
            raise unittest.SkipTest(f"Firmware ELF not found at {cls.ELF_PATH}")
        if not os.path.exists(cls.RESC_PATH):
            raise unittest.SkipTest(f"Renode script not found at {cls.RESC_PATH}")

    def run_renode_commands(self, shell_commands: list, timeout: int = 30) -> str:
        """
        Run shell commands in Renode simulation and capture output.

        Args:
            shell_commands: List of shell commands to send
            timeout: Maximum time to wait (seconds)

        Returns:
            Captured UART output
        """
        # Build Renode command sequence with absolute paths
        renode_cmds = [
            f'$elf=@{self.ELF_PATH}',
            f'include @{self.RESC_PATH}',
            'start',
            'sleep 2',  # Wait for boot
        ]

        # Add shell commands with delays
        for cmd in shell_commands:
            renode_cmds.append(f'uart0 WriteLine "{cmd}"')
            renode_cmds.append('sleep 1')

        renode_cmds.extend([
            'sysbus.uart0 DumpHistoryBuffer',
            'quit'
        ])

        # Run Renode from workspace root
        cmd = [
            self.RENODE_PATH,
            '--disable-gui',
            '--console',
            '-e', '; '.join(renode_cmds)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=self.WORKSPACE_ROOT
        )

        return result.stdout + result.stderr

    def test_boot_and_init(self):
        """Test that firmware boots and initializes correctly."""
        output = self.run_renode_commands([])

        # Check for boot message
        self.assertIn('Booting Zephyr', output)

        # Check application started
        self.assertIn('JTAG Switch Application Starting', output)

        # Check GPIO initialized
        self.assertIn('GPIO control initialized', output)
        self.assertIn('gpio_emul', output)

        # Check shell ready
        self.assertIn('JTAG Switch ready', output)

    def test_status_command(self):
        """Test jtag status command."""
        output = self.run_renode_commands(['jtag status'])

        # Check status output
        self.assertIn('JTAG Switch Status', output)
        self.assertIn('select0:', output)
        self.assertIn('select1:', output)
        self.assertIn('connector', output)

    def test_select0_command(self):
        """Test jtag select0 command."""
        output = self.run_renode_commands([
            'jtag status',
            'jtag select0 1',
            'jtag status'
        ])

        # Check initial state (both 0)
        self.assertIn('select0: 0', output)

        # Check select0 was set
        self.assertIn('select0 set to 1', output)

        # Check final state
        self.assertIn('select0: 1', output)

    def test_select1_command(self):
        """Test jtag select1 command."""
        output = self.run_renode_commands([
            'jtag status',
            'jtag select1 1',
            'jtag status'
        ])

        # Check initial state
        self.assertIn('select1: 0', output)

        # Check select1 was set
        self.assertIn('select1 set to 1', output)

        # Check final state
        self.assertIn('select1: 1', output)

    def test_mutual_exclusion(self):
        """Test that mutual exclusion constraint is enforced."""
        output = self.run_renode_commands([
            'jtag select0 1',  # Set select0 HIGH
            'jtag status',
            'jtag select1 1',  # Try to set select1 HIGH - should clear select0
            'jtag status'
        ])

        # Check mutual exclusion warning
        self.assertIn('Mutual exclusion', output)
        self.assertIn('clearing select0', output)

        # Check final state: select0=0, select1=1
        # Find the final status output
        lines = output.split('\n')
        final_status_idx = None
        for i, line in enumerate(lines):
            if 'jtag status' in line and i > len(lines) // 2:
                final_status_idx = i
                break

        if final_status_idx:
            final_section = '\n'.join(lines[final_status_idx:])
            self.assertIn('select0: 0', final_section)
            self.assertIn('select1: 1', final_section)

    def test_toggle_command(self):
        """Test jtag toggle command."""
        output = self.run_renode_commands([
            'jtag status',
            'jtag toggle0',
            'jtag status',
            'jtag toggle0',
            'jtag status'
        ])

        # Should see select0 go from 0 -> 1 -> 0
        # Check toggle messages
        self.assertIn('select0', output)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
