# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for namespaces router endpoints using FastAPI TestClient with dependency overrides."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from prometheus_api_client import PrometheusConnect

from api_common.auth.security import get_user_groups
from app import app  # type: ignore[attr-defined]
from app.metrics.client import get_prometheus_client
from app.metrics.enums import NamespaceMetricName
from app.metrics.schemas import (
    Datapoint,
    DatapointMetadataBase,
    DatapointsWithMetadata,
    MetricsTimeseries,
    TimeseriesRange,
)
from app.namespaces.crds import Namespace
from app.namespaces.schemas import (
    ChattableResponse,
    NamespaceWorkloadMetricsListPaginated,
)
from app.namespaces.security import get_workbench_namespace
from app.workloads.enums import WorkloadStatus
from tests.dependency_overrides import (
    BASE_OVERRIDES,
    SESSION_OVERRIDES,
    override_dependencies,
    runtime_dependency_overrides,
)
from tests.factory import (
    make_namespace_crd,
    make_namespace_stats_counts,
    make_namespace_workload_metrics,
)


@override_dependencies(
    {
        **BASE_OVERRIDES,
        get_user_groups: lambda: ["namespace-1", "namespace-2"],
    }
)
@patch("app.namespaces.router.get_accessible_namespaces", autospec=True)
def test_list_namespaces(mock_get_namespaces: AsyncMock) -> None:
    """Test GET /namespaces returns list of accessible namespaces."""
    mock_namespace1 = MagicMock(spec=Namespace)
    mock_namespace1.name = "namespace-1"
    mock_namespace2 = MagicMock(spec=Namespace)
    mock_namespace2.name = "namespace-2"
    mock_get_namespaces.return_value = [mock_namespace1, mock_namespace2]

    with TestClient(app) as client:
        response = client.get("/v1/namespaces")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    assert "namespace-1" in data["data"]
    assert "namespace-2" in data["data"]
    mock_get_namespaces.assert_called_once()


@override_dependencies(
    {
        **BASE_OVERRIDES,
        get_user_groups: lambda: ["namespace-1", "namespace-2"],
    }
)
@patch("app.namespaces.router.get_accessible_namespaces", autospec=True)
def test_list_namespaces_empty(mock_get_namespaces: AsyncMock) -> None:
    """Test GET /namespaces returns empty list when no namespaces are accessible."""
    mock_get_namespaces.return_value = []

    with TestClient(app) as client:
        response = client.get("/v1/namespaces")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 0
    mock_get_namespaces.assert_called_once()


def test_get_namespace_metrics() -> None:
    """Test GET /namespaces/{namespace}/metrics returns paginated metrics."""
    mock_namespace = make_namespace_crd(
        name="test-namespace",
        labels={"project-id": "test-project"},
    )

    mock_metric = make_namespace_workload_metrics(
        name="test-workload",
        display_name="Test Workload",
        status=WorkloadStatus.RUNNING,
    )
    mock_response = NamespaceWorkloadMetricsListPaginated(
        data=[mock_metric],
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
    )

    with (
        runtime_dependency_overrides(
            {
                **SESSION_OVERRIDES,
                get_workbench_namespace: lambda: mock_namespace,
            }
        ),
        patch("app.namespaces.router.get_namespace_workload_metrics_paginated", autospec=True) as mock_get_metrics,
    ):
        mock_get_metrics.return_value = mock_response

        with TestClient(app) as client:
            response = client.get("/v1/namespaces/test-namespace/metrics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "test-workload"
    assert data["total"] == 1
    mock_get_metrics.assert_called_once()


def test_get_namespace_metrics_with_pagination() -> None:
    """Test GET /namespaces/{namespace}/metrics with pagination parameters."""
    mock_namespace = make_namespace_crd(
        name="test-namespace",
        labels={"project-id": "test-project"},
    )

    mock_response = NamespaceWorkloadMetricsListPaginated(
        data=[],
        total=0,
        page=2,
        page_size=50,
        total_pages=0,
    )

    with (
        runtime_dependency_overrides(
            {
                **SESSION_OVERRIDES,
                get_workbench_namespace: lambda: mock_namespace,
            }
        ),
        patch("app.namespaces.router.get_namespace_workload_metrics_paginated", autospec=True) as mock_get_metrics,
    ):
        mock_get_metrics.return_value = mock_response

        with TestClient(app) as client:
            response = client.get(
                "/v1/namespaces/test-namespace/metrics",
                params={"page": 2, "pageSize": 50},
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["page"] == 2
    assert data["pageSize"] == 50
    mock_get_metrics.assert_called_once()
    call_kwargs = mock_get_metrics.call_args.kwargs
    assert call_kwargs["page"] == 2
    assert call_kwargs["page_size"] == 50


def test_get_namespace_metrics_invalid_pagination() -> None:
    """Test GET /namespaces/{namespace}/metrics with invalid pagination parameters."""
    mock_namespace = make_namespace_crd(
        name="test-namespace",
        labels={"project-id": "test-project"},
    )

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            get_workbench_namespace: lambda: mock_namespace,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            # Test with page < 1
            response = client.get(
                "/v1/namespaces/test-namespace/metrics",
                params={"page": 0},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test with pageSize < 1
            response = client.get(
                "/v1/namespaces/test-namespace/metrics",
                params={"pageSize": 0},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_namespace_stats() -> None:
    """Test GET /namespaces/{namespace}/stats returns resource counts."""
    mock_namespace = make_namespace_crd(
        name="test-namespace",
        labels={"project-id": "test-project"},
    )

    mock_stats = make_namespace_stats_counts(
        namespace="test-namespace",
    )

    with (
        runtime_dependency_overrides(
            {
                **SESSION_OVERRIDES,
                get_workbench_namespace: lambda: mock_namespace,
            }
        ),
        patch("app.namespaces.router.get_namespace_stats_counts", autospec=True) as mock_get_stats,
    ):
        mock_get_stats.return_value = mock_stats

        with TestClient(app) as client:
            response = client.get("/v1/namespaces/test-namespace/stats")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["namespace"] == "test-namespace"
    assert data["total"] == 5
    assert len(data["statusCounts"]) == 2
    mock_get_stats.assert_called_once()


def test_get_namespace_metric() -> None:
    """Test GET /namespaces/{namespace}/metrics/{metric} returns timeseries data."""
    mock_namespace = make_namespace_crd(
        name="test-namespace",
        labels={"project-id": "test-project"},
    )

    now = datetime.now(UTC).replace(microsecond=0)
    start_time = now - timedelta(hours=1)
    end_time = now

    mock_response = MetricsTimeseries(
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

    with (
        runtime_dependency_overrides(
            {
                **SESSION_OVERRIDES,
                get_workbench_namespace: lambda: mock_namespace,
                get_prometheus_client: lambda: MagicMock(spec=PrometheusConnect),
            }
        ),
        patch("app.namespaces.router.get_metric_by_namespace", autospec=True) as mock_get_metric,
    ):
        mock_get_metric.return_value = mock_response

        with TestClient(app) as client:
            response = client.get(
                "/v1/namespaces/test-namespace/metrics/gpu_device_utilization",
                params={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert "range" in data
    mock_get_metric.assert_called_once()
    call_kwargs = mock_get_metric.call_args.kwargs
    assert call_kwargs["metric"] == NamespaceMetricName.GPU_DEVICE_UTILIZATION


def test_get_namespace_metric_with_milliseconds() -> None:
    """Test GET /namespaces/{namespace}/metrics/{metric} works with non-zero milliseconds in timestamps."""
    mock_namespace = make_namespace_crd(
        name="test-namespace",
        labels={"project-id": "test-project"},
    )

    now = datetime.now(UTC)
    start_time = now.replace(microsecond=123456) - timedelta(hours=1)
    end_time = now.replace(microsecond=987654)

    mock_response = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label="gpu-0"),
                values=[
                    Datapoint(value=50.0, timestamp=start_time.replace(microsecond=0)),
                    Datapoint(value=75.0, timestamp=end_time.replace(microsecond=0)),
                ],
            )
        ],
        range=TimeseriesRange(
            start=start_time,
            end=end_time,
            interval_seconds=3600,
            timestamps=[start_time.replace(microsecond=0), end_time.replace(microsecond=0)],
        ),
    )

    with (
        runtime_dependency_overrides(
            {
                **SESSION_OVERRIDES,
                get_workbench_namespace: lambda: mock_namespace,
                get_prometheus_client: lambda: MagicMock(spec=PrometheusConnect),
            }
        ),
        patch("app.namespaces.router.get_metric_by_namespace", autospec=True) as mock_get_metric,
    ):
        mock_get_metric.return_value = mock_response

        with TestClient(app) as client:
            response = client.get(
                "/v1/namespaces/test-namespace/metrics/gpu_device_utilization",
                params={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert "range" in data
    mock_get_metric.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.namespaces.router.get_chattable_resources", autospec=True)
def test_get_chattable_resources(mock_get_chattable: AsyncMock) -> None:
    """Test GET /namespaces/{namespace}/chattable returns AIM services and workloads."""
    mock_response = ChattableResponse(
        aim_services=[],
        workloads=[],
    )
    mock_get_chattable.return_value = mock_response

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/chattable")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "aimServices" in data
    assert "workloads" in data
    mock_get_chattable.assert_called_once()


def test_get_namespace_metrics_unauthorized() -> None:
    """Test GET /namespaces/{namespace}/metrics returns 403 for unauthorized access."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            get_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/v1/namespaces/unauthorized-namespace/metrics")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()


def test_get_namespace_stats_unauthorized() -> None:
    """Test GET /namespaces/{namespace}/stats returns 403 for unauthorized access."""

    def mock_unauthorized_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to namespace 'unauthorized-namespace'",
        )

    with runtime_dependency_overrides(
        {
            **SESSION_OVERRIDES,
            get_workbench_namespace: mock_unauthorized_access,
        }
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/v1/namespaces/unauthorized-namespace/stats")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "access" in response.json()["detail"].lower()
