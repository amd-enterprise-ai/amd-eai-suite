#!/usr/bin/env python3

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
"""
Wrapper script for fix_shellcheck_issues.sh that ensures shellcheck is installed.
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


def ensure_shellcheck_installed():
    """Ensure shellcheck is installed and available."""
    # Check if shellcheck is already in PATH
    if shutil.which("shellcheck"):
        print("shellcheck is already in PATH")
        return True

    # Check if shellcheck-py is installed
    if importlib.util.find_spec("shellcheck") is None:
        print("Installing shellcheck-py...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "shellcheck-py==0.9.0.6"])
        except subprocess.CalledProcessError:
            print("Failed to install shellcheck-py")
            return False

    return True


def run_shellcheck_fixer(args):
    """Run the shellcheck fixer script with the given arguments."""
    script_dir = Path(__file__).parent
    fixer_script = script_dir / "fix_shellcheck_issues.sh"

    if not fixer_script.exists():
        print(f"Error: {fixer_script} does not exist")
        return 1

    # Make sure the script is executable
    fixer_script.chmod(fixer_script.stat().st_mode | 0o111)

    # Run the script with the given arguments
    cmd = [str(fixer_script)] + args
    return subprocess.call(cmd)


def main():
    """Main entry point."""
    if not ensure_shellcheck_installed():
        return 1

    return run_shellcheck_fixer(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
