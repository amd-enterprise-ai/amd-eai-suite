#!/usr/bin/env python3

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime

import docker


@dataclass
class CleanupStats:
    """Statistics from the cleanup operation."""

    containers_removed: int = 0
    containers_kept: int = 0
    fallback_removed: int = 0
    networks_removed: int = 0


def is_process_running(pid: int | None) -> bool:
    """Check if a process is still running."""
    if pid is None:
        return False
    try:
        # In Unix, if signal 0 doesn't raise an exception, the process is running
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_container_age_minutes(container: docker.models.containers.Container) -> int:
    """Get container age in minutes."""
    try:
        created_time = container.attrs["Created"]
        created_dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        current_dt = datetime.now().astimezone()
        age_seconds = (current_dt - created_dt).total_seconds()
        return int(age_seconds / 60)
    except (KeyError, ValueError):
        return 0


def get_container_pytest_pid(container: docker.models.containers.Container) -> int | None:
    """Extract PID from container environment or labels."""
    # Try to get PID from environment variables
    env_vars = container.attrs.get("Config", {}).get("Env", [])
    for env in env_vars:
        if env.startswith("PYTEST_CURRENT_TEST_PID="):
            try:
                return int(env.split("=")[1])
            except ValueError:
                return None

    # Try to extract from container name pattern
    if (container_name := container.name) is not None:
        match = re.search(r"pytest-(\d+)-", container_name)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

    return None


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Smart cleanup script for pytest Docker resources")
    parser.add_argument("--fallback-age", type=int, default=30, help="Fallback age in minutes (default: 30)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()


def main(fallback_age_minutes: int = 30, verbose: bool = False) -> CleanupStats:
    """
    Main function to clean up pytest Docker resources.

    Args:
        fallback_age_minutes: Age in minutes for fallback cleanup
        verbose: Whether to enable verbose output

    Returns:
        CleanupStats with cleanup statistics
    """
    try:
        client = docker.from_env()
    except Exception as e:
        print(f"Failed to connect to Docker: {e}")
        sys.exit(1)

    # Initialize stats object
    stats = CleanupStats()

    # Get all pytest containers
    pytest_containers = list(client.containers.list(all=True, filters={"name": "pytest"}))

    # Only show startup message if verbose or containers exist
    if verbose or pytest_containers:
        print("🧹 Cleaning up orphaned pytest Docker resources...")
        print(f"Process-based cleanup with {fallback_age_minutes}-minute fallback")
        print("Scanning pytest containers...")

    for container in pytest_containers:
        if verbose:
            print(f"Checking container: {container.name}")

        # Get pytest PID associated with this container
        pytest_pid = get_container_pytest_pid(container)
        container_age = get_container_age_minutes(container)

        should_remove = False
        reason = ""

        # Process-based check
        if pytest_pid is not None:
            if not is_process_running(pytest_pid):
                should_remove = True
                reason = f"pytest process {pytest_pid} no longer running"
            else:
                if verbose:
                    print(f"  ✅ Keeping (pytest process {pytest_pid} still active)")
                stats.containers_kept += 1
        else:
            # Fallback to time-based cleanup if no PID found
            if container_age > fallback_age_minutes:
                should_remove = True
                reason = f"fallback: container older than {fallback_age_minutes} minutes (age: {container_age}m)"
                stats.fallback_removed += 1
            else:
                if verbose:
                    print(f"  ✅ Keeping (no PID found, but only {container_age} minutes old)")
                stats.containers_kept += 1

        if should_remove:
            print(f"  🗑️  Removing: {reason}")
            try:
                container.stop(timeout=1)
                container.remove()
                stats.containers_removed += 1
            except docker.errors.APIError as e:
                print(f"  ❌ Error removing container: {str(e)}")

    # Clean up orphaned pytest networks
    pytest_networks = list(client.networks.list(filters={"name": "pytest"}))
    if verbose or pytest_networks:
        print("Cleaning up pytest networks...")

    for network in pytest_networks:
        try:
            network.remove()
            print(f"  🗑️  Removed network: {network.name}")
            stats.networks_removed += 1
        except docker.errors.APIError:
            if verbose:
                print(f"  ✅ Network {network.name} still in use")

    # Only show summary if something was removed or verbose mode
    if stats.containers_removed > 0 or stats.networks_removed > 0 or verbose:
        print("")
        print("✅ Cleanup complete!")
        print("📊 Summary:")
        print(f"  Containers removed: {stats.containers_removed}")
        if verbose:
            print(f"  Containers kept (active): {stats.containers_kept}")
        print(f"  Networks removed: {stats.networks_removed}")
        if stats.fallback_removed > 0:
            print(f"  Fallback cleanups: {stats.fallback_removed}")
        if verbose:
            print("")
            print("📊 Current Docker resource usage:")
            print(f"  Containers: {len(list(client.containers.list(all=True)))} total")
            print(f"  Networks: {len(list(client.networks.list()))} total")

    return stats


if __name__ == "__main__":
    args = parse_args()
    main(fallback_age_minutes=args.fallback_age, verbose=args.verbose)
