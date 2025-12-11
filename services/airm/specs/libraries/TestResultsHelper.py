# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Robot Framework listener that prints helpful messages after test execution.
Provides guidance on using robot-extract to analyze test failures.
"""

import shutil


class TestResultsHelper:
    """
    Listener that prints helpful messages after test execution completes.

    This listener hooks into the close() event to print instructions for
    analyzing test results, especially when there are failures.
    """

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        """Initialize the listener."""
        self.has_failures = False

    def end_test(self, data, result):
        """Track if any test failed."""
        if not result.passed:
            self.has_failures = True

    def close(self):
        """
        Print helpful message at the end of test execution.
        Called after all tests have finished and output files are written.
        Only prints robot-extract instructions if the command is available.
        """
        # Check if robot-extract is available
        if not shutil.which("robot-extract"):
            return

        print("\n" + "=" * 80)
        print("Test Results Analysis")
        print("=" * 80)

        if self.has_failures:
            print("\n⚠️  Some tests failed. To analyze failures in detail, run:")
            print("\n  robot-extract --failed --first --log-level trace results/output.xml")
            print("\nFor a specific test:")
            print('\n  robot-extract --name "Test Name" --log-level trace results/output.xml')
        else:
            print("\n✅ All tests passed!")
            print("\nTo view detailed execution logs:")
            print('\n  robot-extract --name "Test Name" --log-level trace results/output.xml')

        print("\nFor more query options:")
        print("\n  robot-extract --help")
        print("\n" + "=" * 80 + "\n")
