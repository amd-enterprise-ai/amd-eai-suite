# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Utility functions for workloads manager."""

import os
import tempfile
from contextlib import contextmanager

import rich.table
from loguru import logger
from rich.console import Console


def display_registration_result(result, console: Console) -> None:
    """Display registration result in a formatted table.

    Args:
        result: WorkloadRegistrationResult instance
        console: Rich console instance to print to
    """
    # If we have files to display, create a table
    if result.files and result.chart_id:
        if result.files:
            # Create a table for the registration results
            table = rich.table.Table(
                show_header=True, title=f"Registration Files: {result.chart_name}", title_style="bold green"
            )

            table.add_column("Status")
            table.add_column("Path", no_wrap=False, overflow="fold")
            table.add_column("ID", style="cyan", width=36)

            # Add rows to the table - include all files
            for file_data in sorted(result.files, key=lambda x: x.path):
                status = file_data.status.value if hasattr(file_data.status, "value") else str(file_data.status)
                path = file_data.path
                file_id = file_data.id

                # Set style based on status
                if status == "SUCCESS":
                    style = "green"
                    status_text = "UPLOADED"
                elif status == "SKIPPED":
                    style = "grey70"
                    status_text = "SKIPPED"
                else:
                    style = "red"
                    status_text = "FAILED"

                table.add_row(status_text, path, file_id, style=style)

            # Display the table
            console.print(table)

        # Get statistics
        stats = result.stats
        success_count = stats.success
        skipped_count = stats.skipped
        failed_count = stats.failed
        total_count = stats.total

        # Print summary line
        console.print(
            f"\n[green]{success_count} files uploaded[/green] ([grey70]{skipped_count} skipped[/grey70], [red]{failed_count} failed[/red], total: {total_count})"
        )

        # Print chart ID
        console.print(f"\n[cyan]Chart ID:[/cyan] {result.chart_id}")

        # Check if there are any failed files
        if failed_count > 0:
            console.print(f"[bold red]❌ Workload registration completed with {failed_count} failed file(s)[/]")
        elif result.success:
            console.print("[bold green]✅ Workload registered successfully[/]")
    elif not result.success:
        console.print("[bold red]❌ Workload registration failed[/]")


@contextmanager
def temp_file_with_content(content: str, suffix: str = ".yaml"):
    """Context manager for temporary files."""
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(content.encode())
            temp_file_path = temp_file.name
        yield temp_file_path
    except Exception as e:
        logger.debug(f"Error creating temporary file: {e}")
        yield ""
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.debug(f"Error removing temporary file: {e}")


def camel_to_snake(name: str) -> str:
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def normalize_metadata_keys(raw_metadata: dict) -> dict:
    # Map external keys to internal field names
    key_map = {
        "short_description": "description",
        # Add more mappings if needed
    }
    normalized = {}
    for k, v in raw_metadata.items():
        snake = camel_to_snake(k)
        # Use mapped name if present, otherwise use snake_case
        normalized[key_map.get(snake, snake)] = v
    return normalized
