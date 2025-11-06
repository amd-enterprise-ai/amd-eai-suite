# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Additional tests for LogLevel handling and log filtering."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from airm.messaging.schemas import WorkloadComponentKind, WorkloadStatus
from app.logs.schemas import LogLevel
from app.logs.service import get_workload_logs
from app.workloads.schemas import WorkloadComponent, WorkloadWithComponents


@pytest.fixture
def sample_workload() -> WorkloadWithComponents:
    """Return a fake workload with one component. Re-used across tests."""
    component = WorkloadComponent(
        id=UUID("12345678-1234-5678-9012-123456789012"),
        name="test-deployment",
        kind=WorkloadComponentKind.DEPLOYMENT,
        api_version="apps/v1",
        status="Running",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="tester@example.com",
        updated_by="tester@example.com",
    )

    return WorkloadWithComponents(
        id=UUID("87654321-4321-6789-0123-210987654321"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        project_id=UUID("12345678-1234-5678-9012-123456789012"),
        cluster_id=UUID("12345678-1234-5678-9012-123456789012"),
        status=WorkloadStatus.RUNNING,
        created_by="tester@example.com",
        updated_by="tester@example.com",
        components=[component],
    )


def test_log_level_from_label():
    """Ensure mapping from raw strings to LogLevel works, including unknown handling."""
    # Test standard level names
    assert LogLevel.from_label("info") is LogLevel.info
    assert LogLevel.from_label("debug") is LogLevel.debug
    assert LogLevel.from_label("warn") is LogLevel.warning
    assert LogLevel.from_label("error") is LogLevel.error
    assert LogLevel.from_label("critical") is LogLevel.critical
    assert LogLevel.from_label("trace") is LogLevel.trace

    # Test case insensitive
    assert LogLevel.from_label("WARNING") is LogLevel.warning
    assert LogLevel.from_label("ERROR") is LogLevel.error

    # Test synonyms
    assert LogLevel.from_label("warning") is LogLevel.warning
    assert LogLevel.from_label("fatal") is LogLevel.critical

    # Test unknown/invalid inputs default to info
    assert LogLevel.from_label("nonsense") is LogLevel.unknown
    assert LogLevel.from_label(None) is LogLevel.unknown
    assert LogLevel.from_label("") is LogLevel.unknown


@pytest.mark.asyncio
async def test_get_workload_logs_filter_warning(sample_workload):
    """Verify that log entries below the filter level are excluded."""

    # Prepare mock Loki response containing info, warn, and error entries
    mock_response_payload = {
        "data": {
            "result": [
                {
                    "stream": {"detected_level": "info"},
                    "values": [["1640995200000000000", "Info message"]],
                },
                {
                    "stream": {"detected_level": "warning"},
                    "values": [["1640995300000000000", "Warn message"]],
                },
                {
                    "stream": {"detected_level": "error"},
                    "values": [["1640995400000000000", "Error message"]],
                },
            ]
        }
    }

    mock_client = AsyncMock()
    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response_payload
    mock_http_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_http_response

    # Apply level filter 'warn', expect to keep warning and error only
    logs = await get_workload_logs(sample_workload, mock_client, level_filter=LogLevel.warning)

    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    query = called_params["query"]

    assert 'level=~"warning|error|critical"' in query
