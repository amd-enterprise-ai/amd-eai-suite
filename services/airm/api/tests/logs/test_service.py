# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for logs service."""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
import websockets

from airm.messaging.schemas import WorkloadComponentKind, WorkloadStatus
from app.logs.schemas import LogEntry, LogLevel
from app.logs.service import (
    _build_loki_query,
    _parse_and_validate_dates,
    create_websocket_connection,
    get_workload_logs,
    stream_workload_logs,
)
from app.workloads.schemas import WorkloadComponent, WorkloadWithComponents


@pytest.fixture
def mock_workload():
    """Create a mock workload with components."""
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
def mock_loki_response():
    """Mock Loki API response."""
    return {
        "data": {
            "result": [
                {
                    "stream": {
                        "detected_level": "info",
                        "k8s_pod_name": "test-deployment-abc123",
                    },
                    "values": [
                        ["1640995200000000000", "Starting application"],
                        ["1640995260000000000", "Application ready"],
                    ],
                }
            ]
        }
    }


def test_log_entry_creation():
    """Test LogEntry Pydantic model creation."""
    entry = LogEntry(timestamp="2025-01-01T00:00:00Z", level=LogLevel.info, message="Test message")
    assert entry.timestamp == "2025-01-01T00:00:00Z"
    assert entry.level == LogLevel.info
    assert entry.message == "Test message"


@pytest.mark.asyncio
async def test_get_workload_logs_success(mock_workload, mock_loki_response):
    """Test successful logs retrieval."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_response = MagicMock(spec=["json", "raise_for_status"])
    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    result = await get_workload_logs(mock_workload, mock_client)

    assert hasattr(result, "logs")
    assert hasattr(result, "pagination")
    assert len(result.logs) == 2  # two entries
    assert result.logs[0].level == LogLevel.info
    assert result.logs[0].message == "Starting application"
    assert result.pagination.has_more is False
    assert result.pagination.total_returned == 2


@pytest.mark.asyncio
async def test_get_workload_logs_empty_response(mock_workload):
    """Test logs retrieval with empty response."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_response = MagicMock(spec=["json", "raise_for_status"])
    mock_response.json.return_value = {"data": {"result": []}}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    result = await get_workload_logs(mock_workload, mock_client)

    assert hasattr(result, "logs")
    assert hasattr(result, "pagination")
    assert len(result.logs) == 0
    assert result.pagination.has_more is False
    assert result.pagination.total_returned == 0


@pytest.mark.asyncio
async def test_get_workload_logs_error_handling(mock_workload):
    """Test logs retrieval with HTTP error."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_client.get.side_effect = Exception("Connection failed")

    result = await get_workload_logs(mock_workload, mock_client)

    assert hasattr(result, "logs")
    assert hasattr(result, "pagination")
    assert len(result.logs) == 0
    assert result.pagination.has_more is False
    assert result.pagination.total_returned == 0


@pytest.mark.asyncio
async def test_get_workload_logs_with_direction_parameter(mock_workload, mock_loki_response):
    """Test that direction parameter is correctly passed to Loki API."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_response = MagicMock(spec=["json", "raise_for_status"])
    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Test with backward direction
    await get_workload_logs(mock_workload, mock_client, direction="backward")

    # Verify the API was called with the correct direction
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "backward"

    # Reset mock for second test
    mock_client.reset_mock()

    # Test with forward direction (explicit)
    await get_workload_logs(mock_workload, mock_client, direction="forward")

    # Verify the API was called with the correct direction
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert called_params["direction"] == "forward"


@pytest.mark.asyncio
async def test_get_workload_logs_with_workload_log_type(mock_workload, mock_loki_response):
    """Test that workload log_type parameter is correctly handled."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_response = MagicMock(spec=["json", "raise_for_status"])
    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Test with workload log type (default)
    await get_workload_logs(mock_workload, mock_client, log_type="workload")

    # Verify the API was called with the correct query (should not include k8s_resource filter)
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert "query" in called_params
    # The query should include component names but not log_type="k8s_event"
    assert "k8s_pod_name=~" in called_params["query"]
    assert 'log_type="k8s_event"' not in called_params["query"]


@pytest.mark.asyncio
async def test_get_workload_logs_with_event_log_type(mock_workload, mock_loki_response):
    """Test that event log_type parameter is correctly handled."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_response = MagicMock(spec=["json", "raise_for_status"])
    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Test with event log type
    await get_workload_logs(mock_workload, mock_client, log_type="event")

    # Verify the API was called with the correct query (should include log_type="k8s_event")
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert "query" in called_params
    # The query should include both component names and log_type="k8s_event"
    assert "k8s_pod_name=~" in called_params["query"]
    assert 'log_type="k8s_event"' in called_params["query"]


@pytest.mark.asyncio
async def test_get_workload_logs_with_log_type_and_level_filter(mock_workload, mock_loki_response):
    """Test that log_type and level_filter parameters work together correctly."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_response = MagicMock(spec=["json", "raise_for_status"])
    mock_response.json.return_value = mock_loki_response
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Test with event log type and warning level filter
    await get_workload_logs(mock_workload, mock_client, log_type="event", level_filter=LogLevel.warning)

    # Verify the API was called with the correct query
    mock_client.get.assert_called_once()
    called_params = mock_client.get.call_args[1]["params"]
    assert "query" in called_params
    query = called_params["query"]

    # The query should include component names, event filter, and level filter
    assert "k8s_pod_name=~" in query
    assert 'log_type="k8s_event"' in query


def test_parse_and_validate_dates_start_date_greater_than_end_date():
    """Test that ValueError is raised when start_date is greater than end_date."""
    # Create dates where start_date > end_date
    start_date = datetime(2025, 1, 2, 12, 0, 0, tzinfo=UTC)
    end_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    # Should raise ValueError when start_date > end_date
    with pytest.raises(ValueError, match=r"Invalid time range: start_date .* >= end_date .*"):
        _parse_and_validate_dates(start_date, end_date, None, "forward")


def test_parse_and_validate_dates_start_date_equal_to_end_date():
    """Test that ValueError is raised when start_date equals end_date."""
    # Create equal dates
    same_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    # Should raise ValueError when start_date == end_date
    with pytest.raises(ValueError, match=r"Invalid time range: start_date .* >= end_date .*"):
        _parse_and_validate_dates(same_date, same_date, None, "forward")


def test_parse_and_validate_dates_valid_range():
    """Test that valid date range is processed correctly."""
    start_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    end_date = datetime(2025, 1, 2, 12, 0, 0, tzinfo=UTC)

    # Should return the dates when valid range is provided
    result_start, result_end = _parse_and_validate_dates(start_date, end_date, None, "forward")

    assert result_start == start_date
    assert result_end == end_date


def test_build_loki_query_single_component_no_filter():
    """Test building Loki query for single component without level filter."""

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names)

    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}'
    assert result == expected


def test_build_loki_query_multiple_components_no_filter():
    """Test building Loki query for multiple components without level filter."""

    component_names = ["test-deployment", "worker-service", "api-gateway"]
    result = _build_loki_query(component_names)

    expected = '{k8s_pod_name=~"test-deployment.*|worker-service.*|api-gateway.*", log_type!="k8s_event"}'
    assert result == expected


def test_build_loki_query_empty_components():
    """Test building Loki query with empty component list."""

    component_names = []
    result = _build_loki_query(component_names)

    expected = '{k8s_pod_name=~"", log_type!="k8s_event"}'
    assert result == expected


def test_build_loki_query_single_component_with_info_filter():
    """Test building Loki query with info level filter."""

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.info)

    # Info level (20) and higher: info, unknown, warning, error, critical
    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}|detected_level="info" or detected_level="unknown" or detected_level="warn" or detected_level="error" or detected_level="fatal"'
    assert result == expected


def test_build_loki_query_single_component_with_warning_filter():
    """Test building Loki query with warning level filter."""

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.warning)

    # Warning level (30) and higher: warning, error, critical
    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}|detected_level="warn" or detected_level="error" or detected_level="fatal"'
    assert result == expected


def test_build_loki_query_single_component_with_error_filter():
    """Test building Loki query with error level filter."""

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.error)

    # Error level (40) and higher: error, critical
    expected = (
        '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}|detected_level="error" or detected_level="fatal"'
    )
    assert result == expected


def test_build_loki_query_single_component_with_critical_filter():
    """Test building Loki query with critical level filter."""

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.critical)

    # Critical level (50): only critical
    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}|detected_level="fatal"'
    assert result == expected


def test_build_loki_query_single_component_with_trace_filter():
    """Test building Loki query with trace level filter (lowest level)."""

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.trace)

    # Trace level (0) and higher: all levels
    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}|detected_level="trace" or detected_level="debug" or detected_level="info" or detected_level="unknown" or detected_level="warn" or detected_level="error" or detected_level="fatal"'
    assert result == expected


def test_build_loki_query_single_component_with_debug_filter():
    """Test building Loki query with debug level filter."""

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.debug)

    # Debug level (10) and higher: debug, info, unknown, warning, error, critical
    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}|detected_level="debug" or detected_level="info" or detected_level="unknown" or detected_level="warn" or detected_level="error" or detected_level="fatal"'
    assert result == expected


def test_build_loki_query_multiple_components_with_filter():
    """Test building Loki query for multiple components with level filter."""

    component_names = ["web-server", "database", "cache"]
    result = _build_loki_query(component_names, LogLevel.warning)

    # Warning level and above with multiple components
    expected = '{k8s_pod_name=~"web-server.*|database.*|cache.*", log_type!="k8s_event"}|detected_level="warn" or detected_level="error" or detected_level="fatal"'
    assert result == expected


def test_build_loki_query_with_workload_log_type():
    """Test building Loki query with workload log type (default)."""
    from app.logs.service import _build_loki_query

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, log_type="workload")

    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}'
    assert result == expected


def test_build_loki_query_with_event_log_type():
    """Test building Loki query with event log type."""
    from app.logs.service import _build_loki_query

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, log_type="event")

    # Event type should add log_type="k8s_event" filter
    expected = '{k8s_pod_name=~"test-deployment.*", log_type="k8s_event"}'
    assert result == expected


def test_build_loki_query_with_event_log_type_and_level_filter():
    """Test building Loki query with event log type and level filter."""
    from app.logs.service import _build_loki_query

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.warning, log_type="event")

    # Should include both event filter and level filter
    expected = '{k8s_pod_name=~"test-deployment.*", log_type="k8s_event"}|detected_level="warn" or detected_level="error" or detected_level="fatal"'
    assert result == expected


def test_build_loki_query_with_workload_log_type_and_level_filter():
    """Test building Loki query with workload log type and level filter."""
    from app.logs.service import _build_loki_query

    component_names = ["test-deployment"]
    result = _build_loki_query(component_names, LogLevel.info, log_type="workload")

    # Should include only level filter for workload type
    expected = '{k8s_pod_name=~"test-deployment.*", log_type!="k8s_event"}|detected_level="info" or detected_level="unknown" or detected_level="warn" or detected_level="error" or detected_level="fatal"'
    assert result == expected


def test_build_loki_query_with_multiple_components_and_event_log_type():
    """Test building Loki query with multiple components and event log type."""
    from app.logs.service import _build_loki_query

    component_names = ["web-server", "database", "cache"]
    result = _build_loki_query(component_names, log_type="event")

    # Should include multiple components with event filter
    expected = '{k8s_pod_name=~"web-server.*|database.*|cache.*", log_type="k8s_event"}'
    assert result == expected


@pytest.mark.asyncio
async def test_get_workload_logs_invalid_date_range(mock_workload):
    """Test that get_workload_logs handles invalid date range properly."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()

    # Create dates where start_date > end_date
    start_date = datetime(2025, 1, 2, 12, 0, 0, tzinfo=UTC)
    end_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    # Should raise ValueError when start_date > end_date
    with pytest.raises(ValueError, match=r"Invalid time range: start_date .* >= end_date .*"):
        await get_workload_logs(mock_workload, mock_client, start_date=start_date, end_date=end_date)


class MockWebSocket:
    """Mock WebSocket connection for testing streaming functionality."""

    def __init__(self, messages: list[str], should_fail_ping: bool = False):
        self.messages = messages
        self.message_iterator = iter(messages)
        self.closed = False
        self.close_called = False
        self.should_fail_ping = should_fail_ping

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the WebSocket connection."""
        self.closed = True
        self.close_called = True

    async def ping(self):
        """Simulate WebSocket ping."""
        if self.should_fail_ping:
            raise websockets.ConnectionClosed(None, None)

    async def recv(self):
        """Simulate WebSocket recv() method."""
        try:
            return next(self.message_iterator)
        except StopIteration:
            # When no more messages, simulate timeout by waiting indefinitely
            await asyncio.sleep(float("inf"))

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.message_iterator)
        except StopIteration:
            raise StopAsyncIteration


def create_mock_websocket_connect(mock_ws):
    """Helper to create a mock websockets.connect that returns the given MockWebSocket."""

    async def mock_connect(url, ping_interval=30, ping_timeout=10, close_timeout=10):
        return mock_ws

    return mock_connect


@pytest.fixture
def sample_log_messages():
    """Sample WebSocket messages for testing."""
    future_time = datetime.now(UTC).timestamp() + 3600  # 1 hour from now
    timestamp1 = int(future_time * 1_000_000_000)
    timestamp2 = timestamp1 + 1_000_000_000  # 1 second later

    return [
        json.dumps(
            {
                "streams": [
                    {
                        "stream": {"detected_level": "info", "k8s_pod_name": "test-deployment-abc123"},
                        "values": [[str(timestamp1), "First log message"]],
                    }
                ]
            }
        ),
        json.dumps(
            {
                "streams": [
                    {
                        "stream": {"detected_level": "error", "k8s_pod_name": "test-deployment-abc123"},
                        "values": [[str(timestamp2), "Error log message"]],
                    }
                ]
            }
        ),
    ]


@pytest.mark.asyncio
async def test_create_websocket_connection_basic_functionality():
    """Test basic create_websocket_connection functionality."""
    workload_id = UUID("ab647a92-960b-4dcb-9262-77a9efa062c1")
    query = '{k8s_pod_name=~"test-deployment.*"}'

    mock_ws = MockWebSocket([])
    call_count = 0

    async def mock_connect_with_counter(url, ping_interval=30, ping_timeout=10, close_timeout=10):
        nonlocal call_count
        call_count += 1
        return mock_ws

    with patch("app.logs.service.websockets.connect", mock_connect_with_counter):
        # Test connection creation
        connection = await create_websocket_connection(workload_id, query)
        assert connection == mock_ws
        assert call_count == 1

        # Test that each call creates a new connection (no reuse)
        connection2 = await create_websocket_connection(workload_id, query)
        assert connection2 == mock_ws
        assert call_count == 2  # Should have been called twice


@pytest.mark.asyncio
async def test_create_websocket_connection_multiple_calls():
    """Test create_websocket_connection creates new connections each time."""
    workload_id = UUID("ab647a92-960b-4dcb-9262-77a9efa062c1")
    query = '{k8s_pod_name=~"test-deployment.*"}'

    # Each connection should be created fresh
    mock_ws1 = MockWebSocket([])
    mock_ws2 = MockWebSocket([])

    connect_calls = [mock_ws1, mock_ws2]
    call_count = 0

    async def mock_connect_multiple(url, ping_interval=30, ping_timeout=10, close_timeout=10):
        nonlocal call_count
        ws = connect_calls[call_count]
        call_count += 1
        return ws

    with patch("app.logs.service.websockets.connect", mock_connect_multiple):
        # Create first connection
        connection1 = await create_websocket_connection(workload_id, query)
        assert connection1 == mock_ws1
        assert call_count == 1

        # Create second connection - should always create a new one
        connection2 = await create_websocket_connection(workload_id, query)
        assert connection2 == mock_ws2
        assert call_count == 2


@pytest.mark.asyncio
async def test_stream_workload_logs_success(mock_workload, sample_log_messages):
    """Test successful log streaming."""
    mock_ws = MockWebSocket(sample_log_messages)

    with patch("app.logs.service.websockets.connect", create_mock_websocket_connect(mock_ws)):
        logs = []
        count = 0

        async for log_entry_str in stream_workload_logs(mock_workload):
            if log_entry_str == "[HEARTBEAT]":
                continue
            log_entry = LogEntry.model_validate_json(log_entry_str)
            logs.append(log_entry)
            count += 1
            if count >= 2:  # Stop after collecting expected logs
                break

        assert len(logs) == 2
        assert logs[0].level == LogLevel.info
        assert logs[0].message == "First log message"
        assert logs[1].level == LogLevel.error
        assert logs[1].message == "Error log message"


@pytest.mark.asyncio
async def test_stream_workload_logs_with_level_filter(mock_workload, sample_log_messages):
    """Test log streaming with level filter."""
    mock_ws = MockWebSocket(sample_log_messages)

    with patch("app.logs.service.websockets.connect", create_mock_websocket_connect(mock_ws)):
        logs = []
        count = 0

        # Only get error level and above
        async for log_entry_str in stream_workload_logs(mock_workload, level_filter=LogLevel.error):
            if log_entry_str == "[HEARTBEAT]":
                continue
            log_entry = LogEntry.model_validate_json(log_entry_str)
            logs.append(log_entry)
            count += 1
            if count >= 2:
                break

        # Should still get all logs since filtering happens in the query, not post-processing
        assert len(logs) == 2


@pytest.mark.asyncio
async def test_stream_workload_logs_websocket_failure(mock_workload):
    """Test log streaming behavior when WebSocket connection fails."""

    async def failing_connect(url, ping_interval=30, ping_timeout=10, close_timeout=10):
        raise websockets.WebSocketException("Connection failed")

    with patch("app.logs.service.websockets.connect", failing_connect):
        with pytest.raises(websockets.WebSocketException):
            async for _ in stream_workload_logs(mock_workload):
                pass  # Should not reach here


@pytest.mark.asyncio
async def test_stream_workload_logs_cancellation_cleanup(mock_workload, sample_log_messages):
    """Test that stream cancellation properly cleans up connections."""
    mock_ws = MockWebSocket(sample_log_messages)

    with patch("app.logs.service.websockets.connect", create_mock_websocket_connect(mock_ws)):
        stream_gen = stream_workload_logs(mock_workload)

        # Start consuming the stream
        try:
            log_entry_str = await stream_gen.__anext__()
            if log_entry_str != "[HEARTBEAT]":
                log_entry = LogEntry.model_validate_json(log_entry_str)
                assert log_entry.message == "First log message"

            # Simulate client disconnection
            raise asyncio.CancelledError("Client disconnected")

        except asyncio.CancelledError:
            # Cleanup should happen in finally block
            await stream_gen.aclose()

        # Connection should be properly closed
        assert mock_ws.close_called


@pytest.mark.asyncio
async def test_stream_workload_logs_malformed_json():
    """Test log streaming handles malformed JSON gracefully."""
    mock_workload = WorkloadWithComponents(
        id=UUID("ab647a92-960b-4dcb-9262-77a9efa062c1"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        project_id=UUID("12345678-1234-5678-9012-123456789012"),
        cluster_id=UUID("12345678-1234-5678-9012-123456789012"),
        status=WorkloadStatus.RUNNING,
        created_by="test@example.com",
        updated_by="test@example.com",
        components=[
            WorkloadComponent(
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
        ],
    )

    malformed_messages = [
        "invalid json",  # Should be skipped
        json.dumps({"streams": [{"stream": {"level": "info"}, "values": []}]}),  # Valid but empty
    ]
    mock_ws = MockWebSocket(malformed_messages)

    with patch("app.logs.service.websockets.connect", create_mock_websocket_connect(mock_ws)):
        logs = []
        count = 0

        async for log_entry_str in stream_workload_logs(mock_workload):
            count += 1
            if count >= 5:  # Prevent infinite loop
                break
            if log_entry_str == "[HEARTBEAT]":
                continue
            logs.append(log_entry_str)

        # Should handle malformed JSON gracefully and continue
        assert len(logs) == 0  # No valid logs in this test


@pytest.mark.asyncio
async def test_stream_workload_logs_no_components(mock_workload):
    """Test log streaming with workload that has no components."""
    # Remove components from workload
    mock_workload.components = []

    logs = []
    async for log_entry_str in stream_workload_logs(mock_workload):
        if log_entry_str != "[HEARTBEAT]":
            logs.append(log_entry_str)

    # Should yield no logs when no components exist
    assert len(logs) == 0


@pytest.mark.asyncio
async def test_stream_workload_logs_no_start_time_filter(mock_workload):
    """Test log streaming without start_time filter accepts all logs."""

    # Create test messages with past timestamps
    past_time = datetime.now(UTC).timestamp() - 3600  # 1 hour ago
    timestamp1 = int(past_time * 1_000_000_000)
    timestamp2 = timestamp1 + 1_000_000_000

    test_messages = [
        json.dumps(
            {
                "streams": [
                    {
                        "stream": {"level": "info", "k8s_pod_name": "test-deployment-abc123"},
                        "values": [[str(timestamp1), "Past log message"]],
                    }
                ]
            }
        ),
        json.dumps(
            {
                "streams": [
                    {
                        "stream": {"level": "error", "k8s_pod_name": "test-deployment-abc123"},
                        "values": [[str(timestamp2), "Another past log"]],
                    }
                ]
            }
        ),
    ]

    mock_ws = MockWebSocket(test_messages)

    with patch("app.logs.service.websockets.connect", create_mock_websocket_connect(mock_ws)):
        logs = []
        count = 0

        # Call without start_time parameter
        async for log_entry_str in stream_workload_logs(mock_workload):
            if log_entry_str == "[HEARTBEAT]":
                continue
            log_entry = LogEntry.model_validate_json(log_entry_str)
            logs.append(log_entry)
            count += 1
            if count >= 2:
                break

        # Should get both logs since no time filter is applied
        assert len(logs) == 2
        assert logs[0].message == "Past log message"
        assert logs[1].message == "Another past log"
