# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workload utility functions."""

from pathlib import Path

import git
from loguru import logger

from .. import config
from ..core.patches import get_available_patches
from ..models import Workload


def get_workloads() -> list[Workload]:
    """Get list of all workloads as Workload objects."""
    workloads_dir = Path(config.WORKLOADS_DIR)
    logger.debug(f"Using workloads directory from config: {workloads_dir}")

    if not workloads_dir.exists():
        logger.error(f"Workloads directory does not exist: {workloads_dir}")
        return []

    workloads_path = workloads_dir / "workloads"
    if not workloads_path.exists():
        logger.error(f"Workloads path does not exist: {workloads_path}")
        return []

    # List available workload directories
    workload_dirs = [d for d in workloads_path.iterdir() if d.is_dir()]
    logger.debug(f"Found {len(workload_dirs)} workload directories: {[d.name for d in workload_dirs]}")

    if not workload_dirs:
        logger.error("No workload directories found")
        return []

    available_patches = get_available_patches()
    changed_workloads, _ = get_changed_workloads()

    # Create workload objects and sort them (metadata first, then by name)
    workload_objects = []
    for workload_dir in workloads_path.iterdir():
        if workload_dir.is_dir():
            workload = Workload(
                path=workload_dir,
                has_patch=workload_dir.name in available_patches,
                has_changes=workload_dir.name in changed_workloads,
            )
            workload_objects.append(workload)

    # Sort workloads with metadata first, then by name
    return sorted(workload_objects, key=lambda w: (not bool(w.metadata), w.dir_name))


def get_workloads_dir_names() -> list[str]:
    """Get list of workload names."""
    return [w.dir_name for w in get_workloads()]


def get_registerable_workloads() -> list[Workload]:
    """Get list of workloads that can be registered."""
    return [w for w in get_workloads() if w.is_registerable]


def get_changed_workloads() -> tuple[set[str], list[str]]:
    """Get the list of workloads that have been modified."""
    workloads_dir = Path(config.WORKLOADS_DIR)

    if not workloads_dir.exists():
        logger.error(f"Workloads directory not found at {workloads_dir}")
        return set(), []

    try:
        repo = git.Repo(workloads_dir)
        ignored_dirs = {".git", ".github", "docker", "docs"}

        # Use git status to get accurate view of all changed files
        try:
            git_status_output = repo.git.status("--porcelain").split("\n")
            all_changed_files = []
            for line in git_status_output:
                if line.strip():
                    # Extract the file path (starts at position 3)
                    file_path = line[3:].strip()
                    all_changed_files.append(file_path)
        except Exception as e:
            # Fallback to the original method if git status fails
            logger.warning(f"Error running git status: {e}")
            changed_files = repo.git.diff("--name-only", "HEAD").split("\n")
            untracked_files = repo.untracked_files
            all_changed_files = changed_files + untracked_files

        # Categorize changes
        changed_workloads = set()
        non_workload_changes = []

        for file_path in all_changed_files:
            if file_path and file_path.startswith("workloads/"):
                parts = file_path.split("/")
                if len(parts) > 1 and parts[1] not in ignored_dirs:
                    changed_workloads.add(parts[1])
            else:
                # Track files changed outside workloads folder
                if file_path.strip():  # Skip empty lines
                    non_workload_changes.append(file_path)

        return changed_workloads, non_workload_changes
    except Exception as e:
        logger.warning(f"Unable to determine changed workloads: {e}")
        return set(), []


def check_patches_match_changes(
    changed_workloads: set[str], available_patches: list[str], non_workload_changes: list[str]
) -> bool:
    """Check if the current changes match the existing patches."""
    # Changes match if:
    # 1. All changed workloads have corresponding patches AND
    # 2. There are no changes outside workloads directory
    workloads_match = changed_workloads and changed_workloads.issubset(set(available_patches))
    return bool(workloads_match and not non_workload_changes)
