# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for base models."""

from workloads_manager.models.base import ProcessingStats, ProcessingStatus


def test_processing_stats_increment():
    """Test ProcessingStats increment method."""
    stats = ProcessingStats()

    # Initial state
    assert stats.total == 0
    assert stats.success == 0
    assert stats.failed == 0
    assert stats.skipped == 0

    # Increment success
    stats.increment(ProcessingStatus.SUCCESS)
    assert stats.total == 1
    assert stats.success == 1
    assert stats.failed == 0
    assert stats.skipped == 0

    # Increment failed
    stats.increment(ProcessingStatus.FAILED)
    assert stats.total == 2
    assert stats.success == 1
    assert stats.failed == 1
    assert stats.skipped == 0

    # Increment skipped
    stats.increment(ProcessingStatus.SKIPPED)
    assert stats.total == 3
    assert stats.success == 1
    assert stats.failed == 1
    assert stats.skipped == 1
