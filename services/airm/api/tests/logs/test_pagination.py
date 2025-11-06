# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Test pagination functionality for workload logs."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from airm.messaging.schemas import WorkloadComponentKind, WorkloadStatus
from app.logs.service import get_workload_logs
from app.workloads.schemas import WorkloadComponent, WorkloadWithComponents


@pytest.fixture
def mock_workload_for_pagination():
    """Create a mock workload for pagination testing."""
    component = WorkloadComponent(
        id=UUID("12345678-1234-5678-9012-123456789012"),
        name="test-deployment",
        kind=WorkloadComponentKind.DEPLOYMENT,
        api_version="apps/v1",
        status="Running",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    return WorkloadWithComponents(
        id=UUID("ab647a92-960b-4dcb-9262-77a9efa062c1"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        project_id=UUID("12345678-1234-5678-9012-123456789012"),
        cluster_id=UUID("12345678-1234-5678-9012-123456789012"),
        status=WorkloadStatus.RUNNING,
        created_by="test@example.com",
        updated_by="test@example.com",
        components=[component],
    )


@pytest.mark.asyncio
async def test_pagination_has_more_results(mock_workload_for_pagination):
    """Test pagination when there are more results than the limit."""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Mock response with 3 entries (limit + 1 to test has_more)
    mock_loki_response = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                    "values": [
                        ["1640995200000000000", "Log entry 1"],
                        ["1640995260000000000", "Log entry 2"],
                        ["1640995320000000000", "Log entry 3"],
                    ],
                }
            ]
        }
    }

    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Request limit of 2
    result = await get_workload_logs(mock_workload_for_pagination, mock_client, limit=2)

    assert hasattr(result, "logs")
    assert hasattr(result, "pagination")
    assert len(result.logs) == 2  # Should return exactly the limit
    assert result.pagination.has_more is True
    assert result.pagination.page_token is not None
    assert result.pagination.total_returned == 2

    # The next page token should be the timestamp of the last returned entry plus 1 microsecond
    assert (
        result.pagination.page_token
        == (datetime.fromisoformat(result.logs[-1].timestamp) + timedelta(microseconds=1)).isoformat()
    )


@pytest.mark.asyncio
async def test_pagination_no_more_results(mock_workload_for_pagination):
    """Test pagination when there are no more results."""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Mock response with 2 entries (less than limit)
    mock_loki_response = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                    "values": [["1640995200000000000", "Log entry 1"], ["1640995260000000000", "Log entry 2"]],
                }
            ]
        }
    }

    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Request limit of 3
    result = await get_workload_logs(mock_workload_for_pagination, mock_client, limit=3)

    assert len(result.logs) == 2  # Should return all available entries
    assert result.pagination.has_more is False
    assert result.pagination.page_token is None
    assert result.pagination.total_returned == 2


@pytest.mark.asyncio
async def test_pagination_with_direction_backward(mock_workload_for_pagination):
    """Test pagination functionality with backward direction."""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Mock response with 3 entries (limit + 1 to test has_more)
    mock_loki_response = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                    "values": [
                        ["1640995200000000000", "Log entry 1"],
                        ["1640995260000000000", "Log entry 2"],
                        ["1640995320000000000", "Log entry 3"],
                    ],
                }
            ]
        }
    }

    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Request limit of 2 with backward direction
    result = await get_workload_logs(mock_workload_for_pagination, mock_client, limit=2, direction="backward")

    # Verify direction parameter was passed correctly
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "backward"

    # Verify pagination works correctly regardless of direction
    assert len(result.logs) == 2  # Should return exactly the limit
    assert result.pagination.has_more is True
    assert result.pagination.page_token is not None
    assert result.pagination.total_returned == 2


@pytest.mark.asyncio
async def test_pagination_backward_next_start_date_calculation(mock_workload_for_pagination):
    """Test that backward pagination calculates next_start_date by subtracting 1 microsecond."""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Mock response with 3 entries (limit + 1 to test has_more)
    mock_loki_response = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                    "values": [
                        ["1640995200000000000", "Log entry 1"],  # 2022-01-01T00:00:00Z
                        ["1640995260000000000", "Log entry 2"],  # 2022-01-01T00:01:00Z
                        ["1640995320000000000", "Log entry 3"],  # 2022-01-01T00:02:00Z
                    ],
                }
            ]
        }
    }

    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Request limit of 2 with backward direction
    result = await get_workload_logs(mock_workload_for_pagination, mock_client, limit=2, direction="backward")

    assert len(result.logs) == 2
    assert result.pagination.has_more is True
    assert result.pagination.page_token is not None

    # For backward direction, next_start_date should be the last returned entry timestamp minus 1 microsecond
    last_entry_timestamp = datetime.fromisoformat(result.logs[-1].timestamp.replace("Z", "+00:00"))
    expected_next_start = (last_entry_timestamp - timedelta(microseconds=1)).isoformat()
    assert result.pagination.page_token == expected_next_start


@pytest.mark.asyncio
async def test_pagination_backward_no_more_results(mock_workload_for_pagination):
    """Test backward pagination when there are no more results."""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Mock response with only 1 entry (less than limit)
    mock_loki_response = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                    "values": [["1640995200000000000", "Single log entry"]],
                }
            ]
        }
    }

    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Request limit of 2 with backward direction
    result = await get_workload_logs(mock_workload_for_pagination, mock_client, limit=2, direction="backward")

    assert len(result.logs) == 1  # Should return the single available entry
    assert result.pagination.has_more is False
    assert result.pagination.page_token is None
    assert result.pagination.total_returned == 1


@pytest.mark.asyncio
async def test_pagination_backward_default_time_range(mock_workload_for_pagination):
    """Test that backward pagination uses correct default time ranges."""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    mock_loki_response = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                    "values": [["1640995200000000000", "Log entry"]],
                }
            ]
        }
    }

    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Call without specifying start_date or end_date with backward direction
    result = await get_workload_logs(mock_workload_for_pagination, mock_client, direction="backward")

    # Verify the client was called with correct parameters
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "backward"

    # For backward direction with default time range:
    # - start_date should be (now - LOKI_DEFAULT_TIME_RANGE_DAYS)
    # - end_date should be now
    # This ensures start < end (Loki requirement) while direction=backward controls result ordering
    start_timestamp = called_params["start"]
    end_timestamp = called_params["end"]

    # start should be less than end (Loki requirement), direction controls ordering
    assert start_timestamp < end_timestamp


@pytest.mark.asyncio
async def test_pagination_backward_with_custom_dates(mock_workload_for_pagination):
    """Test backward pagination with custom start and end dates."""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    mock_loki_response = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                    "values": [["1640995200000000000", "Log entry"]],
                }
            ]
        }
    }

    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Custom date range
    start_date = datetime(2022, 1, 1, tzinfo=UTC)
    end_date = datetime(2022, 1, 2, tzinfo=UTC)

    result = await get_workload_logs(
        mock_workload_for_pagination, mock_client, start_date=start_date, end_date=end_date, direction="backward"
    )

    # Verify the client was called with the specified dates
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "backward"
    assert called_params["start"] == int(start_date.timestamp() * 1_000_000_000)
    assert called_params["end"] == int(end_date.timestamp() * 1_000_000_000)
