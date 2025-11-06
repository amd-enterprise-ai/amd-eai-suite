# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""API client functionality for workloads manager."""

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from .. import config


def get_content_type(file_path: Path | str) -> str:
    """Get MIME type based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext in (".yaml", ".yml"):
        return "text/yaml"
    elif ext == ".json":
        return "application/json"
    elif ext in (".md", ".txt", ".tpl"):
        return "text/plain"
    else:
        return "application/octet-stream"


def make_api_request(
    method: str,
    endpoint: str,
    api_url: httpx.URL,
    data: Mapping[str, Any] | None = None,
    files: Mapping[str, list[Path]] | None = None,
) -> tuple[bool, Mapping[str, Any]]:
    """Make an API request using the httpx library.

    Args:
        method: HTTP method (GET, POST, DELETE)
        endpoint: API endpoint
        api_url: Base API URL as httpx.URL
        data: Optional data to send (for POST)
        files: Optional files to upload - dict mapping field_name to list of file_paths.
               Each field can have multiple files: {'field1': ['path1.txt'], 'field2': ['path2.txt', 'path3.txt']}

    Returns:
        Tuple of (success, response_data)
    """

    # Prepare the URL
    if "?" in endpoint:
        path, query = endpoint.split("?", 1)
        url = api_url.copy_with(path=f"/v1/{path.lstrip('/')}", query=query.encode())
    else:
        url = api_url.copy_with(path=f"/v1/{endpoint.lstrip('/')}")

    # Prepare headers - clean the token to remove any newlines or whitespace
    token = config.TOKEN
    if token:
        # Remove any newlines, carriage returns, or extra whitespace
        token = token.replace("\n", "").replace("\r", "").strip()

    headers = {"Authorization": f"Bearer {token}"}

    # Prepare files for upload if provided
    request_files: list[tuple[str, tuple[str, bytes, str]]] | None = None
    if files:
        # Handle dict format: {field_name: [file_path1, file_path2, ...]}
        request_files = []
        for field_name, file_paths in files.items():
            for file_path in file_paths:
                path_obj = Path(file_path)
                file_content = path_obj.read_bytes()
                content_type = get_content_type(path_obj)
                # Use relative path from chart directory to preserve directory structure
                # For chart files, we need to preserve the templates/ directory structure
                filename = str(path_obj.name)  # Default to just filename

                # Check if this is a workload chart file with directory structure
                # Look for helm directory to preserve directory structure
                path_parts = path_obj.parts
                if "helm" in path_parts:
                    helm_idx = path_parts.index("helm")
                    if helm_idx + 1 < len(path_parts):
                        # Get relative path from helm directory
                        rel_parts = path_parts[helm_idx + 1 :]
                        filename = "/".join(rel_parts)

                request_files.append((field_name, (filename, file_content, content_type)))

    # Log the request (without token)
    logger.debug(f"Making {method} request to {url}")
    if data:
        logger.debug(f"With data: {data}")
    if files:
        total_files = sum(len(file_paths) for file_paths in files.values())
        logger.debug(f"With {total_files} files across {len(files)} fields")

    try:
        # Make the request with appropriate timeout
        with httpx.Client(timeout=httpx.Timeout(5.0, read=30.0)) as client:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                files=request_files,
            )

        # Handle 204 No Content response (common for DELETE requests)
        if response.status_code == 204:
            logger.debug("API returned 204 No Content (success)")
            return True, {}

        try:
            response_data = response.json()
            logger.debug(
                f"API response ({response.status_code}): {str(response_data)[:200]}{'...' if len(str(response_data)) > 200 else ''}"
            )

            # Check if the status code indicates success (2xx)
            if 200 <= response.status_code < 300:
                return True, response_data
            else:
                logger.error(f"API request failed with status {response.status_code}: {response_data}")
                return False, response_data
        except ValueError:
            # Log the raw response for debugging
            logger.debug(f"Error parsing API response: {response.text}")

            # If we got a non-empty response, include it in the error
            if response.text.strip():
                return False, {"error": f"Server returned non-JSON response: {response.text[:100]}"}
            else:
                return False, {"error": "Server returned empty response"}
    except Exception as e:
        logger.error(f"Error making API request: {e}")
        return False, {"error": f"Request failed: {str(e)}"}


def check_api_server(api_url: httpx.URL) -> bool:
    """Check if the API server is accessible.

    Args:
        api_url: API URL to check as httpx.URL

    Returns:
        True if accessible, False otherwise
    """
    try:
        health_url = api_url.copy_with(path="/health")
        result = subprocess.run(
            ["curl", "-s", str(health_url)],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug(f"API health check response: {result.stdout}")
        return True
    except subprocess.CalledProcessError:
        logger.error(f"API server at {api_url} is not accessible")
        return False
