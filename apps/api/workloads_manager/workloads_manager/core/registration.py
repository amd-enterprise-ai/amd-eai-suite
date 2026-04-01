# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Registration functionality."""

from pathlib import Path

import httpx
import yaml
from loguru import logger
from pydantic import ValidationError

from .. import config
from ..core.workloads import get_workloads
from ..models import (
    FileProcessingResult,
    OverlayData,
    ProcessingStats,
    ProcessingStatus,
    WorkloadRegistrationResult,
)
from .api import check_api_server, make_api_request
from .utils import temp_file_with_content


def register_workload(workload_name: str, api_url: httpx.URL) -> WorkloadRegistrationResult:
    """Register a workload template to the service."""
    workload = next((w for w in get_workloads() if w.dir_name == workload_name), None)

    if not workload:
        logger.error(f"Workload {workload_name} not found")
        return WorkloadRegistrationResult(success=False, error=f"Workload {workload_name} not found")

    if not workload.is_registerable:
        logger.error(f"Workload {workload_name} is not registerable (missing metadata)")
        return WorkloadRegistrationResult(
            success=False, error=f"Workload {workload_name} is not registerable (missing metadata)"
        )

    if not config.TOKEN:
        logger.error("TOKEN environment variable not set")
        return WorkloadRegistrationResult(success=False, error="TOKEN environment variable not set")

    if not check_api_server(api_url):
        logger.error(f"Cannot register workload: API server at {api_url} is not accessible")
        return WorkloadRegistrationResult(
            success=False, error=f"Cannot register workload: API server at {api_url} is not accessible"
        )

    logger.info(f"Processing chart: {workload.chart_name}")
    chart_id = upload_chart(workload.path, api_url)

    if not chart_id:
        logger.error("Failed to upload chart. Please check API server accessibility.")
        return WorkloadRegistrationResult(
            success=False,
            error="Failed to upload chart. Please check API server accessibility.",
            chart_name=workload.chart_name,
        )

    processed_files: list[FileProcessingResult] = []
    stats = ProcessingStats()

    # Process overlay files using workload method
    overlay_files = workload.get_overlay_files()
    for file_path, rel_path_str in overlay_files:
        status, file_id = process_single_overlay(file_path, rel_path_str, api_url, chart_id)
        result = FileProcessingResult(path=rel_path_str, status=ProcessingStatus(status), id=file_id)
        processed_files.append(result)
        stats.increment(ProcessingStatus(status))

    # Process all other files for reporting (chart files + skipped files)
    processed_paths = {result.path for result in processed_files}

    for file_path, rel_path_str in workload._iter_files():
        if rel_path_str in processed_paths:
            continue  # Already processed as overlay

        if workload._is_allowed_file(rel_path_str):
            # This is a chart file (not overlay)
            result = FileProcessingResult(path=rel_path_str, status=ProcessingStatus.SUCCESS, id="Part of chart")
        else:
            # This file is not allowed/skipped
            result = FileProcessingResult(path=rel_path_str, status=ProcessingStatus.SKIPPED, id="")

        processed_files.append(result)
        stats.increment(result.status)

    return WorkloadRegistrationResult(
        success=True,
        chart_id=chart_id,
        chart_name=workload.chart_name,
        files=processed_files,
        stats=stats,
    )


def upload_chart(workload_path: Path, api_url: httpx.URL) -> str | None:
    """Upload or update a chart to the service and return the chart ID."""
    workload = next((w for w in get_workloads() if w.dir_name == workload_path.name), None)
    if not workload:
        logger.error(f"Workload {workload_path.name} not found")
        return None

    if not workload.chart_path.exists():
        logger.error(f"Chart directory not found at {workload.chart_path}")
        return None

    api_files = workload.get_chart_upload_data()
    if not api_files:
        return None

    # Build form data with basic fields and metadata
    form_data: dict[str, str | list | dict | None] = {"name": workload.chart_name, "type": workload.type}

    # Add metadata fields if available
    metadata = workload.get_metadata_for_api()
    form_data.update(metadata)

    existing_chart_id = get_chart_id(workload.chart_name, api_url)  # type: ignore
    if existing_chart_id:
        endpoint = f"charts/{existing_chart_id}"
        method = "PUT"
        logger.info(
            f"Updating chart: {workload.chart_name} (ID: {existing_chart_id}) with {len(api_files['files'])} chart files + signature"
        )
    else:
        endpoint = "charts"
        method = "POST"
        logger.info(f"Creating chart: {workload.chart_name} with {len(api_files['files'])} chart files + signature")

    success, response_data = make_api_request(method, endpoint, api_url, data=form_data, files=api_files)

    if not success:
        error_msg = response_data.get("error", "Unknown error")
        if "detail" in response_data:
            error_msg = response_data["detail"]
        logger.error(f"Failed to upload chart: {error_msg}")
        return None

    # For updates, return the existing chart_id; for creates, extract from response
    if existing_chart_id:
        logger.info(f"Successfully updated chart with ID: {existing_chart_id}")
        return existing_chart_id
    else:
        new_chart_id = response_data.get("id")
        if not new_chart_id:
            if "detail" in response_data:
                logger.error(f"API error details: {response_data['detail']}")
            logger.error("Chart creation response did not contain an ID")
            logger.debug(f"Full response: {response_data}")
            return None

        logger.info(f"Successfully created chart with ID: {new_chart_id}")
        return new_chart_id


def get_chart_id(chart_name: str, api_url: httpx.URL) -> str | None:
    """Get the ID of a chart by name."""
    success, response = make_api_request("GET", f"charts?name={chart_name}", api_url)

    if not success:
        logger.debug(f"Failed to get chart ID for {chart_name}: {response.get('error', 'Unknown error')}")
        return None

    # The API might return a list of charts or a single chart
    if isinstance(response, dict):
        chart_id = response.get("id")
        if chart_id:
            logger.debug(f"Found existing chart: {chart_name} (ID: {chart_id})")
            return chart_id
    elif isinstance(response, list):
        # If it's a list, find the chart with matching name
        for chart in response:
            if isinstance(chart, dict) and chart.get("name") == chart_name:
                chart_id = chart.get("id")
                if chart_id:
                    logger.debug(f"Found existing chart: {chart_name} (ID: {chart_id})")
                    return chart_id

    logger.debug(f"No existing chart found for: {chart_name}")
    return None


def get_overlay_id(chart_id: str, canonical_name: str | None, api_url: httpx.URL) -> str | None:
    """Get the ID of an overlay by chart_id and optional canonical_name."""
    success, response = make_api_request("GET", f"overlays?chart_id={chart_id}", api_url)
    if not success:
        logger.debug(f"Failed to get overlays: {response.get('error', 'Unknown error')}")
        return None

    overlays = response if isinstance(response, list) else [response] if response else []
    for overlay in overlays:
        if isinstance(overlay, dict) and canonical_name == overlay.get("canonical_name"):
            return overlay.get("id")
    return None


def process_single_overlay(overlay_file: Path, rel_path_str: str, api_url: httpx.URL, chart_id: str) -> tuple[str, str]:
    """Process a single overlay file and return (status, file_id)."""
    try:
        content = overlay_file.read_text(encoding="utf-8")

        # Get canonical name only for model files
        canonical_name = None
        if rel_path_str.startswith("overrides/models/"):
            try:
                raw_data = yaml.safe_load(content)
                if raw_data and isinstance(raw_data, dict):
                    overlay_data = OverlayData(**raw_data)
                    canonical_name = overlay_data.canonical_name
            except (ValidationError, Exception) as e:
                logger.warning(f"Could not parse YAML from {overlay_file.name}: {e}")

            if not canonical_name:
                # Fallback to filename-based canonical name
                canonical_name = overlay_file.stem.replace("_", "/").replace(":", "/")

        # Upload overlay directly
        with temp_file_with_content(content, suffix=".yaml") as temp_path:
            if not temp_path:
                logger.error(f"Failed to create temporary file for overlay: {overlay_file.name}")
                return (ProcessingStatus.FAILED, "Error creating temp file")

            data = {"chart_id": chart_id}
            if canonical_name:
                data["canonical_name"] = canonical_name

            files = {"overlay_file": [Path(temp_path)]}

            existing_id = get_overlay_id(chart_id, canonical_name, api_url)
            endpoint = f"overlays/{existing_id}" if existing_id else "overlays"
            method = "PUT" if existing_id else "POST"

            success, response = make_api_request(method, endpoint, api_url, data=data, files=files)

            if success and "id" in response:
                overlay_id = existing_id or response["id"]
                action = "updated" if existing_id else "created"
                target = f"model {canonical_name}" if canonical_name else f"file {overlay_file.name}"
                logger.info(f"Successfully {action} overlay for {target} with ID: {overlay_id}")
                return (ProcessingStatus.SUCCESS, overlay_id)
            else:
                error_msg = response.get("error", "Unknown error")
                logger.error(f"Failed to upload overlay: {error_msg}")
                return (ProcessingStatus.FAILED, "")

    except Exception as e:
        logger.error(f"Error processing overlay {overlay_file}: {e}")
        return (ProcessingStatus.FAILED, "Error processing file")
