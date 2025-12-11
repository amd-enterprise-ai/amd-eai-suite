# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for utility functions."""

from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from workloads_manager.core.api import make_api_request
from workloads_manager.core.utils import camel_to_snake, normalize_metadata_keys


def test_make_api_request_files_format(tmp_path: Path) -> None:
    """Test that make_api_request handles the new files format correctly."""
    # Create test files
    file1 = tmp_path / "test1.txt"
    file2 = tmp_path / "test2.txt"
    file3 = tmp_path / "test3.txt"

    file1.write_text("content1")
    file2.write_text("content2")
    file3.write_text("content3")

    # Test the new format: dict mapping field names to lists of file paths
    files = {"single_file": [str(file1)], "multiple_files": [str(file2), str(file3)]}

    # Mock the httpx client request call
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}

    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.request.return_value = mock_response

        with patch("workloads_manager.config.TOKEN", "test-token"):
            success, response = make_api_request(
                method="POST", endpoint="test", api_url=httpx.URL("http://localhost:8000"), files=files
            )

    # Verify the call was made successfully
    assert success
    assert response == {"success": True}

    # Verify the request was called with the correct files
    mock_client.request.assert_called_once()
    call_args = mock_client.request.call_args

    # Check that files were properly formatted
    request_files = call_args.kwargs["files"]
    assert len(request_files) == 3  # 1 + 2 files

    # Verify field names and file contents
    field_names = [item[0] for item in request_files]
    assert "single_file" in field_names
    assert field_names.count("multiple_files") == 2  # Two files for this field


def test_make_api_request_no_files():
    """Test make_api_request without files."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}

    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.request.return_value = mock_response

        with patch("workloads_manager.config.TOKEN", "test-token"):
            success, response = make_api_request(
                method="GET", endpoint="test", api_url=httpx.URL("http://localhost:8000")
            )

    assert success
    assert response == {"data": "test"}

    # Verify no files were passed
    call_args = mock_client.request.call_args
    assert call_args.kwargs.get("files") is None


def test_camel_to_snake_basic():
    assert camel_to_snake("shortDescription") == "short_description"
    assert camel_to_snake("longDescription") == "long_description"
    assert camel_to_snake("CPUCoreCount") == "cpu_core_count"
    assert camel_to_snake("gpuCount") == "gpu_count"
    assert camel_to_snake("simple") == "simple"
    assert camel_to_snake("already_snake_case") == "already_snake_case"


def test_normalize_metadata_keys_basic():
    raw = {
        "shortDescription": "desc",
        "longDescription": "long",
        "featuredImage": "img",
        "requiredResources": {"cpuCoreCount": 2},
        "id": "abc",
        "type": "test",
    }
    normalized = normalize_metadata_keys(raw)
    # shortDescription should map to description
    assert normalized["description"] == "desc"
    # longDescription should be converted to long_description
    assert normalized["long_description"] == "long"
    # featuredImage should be converted to featured_image
    assert normalized["featured_image"] == "img"
    # requiredResources should be converted to required_resources
    assert normalized["required_resources"] == {"cpuCoreCount": 2}
    # id and type should remain unchanged
    assert normalized["id"] == "abc"
    assert normalized["type"] == "test"


def test_normalize_metadata_keys_with_snake_case():
    raw = {"short_description": "desc", "long_description": "long", "featured_image": "img"}
    normalized = normalize_metadata_keys(raw)
    assert normalized["description"] == "desc"
    assert normalized["long_description"] == "long"
    assert normalized["featured_image"] == "img"
