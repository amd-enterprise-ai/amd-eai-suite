# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for the direction parameter in workload logs."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from airm.messaging.schemas import WorkloadComponentKind, WorkloadStatus
from app.logs.service import get_workload_logs
from app.workloads.schemas import WorkloadComponent, WorkloadWithComponents


@pytest.fixture
def mock_workload_for_direction():
    """Create a mock workload for direction testing."""
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


@pytest.fixture
def mock_loki_response_with_timestamps():
    """Mock Loki API response with multiple timestamped entries."""
    return {
        "data": {
            "result": [
                {
                    "stream": {
                        "detected_level": "info",
                        "k8s_pod_name": "test-deployment-abc123",
                    },
                    "values": [
                        ["1640995200000000000", "First log entry"],
                        ["1640995260000000000", "Second log entry"],
                        ["1640995320000000000", "Third log entry"],
                    ],
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_direction_forward_default(mock_workload_for_direction, mock_loki_response_with_timestamps):
    """Test that forward direction is used by default."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = mock_loki_response_with_timestamps
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    await get_workload_logs(mock_workload_for_direction, mock_client)

    # Verify the API was called with direction="forward" by default
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "forward"


@pytest.mark.asyncio
async def test_direction_forward_explicit(mock_workload_for_direction, mock_loki_response_with_timestamps):
    """Test explicit forward direction parameter."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = mock_loki_response_with_timestamps
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    result = await get_workload_logs(mock_workload_for_direction, mock_client, direction="forward")

    # Verify the API was called with direction="forward"
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "forward"

    # Verify results are sorted oldest first (forward direction behavior)
    assert len(result.logs) == 3
    assert result.logs[0].message == "First log entry"
    assert result.logs[1].message == "Second log entry"
    assert result.logs[2].message == "Third log entry"


@pytest.mark.asyncio
async def test_direction_backward(mock_workload_for_direction, mock_loki_response_with_timestamps):
    """Test backward direction parameter."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = mock_loki_response_with_timestamps
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    result = await get_workload_logs(mock_workload_for_direction, mock_client, direction="backward")

    # Verify the API was called with direction="backward"
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "backward"
