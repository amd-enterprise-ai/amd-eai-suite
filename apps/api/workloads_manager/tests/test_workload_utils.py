# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for workload utility functions."""

from pathlib import Path
from unittest.mock import patch

from workloads_manager.core.workloads import (
    check_patches_match_changes,
    get_workloads,
)


def test_get_workloads_with_patches_and_changes(tmp_path: Path) -> None:
    """Test get_workloads function with mocked patches and changes."""
    # Create a workloads directory structure
    workloads_dir = Path(tmp_path) / "workloads"
    workloads_dir.mkdir()

    # Create a test workload directory
    test_workload = workloads_dir / "test-workload"
    test_workload.mkdir()

    # Mock the config to point to our temp directory
    with patch("workloads_manager.config.WORKLOADS_DIR", tmp_path):
        with patch("workloads_manager.core.workloads.get_available_patches", return_value=["test-workload"]):
            with patch("workloads_manager.core.workloads.get_changed_workloads", return_value=({"test-workload"}, [])):
                workloads = get_workloads()

                assert len(workloads) == 1
                assert workloads[0].dir_name == "test-workload"
                assert workloads[0].has_patch
                assert workloads[0].has_changes


def test_check_patches_match_changes():
    """Test check_patches_match_changes function."""
    # Test case 1: Changes match patches
    changed_workloads = {"workload1", "workload2"}
    available_patches = ["workload1", "workload2", "workload3"]
    non_workload_changes = []

    result = check_patches_match_changes(changed_workloads, available_patches, non_workload_changes)
    assert result

    # Test case 2: Changes don't match patches (missing patch)
    changed_workloads = {"workload1", "workload2"}
    available_patches = ["workload1"]  # Missing workload2
    non_workload_changes = []

    result = check_patches_match_changes(changed_workloads, available_patches, non_workload_changes)
    assert not result

    # Test case 3: Non-workload changes present
    changed_workloads = {"workload1"}
    available_patches = ["workload1"]
    non_workload_changes = ["README.md"]  # Non-workload change

    result = check_patches_match_changes(changed_workloads, available_patches, non_workload_changes)
    assert not result

    # Test case 4: No changes
    changed_workloads = set()
    available_patches = ["workload1"]
    non_workload_changes = []

    result = check_patches_match_changes(changed_workloads, available_patches, non_workload_changes)
    assert not result
