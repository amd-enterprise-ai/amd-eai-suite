#!/usr/bin/env python3

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
"""
Wrapper script for shellcheck that shows a helpful message when issues are found.
"""

import re
import subprocess
import sys


def main():
    """Run shellcheck and show a helpful message if issues are found."""
    # Get the files to check from command line arguments
    files = sys.argv[1:]
    if not files:
        print("No files to check")
        return 0

    # Run shellcheck with severity=warning
    cmd = ["shellcheck", "--severity=warning"] + files
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print the shellcheck output
    output = result.stdout
    if output:
        print(output)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # If shellcheck found issues, show a helpful message
    if result.returncode != 0:
        # Extract the files that actually had issues
        files_with_issues = []
        if output:
            # Look for lines like "In filename line X:"
            for line in output.split("\n"):
                match = re.match(r"In\s+([^:]+)\s+line\s+\d+:", line)
                if match:
                    filename = match.group(1)
                    if filename not in files_with_issues:
                        files_with_issues.append(filename)

        # If we couldn't extract the files with issues, use all files
        if not files_with_issues:
            files_with_issues = files

        print("\nShellCheck found issues. You can try to fix them automatically with:")
        print(f"  pre-commit run --hook-stage manual shellcheck-fixer --files {' '.join(files_with_issues)}")
        print()

    # Return the original exit code
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
