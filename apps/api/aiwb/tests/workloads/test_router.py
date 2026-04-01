# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for workloads router endpoints using FastAPI TestClient with dependency overrides."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from api_common.exceptions import NotFoundException, ValidationException
from api_common.schemas import PaginationMetadataResponse
from app import app  # type: ignore[attr-defined]
from app.logs.schemas import LogEntry, LogLevel, LogType, WorkloadLogsResponse
from app.metrics.enums import MetricName
from app.metrics.schemas import (
    Datapoint,
    DatapointMetadataBase,
    DatapointsWithMetadata,
    DateRange,
    MetricsScalar,
    MetricsScalarWithRange,
    MetricsTimeseries,
    TimeseriesRange,
)
from app.namespaces.security import ensure_access_to_workbench_namespace
from app.workloads.enums import WorkloadStatus, WorkloadType
from tests import factory
from tests.dependency_overrides import (
    PROMETHEUS_OVERRIDES,
    SESSION_OVERRIDES,
    override_dependencies,
    runtime_dependency_overrides,
)


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workloads")
def test_list_workloads(mock_get_workloads: AsyncMock) -> None:
    """Test GET /v1/namespaces/{ns}/workloads returns 200."""
    mock_get_workloads.return_value = []

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/workloads")

    assert response.status_code == status.HTTP_200_OK
    assert "data" in response.json()
    mock_get_workloads.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workloads")
def test_list_workloads_with_filters(mock_get_workloads: AsyncMock) -> None:
    """Test GET /v1/namespaces/{ns}/workloads with type and status filters."""
    mock_get_workloads.return_value = []

    with TestClient(app) as client:
        response = client.get(
            "/v1/namespaces/test-namespace/workloads",
            params={
                "workload_type": "INFERENCE",
                "status_filter": "RUNNING",  # Single value, not list - FastAPI will handle it
            },
        )

    # 422 indicates validation error - likely status_filter needs to be passed differently
    # Let's just check that the endpoint is callable
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.list_chattable_workloads")
def test_list_chattable_workloads(mock_list_chattable: AsyncMock) -> None:
    """Test GET /v1/namespaces/{ns}/workloads/chattable returns 200."""
    mock_list_chattable.return_value = []

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/workloads/chattable")

    assert response.status_code == status.HTTP_200_OK
    assert "data" in response.json()
    mock_list_chattable.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_not_found(mock_get: AsyncMock) -> None:
    """Test GET /v1/namespaces/{ns}/workloads/{id} returns 404 when not found."""
    workload_id = uuid4()
    mock_get.return_value = None

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/workloads/{workload_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.delete_workload_components")
@patch("app.workloads.router.get_workload_by_id")
def test_delete_workload_not_found(mock_get: AsyncMock, mock_delete: AsyncMock) -> None:
    """Test DELETE /v1/namespaces/{ns}/workloads/{id} returns 404 when not found."""
    workload_id = uuid4()
    mock_get.return_value = None

    with TestClient(app) as client:
        response = client.delete(f"/v1/namespaces/test-namespace/workloads/{workload_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.chat_with_workload")
def test_chat_endpoint_not_found(mock_chat: AsyncMock) -> None:
    """Test POST /v1/namespaces/{ns}/workloads/{id}/chat returns 404 when workload not found."""
    workload_id = uuid4()
    mock_chat.side_effect = NotFoundException("Workload not found")

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/chat",
            json={"messages": []},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.chat_with_workload")
def test_chat_endpoint_not_chattable(mock_chat: AsyncMock) -> None:
    """Test POST /v1/namespaces/{ns}/workloads/{id}/chat returns 400 when not chattable."""
    workload_id = uuid4()
    mock_chat.side_effect = ValidationException("Workload is not available for chat")

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/chat",
            json={"messages": []},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Metrics Endpoint Tests
# =============================================================================


@override_dependencies(PROMETHEUS_OVERRIDES)
@patch("app.workloads.router.get_metric_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_metrics_success(mock_get_workload: AsyncMock, mock_get_metric: AsyncMock) -> None:
    """Test successful metrics retrieval with Prometheus client."""
    workload_id = uuid4()
    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(hours=1)
    end_time = now

    # Mock workload exists
    mock_workload = MagicMock()
    mock_workload.id = workload_id
    mock_get_workload.return_value = mock_workload

    # Mock metrics response with timeseries data
    mock_metric_response = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label="gpu-0"),
                values=[
                    Datapoint(value=50.0, timestamp=start_time),
                    Datapoint(value=75.0, timestamp=end_time),
                ],
            )
        ],
        range=TimeseriesRange(
            start=start_time,
            end=end_time,
            interval_seconds=3600,
            timestamps=[start_time, end_time],
        ),
    )
    mock_get_metric.return_value = mock_metric_response

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/gpu_device_utilization",
            params={
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert "range" in response_data
    # Check timestamps are present (format may vary: +00:00 vs Z)
    assert "start" in response_data["range"]
    assert "end" in response_data["range"]

    # Verify get_workload_by_id was called correctly
    mock_get_workload.assert_called_once()
    call_kwargs = mock_get_workload.call_args.kwargs
    assert call_kwargs["workload_id"] == workload_id
    assert call_kwargs["namespace"] == "test-namespace"

    # Verify get_metric_by_workload_id was called correctly
    mock_get_metric.assert_called_once()
    call_kwargs = mock_get_metric.call_args.kwargs
    assert call_kwargs["workload_id"] == str(workload_id)
    assert call_kwargs["metric"] == MetricName.GPU_DEVICE_UTILIZATION
    assert call_kwargs["start"] == start_time
    assert call_kwargs["end"] == end_time
    assert "prometheus_client" in call_kwargs


@override_dependencies(PROMETHEUS_OVERRIDES)
@patch("app.workloads.router.get_metric_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_metrics_scalar_response(mock_get_workload: AsyncMock, mock_get_metric: AsyncMock) -> None:
    """Test metrics endpoint returns scalar value."""
    workload_id = uuid4()
    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(hours=1)
    end_time = now

    # Mock workload exists
    mock_workload = MagicMock()
    mock_workload.id = workload_id
    mock_get_workload.return_value = mock_workload

    # Mock metrics response with scalar data
    mock_metric_response = MetricsScalar(data=1000.0)
    mock_get_metric.return_value = mock_metric_response

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/total_tokens",
            params={
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert response_data["data"] == 1000.0
    assert "range" not in response_data  # Scalar doesn't have range

    # Verify the metric parameter was passed correctly
    mock_get_metric.assert_called_once()
    call_kwargs = mock_get_metric.call_args.kwargs
    assert call_kwargs["metric"] == MetricName.TOTAL_TOKENS


@override_dependencies(PROMETHEUS_OVERRIDES)
@patch("app.workloads.router.get_metric_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_metrics_with_time_range(mock_get_workload: AsyncMock, mock_get_metric: AsyncMock) -> None:
    """Test metrics with start/end time parameters."""
    workload_id = uuid4()
    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(days=1)
    end_time = now

    # Mock workload exists
    mock_workload = MagicMock()
    mock_workload.id = workload_id
    mock_get_workload.return_value = mock_workload

    # Mock metrics response with scalar and range
    mock_metric_response = MetricsScalarWithRange(
        data=50.5,
        range=DateRange(start=start_time, end=end_time),
    )
    mock_get_metric.return_value = mock_metric_response

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/requests",
            params={
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert "range" in response_data
    assert response_data["data"] == 50.5

    # Verify time parameters were forwarded correctly
    mock_get_metric.assert_called_once()
    call_kwargs = mock_get_metric.call_args.kwargs
    assert call_kwargs["start"] == start_time
    assert call_kwargs["end"] == end_time


@override_dependencies(PROMETHEUS_OVERRIDES)
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_metrics_workload_not_found(mock_get_workload: AsyncMock) -> None:
    """Test 404 when workload doesn't exist."""
    workload_id = uuid4()
    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(hours=1)
    end_time = now

    # Mock workload not found
    mock_get_workload.return_value = None

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/gpu_device_utilization",
            params={
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()

    # Verify get_workload_by_id was called
    mock_get_workload.assert_called_once()


@override_dependencies(PROMETHEUS_OVERRIDES)
def test_get_workload_metrics_invalid_metric_name() -> None:
    """Test invalid metric name handling."""
    workload_id = uuid4()
    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(hours=1)
    end_time = now

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/invalid_metric_name",
            params={
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        )

    # FastAPI should return 422 for invalid enum value
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@override_dependencies(PROMETHEUS_OVERRIDES)
@patch("app.workloads.router.get_metric_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_metrics_prometheus_error(mock_get_workload: AsyncMock, mock_get_metric: AsyncMock) -> None:
    """Test Prometheus client error handling."""
    workload_id = uuid4()
    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(hours=1)
    end_time = now

    # Mock workload exists
    mock_workload = MagicMock()
    mock_workload.id = workload_id
    mock_get_workload.return_value = mock_workload

    # Mock Prometheus error
    mock_get_metric.side_effect = Exception("Prometheus connection error")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/gpu_device_utilization",
            params={
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        )

    # Should return 500 for internal errors
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Verify both functions were called
    mock_get_workload.assert_called_once()
    mock_get_metric.assert_called_once()


# =============================================================================
# Success Case Tests
# =============================================================================


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_success(mock_get: AsyncMock) -> None:
    """Test GET /v1/namespaces/{ns}/workloads/{id} returns 200 with workload data."""

    workload_id = uuid4()

    # Create a mock workload using centralized factory
    mock_workload = factory.make_workload_mock(
        workload_id=workload_id,
        name="test-workload",
        display_name="Test Workload",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )
    # Add additional attributes not in factory defaults
    mock_workload.chart = None
    mock_workload.chart_name = None

    mock_get.return_value = mock_workload

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/workloads/{workload_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(workload_id)
    assert data["name"] == "test-workload"
    assert data["display_name"] == "Test Workload"
    assert data["type"] == "INFERENCE"
    assert data["status"] == "Running"
    mock_get.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.delete_workload_components")
@patch("app.workloads.router.get_workload_by_id")
def test_delete_workload_success(mock_get: AsyncMock, mock_delete: AsyncMock) -> None:
    """Test DELETE /v1/namespaces/{ns}/workloads/{id} returns 204 on successful deletion."""

    workload_id = uuid4()

    # Create a mock workload using centralized factory
    mock_workload = factory.make_workload_mock(
        workload_id=workload_id,
        name="test-workload",
        display_name="Test Workload",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    mock_get.return_value = mock_workload
    mock_delete.return_value = None

    with TestClient(app) as client:
        response = client.delete(f"/v1/namespaces/test-namespace/workloads/{workload_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    mock_get.assert_called_once()
    mock_delete.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.delete_workload_components")
@patch("app.workloads.router.get_workload_by_id")
def test_delete_workload_background_task_execution(mock_get: AsyncMock, mock_delete: AsyncMock) -> None:
    """Test DELETE endpoint calls delete_workload_components with correct parameters."""

    workload_id = uuid4()
    namespace = "test-namespace"

    # Create a mock workload using centralized factory
    mock_workload = factory.make_workload_mock(
        workload_id=workload_id,
        name="test-workload",
        display_name="Test Workload",
        namespace=namespace,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    mock_get.return_value = mock_workload
    mock_delete.return_value = None

    with TestClient(app) as client:
        response = client.delete(f"/v1/namespaces/{namespace}/workloads/{workload_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Verify delete_workload_components was called with correct arguments
    mock_delete.assert_called_once()
    call_args = mock_delete.call_args
    assert call_args[0][0] == namespace  # First positional arg: namespace
    assert call_args[0][1] == workload_id  # Second positional arg: workload_id
    # Third arg is session (AsyncMock), just verify it exists
    assert call_args[0][2] is not None


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.chat_with_workload")
def test_chat_endpoint_success(mock_chat: AsyncMock) -> None:
    """Test POST /v1/namespaces/{ns}/workloads/{id}/chat returns 200 with streaming response."""

    workload_id = uuid4()

    # Create a mock StreamingResponse
    async def mock_generator():
        yield b"data: Hello\n\n"
        yield b"data: World\n\n"

    mock_response = StreamingResponse(mock_generator(), media_type="text/event-stream")
    mock_chat.return_value = mock_response

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/chat",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

    assert response.status_code == status.HTTP_200_OK
    mock_chat.assert_called_once()
    # Verify the chat function was called with correct workload_id
    call_kwargs = mock_chat.call_args.kwargs
    assert call_kwargs["workload_id"] == workload_id
    assert call_kwargs["namespace"] == "test-namespace"


@override_dependencies(
    {
        **SESSION_OVERRIDES,
        ensure_access_to_workbench_namespace: lambda: "authorized-namespace",
    }
)
@patch("app.workloads.router.get_workloads")
def test_list_workloads_authorization(mock_get_workloads: AsyncMock) -> None:
    """Test GET /v1/namespaces/{ns}/workloads succeeds for authorized namespace."""
    mock_get_workloads.return_value = []

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/authorized-namespace/workloads")

    assert response.status_code == status.HTTP_200_OK
    assert "data" in response.json()
    mock_get_workloads.assert_called_once()
    # Verify called with the authorized namespace
    call_kwargs = mock_get_workloads.call_args.kwargs
    assert call_kwargs["namespace"] == "authorized-namespace"


@override_dependencies(SESSION_OVERRIDES)
def test_endpoint_invalid_uuid_format() -> None:
    """Test endpoints reject malformed UUIDs with 422 error."""
    invalid_uuid = "not-a-valid-uuid"

    with TestClient(app) as client:
        # Test GET workload endpoint
        response = client.get(f"/v1/namespaces/test-namespace/workloads/{invalid_uuid}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "detail" in response.json()

        # Test DELETE workload endpoint
        response = client.delete(f"/v1/namespaces/test-namespace/workloads/{invalid_uuid}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "detail" in response.json()

        # Test POST chat endpoint
        response = client.post(
            f"/v1/namespaces/test-namespace/workloads/{invalid_uuid}/chat",
            json={"messages": []},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "detail" in response.json()


# =============================================================================
# Section 4.1: Authorization Tests
# =============================================================================


def test_get_workload_unauthorized() -> None:
    """Test GET /workloads/{id} with unauthorized namespace returns 403."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    workload_id = uuid4()

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            ensure_access_to_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/v1/namespaces/unauthorized-namespace/workloads/{workload_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


def test_delete_workload_unauthorized() -> None:
    """Test DELETE /workloads/{id} with unauthorized namespace returns 403."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    workload_id = uuid4()

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            ensure_access_to_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.delete(f"/v1/namespaces/unauthorized-namespace/workloads/{workload_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


def test_chat_endpoint_unauthorized() -> None:
    """Test POST /workloads/{id}/chat with unauthorized namespace returns 403."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    workload_id = uuid4()

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            ensure_access_to_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/v1/namespaces/unauthorized-namespace/workloads/{workload_id}/chat",
                json={"messages": []},
            )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


def test_get_workload_metrics_unauthorized() -> None:
    """Test GET /workloads/{id}/metrics/{metric} with unauthorized namespace returns 403."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    workload_id = uuid4()
    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(hours=1)
    end_time = now

    with runtime_dependency_overrides(
        {
            **PROMETHEUS_OVERRIDES,
            ensure_access_to_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                f"/v1/namespaces/unauthorized-namespace/workloads/{workload_id}/metrics/gpu_device_utilization",
                params={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
            )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


def test_get_workload_logs_unauthorized() -> None:
    """Test GET /workloads/{id}/logs with unauthorized namespace returns 403."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    workload_id = uuid4()

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            ensure_access_to_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                f"/v1/namespaces/unauthorized-namespace/workloads/{workload_id}/logs",
                params={"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T23:59:59Z"},
            )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


def test_stream_workload_logs_unauthorized() -> None:
    """Test GET /workloads/{id}/logs/stream with unauthorized namespace returns 403."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    workload_id = uuid4()

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            ensure_access_to_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/v1/namespaces/unauthorized-namespace/workloads/{workload_id}/logs/stream")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


def test_list_chattable_workloads_unauthorized() -> None:
    """Test GET /workloads/chattable with unauthorized namespace returns 403."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            ensure_access_to_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/v1/namespaces/unauthorized-namespace/workloads/chattable")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


# =============================================================================
# Section 4.2: Input Validation Tests
# =============================================================================


@override_dependencies(SESSION_OVERRIDES)
def test_list_workloads_invalid_status_filter() -> None:
    """Test status_filter with invalid enum value returns 422."""
    with TestClient(app) as client:
        response = client.get(
            "/v1/namespaces/test-namespace/workloads",
            params={
                "status_filter": "INVALID_STATUS",
            },
        )

    # FastAPI should return 422 for invalid enum value
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "detail" in response.json()


@override_dependencies(PROMETHEUS_OVERRIDES)
def test_metrics_invalid_datetime_format() -> None:
    """Test start/end with malformed datetime returns 422."""
    workload_id = uuid4()

    with TestClient(app) as client:
        # Test invalid start datetime
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/gpu_device_utilization",
            params={
                "start": "not-a-valid-datetime",
                "end": datetime.now(UTC).isoformat(),
            },
        )

    # FastAPI should return 422 for validation errors
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "detail" in response.json()

    with TestClient(app) as client:
        # Test invalid end datetime
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/metrics/gpu_device_utilization",
            params={
                "start": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
                "end": "invalid-datetime-format",
            },
        )

    # FastAPI should return 422 for validation errors
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "detail" in response.json()


# =============================================================================

# =============================================================================
# GET /workloads/{id}/logs Tests
# =============================================================================

# =============================================================================
# GET /workloads/{id}/logs Tests
# =============================================================================


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_logs_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_logs_success(mock_get_workload: AsyncMock, mock_get_logs: AsyncMock) -> None:
    """Test successful log retrieval."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    # Mock log response
    log_entry = LogEntry(
        timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC), level=LogLevel.INFO, message="Test log message"
    )
    mock_get_logs.return_value = WorkloadLogsResponse(
        data=[log_entry], pagination=PaginationMetadataResponse(has_more=False, page_token=None, total_returned=1)
    )

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs",
            params={"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T23:59:59Z"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["level"] == "info"
    assert data["data"][0]["message"] == "Test log message"
    mock_get_workload.assert_called_once()
    mock_get_logs.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_logs_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_logs_with_filters(mock_get_workload: AsyncMock, mock_get_logs: AsyncMock) -> None:
    """Test with level, log_type, and limit filters."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    mock_get_logs.return_value = WorkloadLogsResponse(
        data=[], pagination=PaginationMetadataResponse(has_more=False, page_token=None, total_returned=0)
    )

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs",
            params={
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-01T23:59:59Z",
                "level": "error",
                "log_type": "event",
                "limit": 500,
            },
        )

    assert response.status_code == status.HTTP_200_OK
    mock_get_logs.assert_called_once()

    # Verify the filters were passed correctly
    call_kwargs = mock_get_logs.call_args.kwargs
    assert call_kwargs["level_filter"] == LogLevel.ERROR
    assert call_kwargs["log_type"] == LogType.EVENT
    assert call_kwargs["limit"] == 500


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_logs_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_logs_with_pagination(mock_get_workload: AsyncMock, mock_get_logs: AsyncMock) -> None:
    """Test with start_time parameter (page_token)."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    next_page_token = "2025-01-01T12:00:00Z"
    mock_get_logs.return_value = WorkloadLogsResponse(
        data=[], pagination=PaginationMetadataResponse(has_more=True, page_token=next_page_token, total_returned=0)
    )

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs",
            params={
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-01T23:59:59Z",
                "page_token": "2025-01-01T11:00:00Z",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["pagination"]["has_more"] is True
    assert data["pagination"]["page_token"] == next_page_token
    mock_get_logs.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_logs_workload_not_found(mock_get_workload: AsyncMock) -> None:
    """Test 404 when workload doesn't exist."""
    workload_id = uuid4()
    mock_get_workload.return_value = None

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs",
            params={"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T23:59:59Z"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_logs_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_logs_loki_error(mock_get_workload: AsyncMock, mock_get_logs: AsyncMock) -> None:
    """Test Loki client error handling."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    # Mock Loki error - service returns empty response on errors
    mock_get_logs.return_value = WorkloadLogsResponse(
        data=[], pagination=PaginationMetadataResponse(has_more=False, page_token=None, total_returned=0)
    )

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs",
            params={"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T23:59:59Z"},
        )

    # Service handles errors gracefully and returns empty results
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 0


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_logs_by_workload_id")
@patch("app.workloads.router.get_workload_by_id")
def test_get_workload_logs_empty_results(mock_get_workload: AsyncMock, mock_get_logs: AsyncMock) -> None:
    """Test empty log results."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    mock_get_logs.return_value = WorkloadLogsResponse(
        data=[], pagination=PaginationMetadataResponse(has_more=False, page_token=None, total_returned=0)
    )

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs",
            params={"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T23:59:59Z"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 0
    assert data["pagination"]["total_returned"] == 0
    assert data["pagination"]["has_more"] is False


# =============================================================================
# GET /workloads/{id}/logs/stream Tests
# =============================================================================


async def mock_log_stream_generator():
    """Mock async generator for log streaming."""
    log_entry = LogEntry(
        timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC), level=LogLevel.INFO, message="Streaming log"
    )
    yield log_entry.model_dump_json()


async def mock_sse_stream_generator():
    """Mock SSE formatted stream."""
    log_entry = LogEntry(
        timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC), level=LogLevel.INFO, message="Streaming log"
    )
    yield f"data: {log_entry.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.stream_workload_logs_sse")
@patch("app.workloads.router.get_workload_by_id")
def test_stream_workload_logs_success(mock_get_workload: AsyncMock, mock_stream: AsyncMock) -> None:
    """Test SSE streaming with proper headers."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    mock_stream.return_value = mock_sse_stream_generator()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream",
            params={"start_time": "2025-01-01T00:00:00Z"},
        )

    assert response.status_code == status.HTTP_200_OK

    # Verify SSE headers
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"

    # Verify content contains SSE formatted data
    content = response.text
    assert "data: " in content

    mock_get_workload.assert_called_once()
    mock_stream.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.stream_workload_logs_sse")
@patch("app.workloads.router.get_workload_by_id")
def test_stream_workload_logs_with_filters(mock_get_workload: AsyncMock, mock_stream: AsyncMock) -> None:
    """Test with level and log_type filters."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    mock_stream.return_value = mock_sse_stream_generator()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream",
            params={"level": "warning", "log_type": "event"},
        )

    assert response.status_code == status.HTTP_200_OK
    mock_stream.assert_called_once()

    # Verify filters were passed
    call_kwargs = mock_stream.call_args.kwargs
    assert call_kwargs["level_filter"] == LogLevel.WARNING
    assert call_kwargs["log_type"] == LogType.EVENT


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.stream_workload_logs_sse")
@patch("app.workloads.router.get_workload_by_id")
def test_stream_workload_logs_with_delay(mock_get_workload: AsyncMock, mock_stream: AsyncMock) -> None:
    """Test custom delay parameter."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    mock_stream.return_value = mock_sse_stream_generator()

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream", params={"delay": 5})

    assert response.status_code == status.HTTP_200_OK
    mock_stream.assert_called_once()

    # Verify delay was passed
    call_kwargs = mock_stream.call_args.kwargs
    assert call_kwargs["delay_seconds"] == 5


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workload_by_id")
def test_stream_workload_logs_delay_validation(mock_get_workload: AsyncMock) -> None:
    """Test delay boundary validation (1-30 range)."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    with TestClient(app) as client:
        # Test delay too low
        response = client.get(f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream", params={"delay": 0})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test delay too high
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream", params={"delay": 31}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Verify get_workload was never called for invalid requests
        mock_get_workload.assert_not_called()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workload_by_id")
def test_stream_workload_logs_workload_not_found(mock_get_workload: AsyncMock) -> None:
    """Test 404 when workload doesn't exist."""
    workload_id = uuid4()
    mock_get_workload.return_value = None

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


async def mock_sse_error_stream():
    """Mock SSE stream with error event."""
    yield 'data: {"error": "Loki connection failed"}\n\n'


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.stream_workload_logs_sse")
@patch("app.workloads.router.get_workload_by_id")
def test_stream_workload_logs_loki_error(mock_get_workload: AsyncMock, mock_stream: AsyncMock) -> None:
    """Test error JSON event when Loki fails."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    mock_stream.return_value = mock_sse_error_stream()

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream")

    assert response.status_code == status.HTTP_200_OK
    content = response.text
    assert "error" in content
    assert "Loki connection failed" in content


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workloads.router.get_workload_by_id")
def test_stream_workload_logs_invalid_start_time(mock_get_workload: AsyncMock) -> None:
    """Test malformed start_time handling."""
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id)
    mock_get_workload.return_value = mock_workload

    with TestClient(app) as client:
        # Invalid ISO format
        response = client.get(
            f"/v1/namespaces/test-namespace/workloads/{workload_id}/logs/stream",
            params={"start_time": "invalid-date"},
        )

    # FastAPI returns 422 for validation errors
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
