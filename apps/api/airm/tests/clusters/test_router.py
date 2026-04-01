# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import app  # type: ignore
from app.clusters.models import Cluster, ClusterNode
from app.clusters.schemas import (
    ClusterIn,
    ClusterKubeConfig,
    ClusterNodeResponse,
    ClusterNodes,
    ClusterResources,
    Clusters,
    ClustersStats,
    ClusterWithResources,
    ClusterWithUserSecret,
    GPUInfo,
)
from app.messaging.schemas import GPUVendor, QuotaStatus, WorkloadStatus
from app.metrics.schemas import (
    Datapoint,
    DatapointsWithMetadata,
    DeviceMetricTimeseries,
    GpuDeviceSingleMetricResponse,
    GpuDeviceWithSingleMetric,
    MetricsTimeRange,
    MetricsTimeseries,
    NodeGpuDevice,
    NodeGpuDevicesResponse,
    NodeWorkloadsWithMetrics,
    NodeWorkloadWithMetrics,
    ProjectDatapointMetadata,
    TimeseriesRange,
    WorkloadGpuDevice,
    WorkloadsWithMetrics,
    WorkloadWithMetrics,
)
from app.projects.enums import ProjectStatus
from app.projects.schemas import ProjectResponse, ProjectsWithResourceAllocation, ProjectWithResourceAllocation
from app.quotas.schemas import QuotaResponse
from app.utilities.exceptions import ForbiddenException, NotFoundException
from app.workloads.enums import WorkloadType
from app.workloads.schemas import WorkloadStatusCount, WorkloadStatusStats
from tests.dependency_overrides import (
    ADMIN_FORBIDDEN_OVERRIDES,
    ADMIN_OVERRIDES,
    ADMIN_SESSION_FORBIDDEN_OVERRIDES,
    ADMIN_SESSION_OVERRIDES,
    ADMIN_SESSION_WITH_USER_MOCK_OVERRIDES,
    ADMIN_WITH_USER_TRACKING_OVERRIDES,
    USER_CLUSTER_SESSION_OVERRIDES,
    USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES,
    USER_EMAIL_UNAUTHORIZED_OVERRIDES,
    USER_WITH_KEYCLOAK_ID_OVERRIDES,
    override_dependencies,
)

default_timeseries_metrics = MetricsTimeseries(
    data=[
        DatapointsWithMetadata(
            metadata=ProjectDatapointMetadata(
                label="default_label",
                project=ProjectResponse(
                    id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
                    name="project1",
                    description="project 1",
                    cluster_id=UUID("0aa22e92-002c-41b7-a06e-dcdb0244974c"),
                    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    status=ProjectStatus.PENDING,
                    status_reason="Creating",
                ),
            ),
            values=[
                Datapoint(value=0.1, timestamp=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC)),
                Datapoint(value=0.3, timestamp=datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC)),
            ],
        ),
        DatapointsWithMetadata(
            metadata=ProjectDatapointMetadata(
                label="default_label",
                project=ProjectResponse(
                    id=UUID("19465a28-1649-4f55-887f-536dd36a47f8"),
                    name="project2",
                    description="project 2",
                    cluster_id=UUID("1ab22e52-102c-31b7-a06e-dcdb0244974c"),
                    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    status=ProjectStatus.PENDING,
                    status_reason="Creating",
                ),
            ),
            values=[
                Datapoint(value=0.2, timestamp=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC)),
                Datapoint(value=0.4, timestamp=datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC)),
            ],
        ),
    ],
    range=TimeseriesRange(
        start=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        end=datetime(2025, 3, 11, 12, 0, 0, tzinfo=UTC),
        interval_seconds=60,
        timestamps=[
            datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
            datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC),
        ],
    ),
)


@pytest.mark.asyncio
@patch(
    "app.clusters.router.create_cluster_and_queues",
    return_value=ClusterWithUserSecret(
        id="08ccd4e0-3bef-480c-8e08-a21f47f51421",
        name="cluster1",
        user_secret="30495734986458367",
        last_heartbeat_at=None,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        workloads_base_url="https://example.com",
        kube_api_url="https://k8s.example.com",
    ),
)
@override_dependencies(ADMIN_OVERRIDES)
async def test_create_cluster_success(_: Any) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/clusters",
            json={"workloads_base_url": "https://example.com", "kube_api_url": "https://k8s.example.com"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": "08ccd4e0-3bef-480c-8e08-a21f47f51421",
        "name": "cluster1",
        "user_secret": "30495734986458367",
        "last_heartbeat_at": None,
        "status": "verifying",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
        "workloads_base_url": "https://example.com",
        "kube_api_url": "https://k8s.example.com",
    }


@pytest.mark.asyncio
@override_dependencies(USER_EMAIL_UNAUTHORIZED_OVERRIDES)
async def test_create_cluster_no_user() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/clusters", json={})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@override_dependencies(ADMIN_FORBIDDEN_OVERRIDES)
async def test_create_cluster_user_not_in_role() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/clusters", json={})

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.clusters.router.create_cluster_and_queues", side_effect=Exception())
@patch("app.utilities.database.session_maker", return_value=AsyncMock())
@override_dependencies(ADMIN_WITH_USER_TRACKING_OVERRIDES)
async def test_create_cluster_exception(session_maker_mock: MagicMock, __: Any) -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/v1/clusters", json={"workloads_base_url": "https://example.com"})
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    session_maker_mock().rollback.assert_called_once()


@pytest.mark.asyncio
@patch(
    "app.clusters.router.create_cluster_and_queues",
    return_value=ClusterWithUserSecret(
        id="08ccd4e0-3bef-480c-8e08-a21f47f51421",
        name="cluster1",
        user_secret="30495734986458367",
        last_heartbeat_at=None,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@override_dependencies(ADMIN_OVERRIDES)
async def test_create_cluster_no_base_url(_: Any) -> None:
    with TestClient(app) as client:
        response = client.post("/v1/clusters", json={})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": "08ccd4e0-3bef-480c-8e08-a21f47f51421",
        "name": "cluster1",
        "user_secret": "30495734986458367",
        "last_heartbeat_at": None,
        "status": "verifying",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
        "workloads_base_url": None,
        "kube_api_url": None,
    }


@pytest.mark.asyncio
@patch("app.clusters.schemas.datetime")
@patch("app.clusters.router.is_user_in_role", return_value=True)
@patch(
    "app.clusters.router.get_clusters_with_resources",
    return_value=Clusters(
        data=[
            ClusterWithResources(
                id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
                name="cluster1",
                last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                available_resources=ClusterResources(
                    cpu_milli_cores=4000,
                    memory_bytes=400 * (1024**3),
                    ephemeral_storage_bytes=100 * (1024**3),
                    gpu_count=8,
                ),
                allocated_resources=ClusterResources(
                    cpu_milli_cores=2000,
                    memory_bytes=200 * (1024**3),
                    ephemeral_storage_bytes=80 * (1024**3),
                    gpu_count=6,
                ),
                total_node_count=4,
                available_node_count=2,
                assigned_quota_count=2,
                gpu_info=GPUInfo(
                    vendor=GPUVendor.AMD, type="740c", name="Instinct MI250X", memory_bytes_per_device=64 * (1024**3)
                ),
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                workloads_base_url="https://example.com",
                kube_api_url="https://k8s.example.com",
            ),
            ClusterWithResources(
                id="0aa18e92-002c-45b7-a06e-dcdb0277974d",
                name="cluster2",
                available_resources=ClusterResources(
                    cpu_milli_cores=4000,
                    memory_bytes=400 * (1024**3),
                    ephemeral_storage_bytes=100 * (1024**3),
                    gpu_count=0,
                ),
                allocated_resources=ClusterResources(
                    cpu_milli_cores=2000,
                    memory_bytes=200 * (1024**3),
                    ephemeral_storage_bytes=80 * (1024**3),
                    gpu_count=0,
                ),
                total_node_count=4,
                available_node_count=2,
                assigned_quota_count=1,
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                workloads_base_url="https://example.com",
                kube_api_url="https://k8s.example.com",
            ),
        ]
    ),
)
@override_dependencies(USER_WITH_KEYCLOAK_ID_OVERRIDES)
@patch("app.clusters.router.is_user_in_role", return_value=True)
async def test_get_clusters_platform_admin_success(_: Any, __: Any, ___: Any, mock_datetime: MagicMock) -> None:
    mock_datetime.now.return_value = datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC)

    with TestClient(app) as client:
        response = client.get("/v1/clusters")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": [
            {
                "allocated_resources": {
                    "cpu_milli_cores": 2000,
                    "ephemeral_storage_bytes": 85899345920,
                    "gpu_count": 6,
                    "memory_bytes": 214748364800,
                },
                "assigned_quota_count": 2,
                "available_node_count": 2,
                "available_resources": {
                    "cpu_milli_cores": 4000,
                    "ephemeral_storage_bytes": 107374182400,
                    "gpu_count": 8,
                    "memory_bytes": 429496729600,
                },
                "gpu_info": {
                    "memory_bytes_per_device": 68719476736,
                    "name": "Instinct MI250X",
                    "type": "740c",
                    "vendor": "AMD",
                },
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "last_heartbeat_at": "2025-03-10T12:00:00Z",
                "name": "cluster1",
                "status": "healthy",
                "total_node_count": 4,
                "created_at": "2025-01-01T12:00:00Z",
                "priority_classes": [
                    {
                        "name": "low",
                        "priority": -100,
                    },
                    {
                        "name": "medium",
                        "priority": 0,
                    },
                    {
                        "name": "high",
                        "priority": 100,
                    },
                ],
                "gpu_allocation_percentage": 75.0,
                "cpu_allocation_percentage": 50.0,
                "memory_allocation_percentage": 50.0,
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
                "workloads_base_url": "https://example.com",
                "kube_api_url": "https://k8s.example.com",
            },
            {
                "allocated_resources": {
                    "cpu_milli_cores": 2000,
                    "ephemeral_storage_bytes": 85899345920,
                    "gpu_count": 0,
                    "memory_bytes": 214748364800,
                },
                "assigned_quota_count": 1,
                "available_node_count": 2,
                "available_resources": {
                    "cpu_milli_cores": 4000,
                    "ephemeral_storage_bytes": 107374182400,
                    "gpu_count": 0,
                    "memory_bytes": 429496729600,
                },
                "gpu_info": None,
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974d",
                "last_heartbeat_at": None,
                "name": "cluster2",
                "status": "verifying",
                "total_node_count": 4,
                "created_at": "2025-01-01T12:00:00Z",
                "priority_classes": [
                    {
                        "name": "low",
                        "priority": -100,
                    },
                    {
                        "name": "medium",
                        "priority": 0,
                    },
                    {
                        "name": "high",
                        "priority": 100,
                    },
                ],
                "gpu_allocation_percentage": 0.0,
                "cpu_allocation_percentage": 50.0,
                "memory_allocation_percentage": 50.0,
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
                "workloads_base_url": "https://example.com",
                "kube_api_url": "https://k8s.example.com",
            },
        ]
    }


@pytest.mark.asyncio
@patch("app.clusters.router.is_user_in_role", return_value=False)
@patch("app.clusters.router.get_projects_accessible_to_user", return_value=[])
@patch(
    "app.clusters.router.get_clusters_accessible_to_user_with_resources",
    return_value=Clusters(
        data=[
            ClusterWithResources(
                id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
                name="accessible_cluster",
                last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                available_resources=ClusterResources(
                    cpu_milli_cores=4000,
                    memory_bytes=400 * (1024**3),
                    ephemeral_storage_bytes=100 * (1024**3),
                    gpu_count=8,
                ),
                allocated_resources=ClusterResources(
                    cpu_milli_cores=2000,
                    memory_bytes=200 * (1024**3),
                    ephemeral_storage_bytes=80 * (1024**3),
                    gpu_count=4,
                ),
                total_node_count=2,
                available_node_count=2,
                assigned_quota_count=1,
                gpu_info=GPUInfo(
                    vendor=GPUVendor.AMD, type="740c", name="Instinct MI250X", memory_bytes_per_device=64 * (1024**3)
                ),
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                workloads_base_url="https://example.com",
                kube_api_url="https://k8s.example.com",
            ),
        ]
    ),
)
@override_dependencies(USER_WITH_KEYCLOAK_ID_OVERRIDES)
async def test_get_clusters_non_admin_success(_: Any, __: Any, ___: Any) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "accessible_cluster"
    assert data["data"][0]["available_resources"]["gpu_count"] == 8
    assert data["data"][0]["allocated_resources"]["gpu_count"] == 4


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        workloads_base_url="https://example.com",
        kube_api_url="https://k8s.example.com",
    ),
)
@pytest.mark.asyncio
@patch("app.clusters.router.is_user_in_role", return_value=True)
@patch(
    "app.clusters.router.get_cluster_with_resources",
    return_value=ClusterWithResources(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        available_resources=ClusterResources(
            cpu_milli_cores=4000, memory_bytes=400 * (1024**3), ephemeral_storage_bytes=100 * (1024**3), gpu_count=8
        ),
        allocated_resources=ClusterResources(
            cpu_milli_cores=2000, memory_bytes=200 * (1024**3), ephemeral_storage_bytes=80 * (1024**3), gpu_count=6
        ),
        total_node_count=4,
        available_node_count=2,
        assigned_quota_count=1,
        gpu_info=GPUInfo(
            vendor=GPUVendor.AMD, type="740c", name="Instinct MI250X", memory_bytes_per_device=64 * (1024**3)
        ),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        workloads_base_url="https://example.com",
        kube_api_url="https://k8s.example.com",
    ),
)
@override_dependencies(USER_WITH_KEYCLOAK_ID_OVERRIDES)
async def test_get_cluster_success(_: Any, __: Any, ___: Any) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "allocated_resources": {
            "cpu_milli_cores": 2000,
            "ephemeral_storage_bytes": 85899345920,
            "gpu_count": 6,
            "memory_bytes": 214748364800,
        },
        "assigned_quota_count": 1,
        "available_node_count": 2,
        "available_resources": {
            "cpu_milli_cores": 4000,
            "ephemeral_storage_bytes": 107374182400,
            "gpu_count": 8,
            "memory_bytes": 429496729600,
        },
        "gpu_info": {
            "memory_bytes_per_device": 68719476736,
            "name": "Instinct MI250X",
            "type": "740c",
            "vendor": "AMD",
        },
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "last_heartbeat_at": "2025-03-10T12:00:00Z",
        "name": "cluster1",
        "status": "unhealthy",
        "total_node_count": 4,
        "created_at": "2025-01-01T12:00:00Z",
        "priority_classes": [
            {
                "name": "low",
                "priority": -100,
            },
            {
                "name": "medium",
                "priority": 0,
            },
            {
                "name": "high",
                "priority": 100,
            },
        ],
        "gpu_allocation_percentage": 75.0,
        "cpu_allocation_percentage": 50.0,
        "memory_allocation_percentage": 50.0,
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
        "workloads_base_url": "https://example.com",
        "kube_api_url": "https://k8s.example.com",
    }


@pytest.mark.asyncio
@patch("app.clusters.router.is_user_in_role", return_value=False)
@patch("app.clusters.router.get_cluster_by_id", return_value=MagicMock(spec=Cluster))
@patch(
    "app.clusters.router.get_cluster_with_resources",
    return_value=ClusterWithResources(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        available_resources=ClusterResources(
            cpu_milli_cores=4000, memory_bytes=400 * (1024**3), ephemeral_storage_bytes=100 * (1024**3), gpu_count=8
        ),
        allocated_resources=ClusterResources(
            cpu_milli_cores=2000, memory_bytes=200 * (1024**3), ephemeral_storage_bytes=80 * (1024**3), gpu_count=6
        ),
        total_node_count=4,
        available_node_count=2,
        assigned_quota_count=2,
        gpu_info=GPUInfo(
            vendor=GPUVendor.AMD, type="740c", name="Instinct MI250X", memory_bytes_per_device=64 * (1024**3)
        ),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        workloads_base_url="https://example.com",
        kube_api_url="https://k8s.example.com",
    ),
)
@patch("app.clusters.router.validate_cluster_accessible_to_user")
@override_dependencies(USER_WITH_KEYCLOAK_ID_OVERRIDES)
async def test_get_cluster_team_member_success(_: Any, __: Any, ___: Any, ____: Any) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "allocated_resources": {
            "cpu_milli_cores": 2000,
            "ephemeral_storage_bytes": 85899345920,
            "gpu_count": 6,
            "memory_bytes": 214748364800,
        },
        "assigned_quota_count": 2,
        "available_node_count": 2,
        "available_resources": {
            "cpu_milli_cores": 4000,
            "ephemeral_storage_bytes": 107374182400,
            "gpu_count": 8,
            "memory_bytes": 429496729600,
        },
        "workloads_base_url": "https://example.com",
        "kube_api_url": "https://k8s.example.com",
        "created_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "gpu_info": {
            "memory_bytes_per_device": 68719476736,
            "name": "Instinct MI250X",
            "type": "740c",
            "vendor": "AMD",
        },
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "last_heartbeat_at": "2025-03-10T12:00:00Z",
        "name": "cluster1",
        "priority_classes": [
            {"name": "low", "priority": -100},
            {"name": "medium", "priority": 0},
            {"name": "high", "priority": 100},
        ],
        "gpu_allocation_percentage": 75.0,
        "cpu_allocation_percentage": 50.0,
        "memory_allocation_percentage": 50.0,
        "status": "unhealthy",
        "total_node_count": 4,
        "updated_at": "2025-01-01T12:00:00Z",
        "updated_by": "test@example.com",
    }


@pytest.mark.asyncio
@patch("app.clusters.router.is_user_in_role", return_value=False)
@patch("app.clusters.router.validate_cluster_accessible_to_user", side_effect=ForbiddenException("No access"))
@override_dependencies(USER_WITH_KEYCLOAK_ID_OVERRIDES)
async def test_get_cluster_team_member_no_access(_: Any, __: Any) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        workloads_base_url="https://example.com",
    ),
)
@patch("app.clusters.router.delete_cluster_from_db", return_value=None)
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_delete_cluster_success(mock_delete_cluster: MagicMock, mock_get_cluster_by_id: MagicMock) -> None:
    with TestClient(app) as client:
        response = client.delete("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_get_cluster_by_id.assert_called_once()
    mock_delete_cluster.assert_called_once()


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", side_effect=NotFoundException("Cluster not found."))
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_delete_cluster_not_found(mock_get_cluster_by_id: MagicMock) -> None:
    with TestClient(app) as client:
        response = client.delete("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cluster not found."}
    mock_get_cluster_by_id.assert_called_once()


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_with_resources")
@patch("app.clusters.router.update_cluster_service")
@patch("app.clusters.router.get_cluster_by_id")
@override_dependencies(ADMIN_OVERRIDES)
async def test_update_cluster_success(
    mock_get_cluster_by_id: MagicMock,
    mock_update_cluster_service: MagicMock,
    mock_get_cluster_with_resources: MagicMock,
) -> None:
    """Test successful cluster base URL update."""
    # Setup mocks
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    original_cluster = Cluster(
        id=cluster_id,
        name="original-cluster",
        workloads_base_url="https://original.example.com",
        kube_api_url="https://k8s.example.com",
    )
    updated_cluster = Cluster(
        id=cluster_id,
        name="original-cluster",  # name should not change
        workloads_base_url="https://updated.example.com",
        kube_api_url="https://k8s.updated.example.com",
        updated_by="test-updater@example.com",
    )

    mock_get_cluster_by_id.return_value = original_cluster
    mock_update_cluster_service.return_value = updated_cluster
    mock_get_cluster_with_resources.return_value = ClusterWithResources(
        id=cluster_id,
        name="original-cluster",
        workloads_base_url="https://updated.example.com",
        kube_api_url="https://k8s.updated.example.com",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 30, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test-updater@example.com",
        last_heartbeat_at=None,
        available_resources=ClusterResources(cpu_milli_cores=0, memory_bytes=0, ephemeral_storage_bytes=0, gpu_count=0),
        allocated_resources=ClusterResources(cpu_milli_cores=0, memory_bytes=0, ephemeral_storage_bytes=0, gpu_count=0),
        total_node_count=0,
        available_node_count=0,
        assigned_quota_count=0,
    )

    # Make request
    cluster_update = ClusterIn(
        workloads_base_url="https://updated.example.com", kube_api_url="https://k8s.updated.example.com"
    )
    with TestClient(app) as client:
        response = client.put(f"/v1/clusters/{cluster_id}", json=cluster_update.model_dump())

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "original-cluster"  # name should not change
    assert response.json()["workloads_base_url"] == "https://updated.example.com"
    assert response.json()["kube_api_url"] == "https://k8s.updated.example.com"
    assert response.json()["updated_by"] == "test-updater@example.com"

    mock_get_cluster_by_id.assert_called_once()
    mock_update_cluster_service.assert_called_once()
    mock_get_cluster_with_resources.assert_called_once()


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", side_effect=NotFoundException("Cluster not found."))
@override_dependencies(ADMIN_OVERRIDES)
async def test_update_cluster_not_found(mock_get_cluster_by_id: MagicMock) -> None:
    """Test cluster update when cluster is not found."""
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    # Make request
    cluster_update = ClusterIn(workloads_base_url="https://updated.example.com")
    with TestClient(app) as client:
        response = client.put(f"/v1/clusters/{cluster_id}", json=cluster_update.model_dump())

    # Assertions
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cluster not found."}
    mock_get_cluster_by_id.assert_called_once()


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_nodes_in_db",
    return_value=ClusterNodes(
        data=[
            ClusterNodeResponse(
                id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
                name="MI250 Node",
                cpu_milli_cores=4000,
                memory_bytes=400 * (1024**3),
                ephemeral_storage_bytes=100 * (1024**3),
                gpu_count=8,
                updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                status="ready",
                gpu_info=GPUInfo(
                    vendor=GPUVendor.AMD, type="740c", name="Instinct MI250X", memory_bytes_per_device=64 * (1024**3)
                ),
            ),
            ClusterNodeResponse(
                id=UUID("01a18e92-002c-45b7-a06e-dcdb0277974c"),
                name="MI300 Node",
                cpu_milli_cores=4000,
                memory_bytes=80 * (1024**3),
                ephemeral_storage_bytes=200 * (1024**3),
                gpu_count=8,
                updated_at=datetime(2025, 2, 1, 0, 0, 0, tzinfo=UTC),
                status="ready",
                gpu_info=GPUInfo(
                    vendor=GPUVendor.AMD, type="74a0", name="Instinct MI300A", memory_bytes_per_device=128 * (1024**3)
                ),
            ),
            ClusterNodeResponse(
                id=UUID("02a18e92-002c-45b7-a06e-dcdb0277974c"),
                name="CPU Healthy Node",
                cpu_milli_cores=16000,
                memory_bytes=200 * (1024**3),
                ephemeral_storage_bytes=400 * (1024**3),
                gpu_count=0,
                updated_at=datetime(2025, 3, 1, 0, 0, 0, tzinfo=UTC),
                status="ready",
            ),
            ClusterNodeResponse(
                id=UUID("03a18e92-002c-45b7-a06e-dcdb0277974c"),
                name="CPU Unhealthy Node",
                cpu_milli_cores=16000,
                memory_bytes=400 * (1024**3),
                ephemeral_storage_bytes=100 * (1024**3),
                gpu_count=0,
                updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                status="unreachable",
            ),
        ]
    ),
)
@patch(
    "app.clusters.router.get_cluster_by_id",
    new_callable=AsyncMock,
    return_value=Cluster(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_nodes_success(_: Any, __: Any) -> None:
    cluster_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": [
            {
                "cpu_milli_cores": 4000,
                "ephemeral_storage_bytes": 107374182400,
                "gpu_count": 8,
                "gpu_info": {
                    "memory_bytes_per_device": 68719476736,
                    "name": "Instinct MI250X",
                    "type": "740c",
                    "vendor": "AMD",
                },
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "memory_bytes": 429496729600,
                "name": "MI250 Node",
                "status": "ready",
                "updated_at": "2025-01-01T00:00:00Z",
            },
            {
                "cpu_milli_cores": 4000,
                "ephemeral_storage_bytes": 214748364800,
                "gpu_count": 8,
                "gpu_info": {
                    "memory_bytes_per_device": 137438953472,
                    "name": "Instinct MI300A",
                    "type": "74a0",
                    "vendor": "AMD",
                },
                "id": "01a18e92-002c-45b7-a06e-dcdb0277974c",
                "memory_bytes": 85899345920,
                "name": "MI300 Node",
                "status": "ready",
                "updated_at": "2025-02-01T00:00:00Z",
            },
            {
                "cpu_milli_cores": 16000,
                "ephemeral_storage_bytes": 429496729600,
                "gpu_count": 0,
                "gpu_info": None,
                "id": "02a18e92-002c-45b7-a06e-dcdb0277974c",
                "memory_bytes": 214748364800,
                "name": "CPU Healthy Node",
                "status": "ready",
                "updated_at": "2025-03-01T00:00:00Z",
            },
            {
                "cpu_milli_cores": 16000,
                "ephemeral_storage_bytes": 107374182400,
                "gpu_count": 0,
                "gpu_info": None,
                "id": "03a18e92-002c-45b7-a06e-dcdb0277974c",
                "memory_bytes": 429496729600,
                "name": "CPU Unhealthy Node",
                "status": "unreachable",
                "updated_at": "2025-01-01T00:00:00Z",
            },
        ]
    }


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_nodes_in_db", new_callable=AsyncMock, return_value=ClusterNodes(data=[]))
@patch(
    "app.clusters.router.get_cluster_by_id",
    new_callable=AsyncMock,
    return_value=Cluster(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_nodes_no_nodes(_: Any, __: Any) -> None:
    cluster_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")
        assert response.json() == {"data": []}


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id", new_callable=AsyncMock, side_effect=NotFoundException("Cluster not found.")
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_nodes_no_cluster(_: MagicMock) -> None:
    cluster_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cluster not found."}


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_cluster_nodes_not_in_role() -> None:
    cluster_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_node_from_db",
    new_callable=AsyncMock,
    return_value=ClusterNodeResponse(
        id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
        name="MI250 Node",
        cpu_milli_cores=4000,
        memory_bytes=400 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_count=8,
        updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        status="ready",
        gpu_info=GPUInfo(
            vendor=GPUVendor.AMD, type="740c", name="Instinct MI250X", memory_bytes_per_device=64 * (1024**3)
        ),
    ),
)
@patch(
    "app.clusters.router.get_cluster_by_id",
    new_callable=AsyncMock,
    return_value=Cluster(
        id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_node_success(_: Any, __: Any) -> None:
    cluster_id = uuid4()
    node_id = UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c")

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    assert response.json()["name"] == "MI250 Node"
    assert response.json()["gpu_info"]["vendor"] == "AMD"


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_node_from_db",
    new_callable=AsyncMock,
    side_effect=NotFoundException("Cluster node not found"),
)
@patch(
    "app.clusters.router.get_cluster_by_id",
    new_callable=AsyncMock,
    return_value=Cluster(
        id=uuid4(),
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_node_not_found(_: Any, __: Any) -> None:
    cluster_id = uuid4()
    node_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "detail" in response.json()


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id",
    new_callable=AsyncMock,
    side_effect=NotFoundException("Cluster with ID ... not found"),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_node_cluster_not_found(_: MagicMock) -> None:
    cluster_id = uuid4()
    node_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "detail" in response.json()


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_cluster_node_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_clusters_stats_from_db",
    return_value=ClustersStats(
        total_cluster_count=3,
        total_node_count=30,
        available_node_count=29,
        total_gpu_node_count=20,
        total_gpu_count=100,
        available_gpu_count=80,
        allocated_gpu_count=60,
    ),
)
@patch("app.clusters.router.is_user_in_role", return_value=True)
@override_dependencies(USER_WITH_KEYCLOAK_ID_OVERRIDES)
async def test_get_clusters_stats_success(_: MagicMock, __: MagicMock) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/stats")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "allocated_gpu_count": 60,
        "available_gpu_count": 80,
        "available_node_count": 29,
        "total_cluster_count": 3,
        "total_gpu_count": 100,
        "total_gpu_node_count": 20,
        "total_node_count": 30,
    }


@pytest.mark.asyncio
@patch("app.clusters.router.is_user_in_role", return_value=False)
@patch("app.clusters.router.get_projects_accessible_to_user", return_value=[])
@patch(
    "app.clusters.router.get_stats_for_clusters_accessible_to_user",
    return_value=ClustersStats(
        total_cluster_count=1,
        total_node_count=10,
        available_node_count=8,
        total_gpu_node_count=5,
        total_gpu_count=40,
        available_gpu_count=32,
        allocated_gpu_count=20,
    ),
)
@override_dependencies(USER_WITH_KEYCLOAK_ID_OVERRIDES)
async def test_get_clusters_stats_non_admin_success(_: Any, __: Any, ___: Any) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/stats")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "allocated_gpu_count": 20,
        "available_gpu_count": 32,
        "available_node_count": 8,
        "total_cluster_count": 1,
        "total_gpu_count": 40,
        "total_gpu_node_count": 5,
        "total_node_count": 10,
    }


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_projects_in_cluster_with_resource_allocation",
    return_value=ProjectsWithResourceAllocation(
        data=[
            ProjectWithResourceAllocation(
                id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
                name="project1",
                description="Description 1",
                cluster_id="0aa18e92-102c-45b7-a06e-dcdb0277974c",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                status=ProjectStatus.PENDING,
                status_reason="Creating",
                cluster=ClusterWithResources(
                    id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    name="cluster1",
                    last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    workloads_base_url="https://example.com",
                    kube_api_url="https://k8s.example.com:6443",
                    available_resources=ClusterResources(
                        cpu_milli_cores=8000,
                        memory_bytes=16 * 1024 * 1024 * 1024,  # 16 GB
                        ephemeral_storage_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
                        gpu_count=2,
                    ),
                    allocated_resources=ClusterResources(
                        cpu_milli_cores=1000,
                        memory_bytes=1024 * 1024 * 1024,  # 1 GB
                        ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
                        gpu_count=0,
                    ),
                    total_node_count=3,
                    available_node_count=2,
                    assigned_quota_count=1,
                ),
                quota=QuotaResponse(
                    id="0aa18e92-202c-45b7-a06e-dcdb0277974c",
                    cpu_milli_cores=1000,
                    memory_bytes=1024 * 1024 * 1024,  # 1 GB
                    ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
                    gpu_count=0,
                    status=QuotaStatus.PENDING,
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test_user",
                    updated_by="test_user",
                ),
            ),
            ProjectWithResourceAllocation(
                id="65b44238-556d-4e59-82ea-ddfafc5491f3",
                name="project2",
                description="Description 2",
                cluster_id="0aa18e92-302c-45b7-a06e-dcdb0277974c",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                status=ProjectStatus.PENDING,
                status_reason="Creating",
                cluster=ClusterWithResources(
                    id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    name="cluster1",
                    last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    workloads_base_url="https://example.com",
                    kube_api_url="https://k8s.example.com:6443",
                    available_resources=ClusterResources(
                        cpu_milli_cores=8000,
                        memory_bytes=16 * 1024 * 1024 * 1024,  # 16 GB
                        ephemeral_storage_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
                        gpu_count=2,
                    ),
                    allocated_resources=ClusterResources(
                        cpu_milli_cores=1000,
                        memory_bytes=1024 * 1024 * 1024,  # 1 GB
                        ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
                        gpu_count=0,
                    ),
                    total_node_count=3,
                    available_node_count=2,
                    assigned_quota_count=1,
                ),
                quota=QuotaResponse(
                    id="0aa18e92-402c-45b7-a06e-dcdb0277974c",
                    cpu_milli_cores=2000,
                    memory_bytes=2 * 1024 * 1024 * 1024,  # 2 GB
                    ephemeral_storage_bytes=10 * 1024 * 1024 * 1024,  # 10 GB
                    gpu_count=1,
                    status=QuotaStatus.PENDING,
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                ),
            ),
        ]
    ),
)
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
        name="cluster1",
        last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        workloads_base_url="https://example.com",
    ),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_projects_success(_: Any, __: Any) -> None:
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{uuid4()}/projects")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": [
            {
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "name": "project1",
                "description": "Description 1",
                "cluster_id": "0aa18e92-102c-45b7-a06e-dcdb0277974c",
                "status": "Pending",
                "status_reason": "Creating",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
                "cluster": {
                    "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "workloads_base_url": "https://example.com",
                    "kube_api_url": "https://k8s.example.com:6443",
                    "name": "cluster1",
                    "last_heartbeat_at": "2025-03-10T12:00:00Z",
                    "available_resources": {
                        "cpu_milli_cores": 8000,
                        "memory_bytes": 17179869184,
                        "ephemeral_storage_bytes": 107374182400,
                        "gpu_count": 2,
                    },
                    "allocated_resources": {
                        "cpu_milli_cores": 1000,
                        "memory_bytes": 1073741824,
                        "ephemeral_storage_bytes": 5368709120,
                        "gpu_count": 0,
                    },
                    "total_node_count": 3,
                    "available_node_count": 2,
                    "assigned_quota_count": 1,
                    "gpu_info": None,
                    "status": "unhealthy",
                    "priority_classes": [
                        {"name": "low", "priority": -100},
                        {"name": "medium", "priority": 0},
                        {"name": "high", "priority": 100},
                    ],
                    "gpu_allocation_percentage": 0.0,
                    "cpu_allocation_percentage": 12.5,
                    "memory_allocation_percentage": 6.25,
                },
                "quota": {
                    "cpu_milli_cores": 1000,
                    "ephemeral_storage_bytes": 5368709120,
                    "gpu_count": 0,
                    "id": "0aa18e92-202c-45b7-a06e-dcdb0277974c",
                    "memory_bytes": 1073741824,
                    "status": "Pending",
                    "status_reason": None,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test_user",
                    "updated_by": "test_user",
                },
                "gpu_allocation_percentage": 0.0,
                "gpu_allocation_exceeded": False,
                "cpu_allocation_percentage": 12.5,
                "cpu_allocation_exceeded": False,
                "memory_allocation_percentage": 6.25,
                "memory_allocation_exceeded": False,
            },
            {
                "id": "65b44238-556d-4e59-82ea-ddfafc5491f3",
                "name": "project2",
                "description": "Description 2",
                "cluster_id": "0aa18e92-302c-45b7-a06e-dcdb0277974c",
                "status": "Pending",
                "status_reason": "Creating",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
                "cluster": {
                    "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "workloads_base_url": "https://example.com",
                    "kube_api_url": "https://k8s.example.com:6443",
                    "name": "cluster1",
                    "last_heartbeat_at": "2025-03-10T12:00:00Z",
                    "available_resources": {
                        "cpu_milli_cores": 8000,
                        "memory_bytes": 17179869184,
                        "ephemeral_storage_bytes": 107374182400,
                        "gpu_count": 2,
                    },
                    "allocated_resources": {
                        "cpu_milli_cores": 1000,
                        "memory_bytes": 1073741824,
                        "ephemeral_storage_bytes": 5368709120,
                        "gpu_count": 0,
                    },
                    "total_node_count": 3,
                    "available_node_count": 2,
                    "assigned_quota_count": 1,
                    "gpu_info": None,
                    "status": "unhealthy",
                    "priority_classes": [
                        {"name": "low", "priority": -100},
                        {"name": "medium", "priority": 0},
                        {"name": "high", "priority": 100},
                    ],
                    "gpu_allocation_percentage": 0.0,
                    "cpu_allocation_percentage": 12.5,
                    "memory_allocation_percentage": 6.25,
                },
                "quota": {
                    "cpu_milli_cores": 2000,
                    "ephemeral_storage_bytes": 10737418240,
                    "gpu_count": 1,
                    "id": "0aa18e92-402c-45b7-a06e-dcdb0277974c",
                    "memory_bytes": 2147483648,
                    "status": "Pending",
                    "status_reason": None,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                },
                "gpu_allocation_percentage": 50.0,
                "gpu_allocation_exceeded": False,
                "cpu_allocation_percentage": 25.0,
                "cpu_allocation_exceeded": False,
                "memory_allocation_percentage": 12.5,
                "memory_allocation_exceeded": False,
            },
        ]
    }


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id", new_callable=AsyncMock, side_effect=NotFoundException("Cluster not found")
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_projects_no_cluster(_: MagicMock) -> None:
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{uuid4()}/projects")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_cluster_projects_not_in_role() -> None:
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{uuid4()}/projects")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_status_stats_for_workloads_in_cluster",
    return_value=WorkloadStatusStats(
        name="test-cluster",
        total_workloads=15,
        statusCounts=[
            WorkloadStatusCount(status=WorkloadStatus.RUNNING, count=5),
            WorkloadStatusCount(status=WorkloadStatus.PENDING, count=3),
            WorkloadStatusCount(status=WorkloadStatus.COMPLETE, count=4),
            WorkloadStatusCount(status=WorkloadStatus.FAILED, count=2),
            WorkloadStatusCount(status=WorkloadStatus.TERMINATED, count=1),
        ],
    ),
)
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id="370e6fc1-fa23-41c7-9ad4-84863a0942f9",
        name="test-cluster",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_workload_stats_success(_: Any, __: Any) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/370e6fc1-fa23-41c7-9ad4-84863a0942f9/workloads/stats")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "test-cluster"
    assert data["total_workloads"] == 15
    assert len(data["statusCounts"]) == 5
    status_counts = {sc["status"] for sc in data["statusCounts"]}
    assert "Running" in status_counts
    assert "Pending" in status_counts
    assert "Complete" in status_counts


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_cluster_workload_stats_not_in_role() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/370e6fc1-fa23-41c7-9ad4-84863a0942f9/workloads/stats")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", new_callable=AsyncMock, return_value=None)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_workload_stats_cluster_not_found(_: MagicMock) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/clusters/370e6fc1-fa23-41c7-9ad4-84863a0942f9/workloads/stats")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster with ID" in response.json()["detail"]


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Cluster 1"),
)
@patch(
    "app.clusters.router.get_gpu_device_utilization_timeseries_for_cluster_from_ds",
    return_value=default_timeseries_metrics,
)
@patch("app.metrics.schemas.datetime")
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_gpu_device_utilization_timeseries_for_cluster_success(mock_dt: MagicMock, _: Any, __: Any) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": [
            {
                "metadata": {
                    "label": "default_label",
                    "project": {
                        "description": "project 1",
                        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                        "name": "project1",
                        "cluster_id": "0aa22e92-002c-41b7-a06e-dcdb0244974c",
                        "status": "Pending",
                        "status_reason": "Creating",
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                    },
                },
                "values": [
                    {"timestamp": "2025-03-10T12:00:00Z", "value": 0.1},
                    {"timestamp": "2025-03-10T12:01:00Z", "value": 0.3},
                ],
            },
            {
                "metadata": {
                    "label": "default_label",
                    "project": {
                        "description": "project 2",
                        "id": "19465a28-1649-4f55-887f-536dd36a47f8",
                        "name": "project2",
                        "cluster_id": "1ab22e52-102c-31b7-a06e-dcdb0244974c",
                        "status": "Pending",
                        "status_reason": "Creating",
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                    },
                },
                "values": [
                    {"timestamp": "2025-03-10T12:00:00Z", "value": 0.2},
                    {"timestamp": "2025-03-10T12:01:00Z", "value": 0.4},
                ],
            },
        ],
        "range": {
            "end": "2025-03-11T12:00:00Z",
            "interval_seconds": 60,
            "start": "2025-03-10T12:00:00Z",
            "timestamps": ["2025-03-10T12:00:00Z", "2025-03-10T12:01:00Z"],
        },
    }


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_gpu_device_utilization_timeseries_for_cluster_not_in_role() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", return_value=None, autospec=True)
@patch("app.metrics.schemas.datetime")
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_gpu_device_utilization_timeseries_for_cluster_no_cluster(mock_dt: MagicMock, _: MagicMock) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_pcie_bandwidth_timeseries_for_node",
)
@patch(
    "app.clusters.router.get_cluster_and_node_by_ids",
    return_value=(
        Cluster(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Cluster 1"),
        MagicMock(spec=ClusterNode, name="node-1"),
    ),
)
@patch("app.metrics.schemas.datetime")
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_pcie_bandwidth_success(mock_dt: MagicMock, _: Any, mock_get_pcie: Any) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    recent_pcie_test_end = mock_dt.now.return_value.replace(microsecond=0) - timedelta(minutes=1)
    recent_pcie_test_start = recent_pcie_test_end - timedelta(days=1)
    recent_pcie_test_second_point = recent_pcie_test_start + timedelta(minutes=1)

    mock_get_pcie.return_value = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-uuid-1",
                gpu_id="0",
                hostname="node-1",
                metric=DeviceMetricTimeseries(
                    series_label="pcie_bandwidth",
                    values=[
                        Datapoint(timestamp=recent_pcie_test_start, value=100.0),
                        Datapoint(timestamp=recent_pcie_test_second_point, value=150.0),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(
            start=recent_pcie_test_start,
            end=recent_pcie_test_end,
        ),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/nodes/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metrics/pcie/bandwidth?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "gpu_devices" in data
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-uuid-1"
    assert data["gpu_devices"][0]["hostname"] == "node-1"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "pcie_bandwidth"
    assert "range" in data


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_and_node_by_ids",
    side_effect=NotFoundException("Cluster node not found"),
)
@patch("app.metrics.schemas.datetime")
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_pcie_bandwidth_node_not_found(mock_dt: MagicMock, _: Any) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/nodes/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metrics/pcie/bandwidth?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_pcie_bandwidth_forbidden() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/nodes/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metrics/pcie/bandwidth?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_pcie_efficiency_timeseries_for_node",
)
@patch(
    "app.clusters.router.get_cluster_and_node_by_ids",
    return_value=(
        Cluster(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Cluster 1"),
        MagicMock(spec=ClusterNode, name="node-1"),
    ),
)
@patch("app.metrics.schemas.datetime")
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_pcie_efficiency_success(mock_dt: MagicMock, _cluster_and_node: Any, mock_get_pcie: Any) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    recent_pcie_test_end = mock_dt.now.return_value.replace(microsecond=0) - timedelta(minutes=1)
    recent_pcie_test_start = recent_pcie_test_end - timedelta(days=1)
    recent_pcie_test_second_point = recent_pcie_test_start + timedelta(minutes=1)

    mock_get_pcie.return_value = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-uuid-1",
                gpu_id="0",
                hostname="node-1",
                metric=DeviceMetricTimeseries(
                    series_label="pcie_efficiency",
                    values=[
                        Datapoint(timestamp=recent_pcie_test_start, value=75.5),
                        Datapoint(timestamp=recent_pcie_test_second_point, value=100.0),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(
            start=recent_pcie_test_start,
            end=recent_pcie_test_end,
        ),
    )
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/nodes/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metrics/pcie/efficiency?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "gpu_devices" in data
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-uuid-1"
    assert data["gpu_devices"][0]["hostname"] == "node-1"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "pcie_efficiency"
    assert "range" in data


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_and_node_by_ids",
    side_effect=NotFoundException("Cluster node not found"),
)
@patch("app.metrics.schemas.datetime")
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_pcie_efficiency_node_not_found(mock_dt: MagicMock, _: Any) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/nodes/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metrics/pcie/efficiency?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_pcie_efficiency_forbidden() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/nodes/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metrics/pcie/efficiency?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.clusters.router.get_workloads_metrics_by_cluster", autospec=True)
@patch("app.clusters.router.get_cluster_by_id", autospec=True)
@override_dependencies(ADMIN_SESSION_WITH_USER_MOCK_OVERRIDES)
async def test_get_cluster_workloads_metrics_success(mock_get_cluster: MagicMock, mock_get_metrics: MagicMock) -> None:
    cluster_id = uuid4()

    mock_cluster = MagicMock()
    mock_cluster.id = cluster_id
    mock_cluster.name = "TestCluster"
    mock_cluster.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    mock_get_cluster.return_value = mock_cluster

    mock_get_metrics.return_value = WorkloadsWithMetrics(
        data=[
            WorkloadWithMetrics(
                id=uuid4(),
                project_id=uuid4(),
                cluster_id=cluster_id,
                status="Running",
                display_name="Mock Workload",
                type=WorkloadType.CUSTOM,
                gpu_count=4,
                vram=16384,
                run_time=7200,
                created_at=None,
                created_by="tester",
                updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                updated_by="tester",
            )
        ],
        total=1,
        page=1,
        page_size=10,
    )

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/workloads/metrics")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["display_name"] == "Mock Workload"
    assert data["data"][0]["gpu_count"] == 4
    assert data["data"][0]["vram"] == 16384
    assert data["data"][0]["run_time"] == 7200


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", autospec=True)
@patch("app.clusters.router.get_workloads_metrics_by_cluster", autospec=True)
@override_dependencies(ADMIN_SESSION_WITH_USER_MOCK_OVERRIDES)
async def test_get_cluster_workloads_metrics_cluster_not_found(
    mock_get_metrics: MagicMock, mock_get_cluster: MagicMock
) -> None:
    cluster_id = uuid4()

    mock_get_cluster.return_value = None
    mock_get_metrics.return_value = None

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/workloads/metrics")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Cluster not found"


@pytest.mark.asyncio
@override_dependencies(ADMIN_SESSION_FORBIDDEN_OVERRIDES)
async def test_get_cluster_workloads_metrics_not_in_role() -> None:
    cluster_id = uuid4()
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/workloads/metrics")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_kubeconfig_as_yaml", return_value=ClusterKubeConfig(kube_config="config"))
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id=uuid4(),
        name="test-cluster",
        kube_api_url="https://k8s.example.com:6443",
        workloads_base_url="https://workloads.example.com",
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_kubeconfig_success(_: MagicMock, __: MagicMock) -> None:
    """Test successful kubeconfig retrieval."""
    cluster_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/kube-config")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"kube_config": "config"}


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", side_effect=NotFoundException("Cluster not found"))
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_cluster_kubeconfig_not_found(_: MagicMock) -> None:
    cluster_id = uuid4()
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/kube-config")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_cluster_kubeconfig_forbidden() -> None:
    cluster_id = uuid4()
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/kube-config")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_utilization_success() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-aaa",
                gpu_id="0",
                hostname="worker-1",
                metric=DeviceMetricTimeseries(
                    series_label="gpu_activity_pct",
                    values=[
                        Datapoint(value=75.0, timestamp=start),
                        Datapoint(value=80.0, timestamp=end),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_utilization", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/core-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-aaa"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "gpu_activity_pct"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 75.0


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_utilization_cluster_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/core-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_utilization_node_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/core-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_gpu_utilization_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()
    now = datetime.now(UTC)
    start_iso = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/core-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_utilization_with_step_param() -> None:
    """?step= is forwarded to the service as the query interval in seconds."""
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_utilization", return_value=mock_response) as mock_svc,
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/core-utilization"
            f"?start={start_iso}&end={end_iso}&step=300"
        )

    assert response.status_code == status.HTTP_200_OK
    assert mock_svc.call_args[1]["step"] == 300


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_utilization_invalid_step_param() -> None:
    """step=0 is rejected by the schema (ge=1)."""
    now = datetime.now(UTC)
    start_iso = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = uuid4()
    node_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/core-utilization?start={start_iso}&end={end_iso}&step=0"
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_memory_utilization_success() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-aaa",
                gpu_id="0",
                hostname="worker-1",
                metric=DeviceMetricTimeseries(
                    series_label="vram_utilization_pct",
                    values=[
                        Datapoint(value=62.5, timestamp=start),
                        Datapoint(value=70.0, timestamp=end),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_vram_utilization", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/memory-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-aaa"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "vram_utilization_pct"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 62.5


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_power_usage_success() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-aaa",
                gpu_id="0",
                hostname="worker-1",
                metric=DeviceMetricTimeseries(
                    series_label="power_watts",
                    values=[
                        Datapoint(value=19.5, timestamp=start),
                        Datapoint(value=20.1, timestamp=end),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_power_usage", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/power-usage?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-aaa"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "power_watts"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 19.5


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_memory_utilization_cluster_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/memory-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_power_usage_cluster_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/power-usage?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_memory_utilization_node_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/memory-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_power_usage_node_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/power-usage?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_gpu_memory_utilization_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()
    now = datetime.now(UTC)
    start_iso = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/memory-utilization?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_power_usage_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()
    now = datetime.now(UTC)
    start_iso = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/power-usage?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_clock_speed_success() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-bbb",
                gpu_id="1",
                hostname="worker-2",
                metric=DeviceMetricTimeseries(
                    series_label="clock_speed_mhz",
                    values=[
                        Datapoint(value=2100.0, timestamp=start),
                        Datapoint(value=1800.0, timestamp=end),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_clock_speed", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-2")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/clock-speed?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-bbb"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "clock_speed_mhz"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 2100.0


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_devices_success() -> None:
    now = datetime.now(UTC)

    mock_response = NodeGpuDevicesResponse(
        gpu_devices=[
            NodeGpuDevice(
                gpu_uuid="uuid-aaa",
                gpu_id="0",
                product_name="Instinct MI300",
                temperature=63.5,
                power_consumption=19.5,
                vram_utilization=25.0,
                last_updated=now,
            ),
            NodeGpuDevice(
                gpu_uuid="uuid-bbb",
                gpu_id="1",
                product_name="Instinct MI300",
                temperature=42.0,
                power_consumption=15.0,
                vram_utilization=12.5,
                last_updated=now,
            ),
        ]
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_devices_with_metrics", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(
                Cluster(id=cluster_id, name="test-cluster"),
                MagicMock(spec=ClusterNode, name="worker-1", gpu_product_name="Instinct MI300"),
            ),
        ),
        TestClient(app) as client,
    ):
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/gpu-devices")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 2
    assert data["gpu_devices"][0]["gpu_uuid"] == "uuid-aaa"
    assert data["gpu_devices"][0]["gpu_id"] == "0"
    assert data["gpu_devices"][0]["product_name"] == "Instinct MI300"
    assert data["gpu_devices"][0]["temperature"] == 63.5
    assert data["gpu_devices"][0]["power_consumption"] == 19.5
    assert data["gpu_devices"][0]["vram_utilization"] == 25.0
    assert data["gpu_devices"][1]["gpu_uuid"] == "uuid-bbb"
    assert data["gpu_devices"][1]["gpu_id"] == "1"


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_clock_speed_cluster_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/clock-speed?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_devices_cluster_not_found() -> None:
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/gpu-devices")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_get_node_workloads_metrics_cluster_not_found() -> None:
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/workloads/metrics")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_clock_speed_node_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/clock-speed?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_gpu_devices_node_not_found() -> None:
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/gpu-devices")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_get_node_workloads_metrics_node_not_found() -> None:
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/workloads/metrics")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_gpu_clock_speed_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()
    now = datetime.now(UTC)
    start_iso = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/clock-speed?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_power_usage_with_step_param() -> None:
    """?step= is forwarded to the service as the query interval in seconds."""
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_power_usage", return_value=mock_response) as mock_svc,
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/power-usage?start={start_iso}&end={end_iso}&step=300"
        )

    assert response.status_code == status.HTTP_200_OK
    assert mock_svc.call_args[1]["step"] == 300


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_memory_temperature_success() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-bbb",
                gpu_id="1",
                hostname="worker-2",
                metric=DeviceMetricTimeseries(
                    series_label="memory_temperature_celsius",
                    values=[
                        Datapoint(value=68.0, timestamp=start),
                        Datapoint(value=70.2, timestamp=end),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_memory_temperature", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-2")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/memory?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-bbb"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "memory_temperature_celsius"


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_memory_temperature_cluster_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/memory?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_memory_temperature_node_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/memory?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_memory_temperature_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()
    now = datetime.now(UTC)
    start_iso = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/memory?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_memory_temperature_with_step() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_memory_temperature", return_value=mock_response) as mock_svc,
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/memory?start={start_iso}&end={end_iso}&step=300"
        )

    assert response.status_code == status.HTTP_200_OK
    assert mock_svc.call_args[1]["step"] == 300


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_memory_temperature_default_step_is_none() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_memory_temperature", return_value=mock_response) as mock_svc,
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/memory?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    assert mock_svc.call_args[1]["step"] is None


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_gpu_devices_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/gpu-devices")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(ADMIN_SESSION_FORBIDDEN_OVERRIDES)
async def test_get_node_workloads_metrics_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/workloads/metrics")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_get_node_workloads_metrics_success() -> None:
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()
    workload_id = uuid4()

    mock_response = NodeWorkloadsWithMetrics(
        data=[
            NodeWorkloadWithMetrics(
                id=workload_id,
                project_id=uuid4(),
                cluster_id=UUID(cluster_id),
                status=WorkloadStatus.RUNNING.value,
                display_name="test-workload",
                type=WorkloadType.INFERENCE.value,
                gpu_count=2,
                vram=16384.0,
                gpu_devices=[
                    WorkloadGpuDevice(gpu_id="0", hostname="worker-1"),
                    WorkloadGpuDevice(gpu_id="1", hostname="worker-1"),
                ],
                updated_at=datetime.now(UTC),
                updated_by="test@example.com",
            ),
        ]
    )

    with (
        patch("app.clusters.router.get_workloads_metrics_by_node", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/workloads/metrics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["display_name"] == "test-workload"
    assert len(data["data"][0]["gpu_devices"]) == 2
    assert data["data"][0]["gpu_devices"][0]["gpu_id"] == "0"


@pytest.mark.asyncio
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_get_node_workloads_metrics_empty() -> None:
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    mock_response = NodeWorkloadsWithMetrics(data=[])

    with (
        patch("app.clusters.router.get_workloads_metrics_by_node", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(f"/v1/clusters/{cluster_id}/nodes/{node_id}/workloads/metrics")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == []


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_junction_temperature_success() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-aaa",
                gpu_id="0",
                hostname="worker-1",
                metric=DeviceMetricTimeseries(
                    series_label="junction_temperature_celsius",
                    values=[
                        Datapoint(value=72.0, timestamp=start),
                        Datapoint(value=75.5, timestamp=end),
                    ],
                ),
            ),
        ],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_junction_temperature", return_value=mock_response),
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/junction?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-aaa"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "junction_temperature_celsius"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 72.0


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_junction_temperature_cluster_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = uuid4()
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Cluster with ID {cluster_id} not found"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/junction?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Cluster" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_junction_temperature_node_not_found() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            side_effect=NotFoundException(f"Node with ID {node_id} not found in cluster {cluster_id}"),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/junction?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Node" in response.json()["detail"]


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES)
async def test_get_node_junction_temperature_forbidden() -> None:
    cluster_id = uuid4()
    node_id = uuid4()
    now = datetime.now(UTC)
    start_iso = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/junction?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_junction_temperature_with_step_param() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_junction_temperature", return_value=mock_response) as mock_svc,
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/junction"
            f"?start={start_iso}&end={end_iso}&step=300"
        )

    assert response.status_code == status.HTTP_200_OK
    assert mock_svc.call_args[1]["step"] == 300


@pytest.mark.asyncio
@override_dependencies(USER_CLUSTER_SESSION_OVERRIDES)
async def test_get_node_junction_temperature_default_step_is_none() -> None:
    """When no step param is provided, step=None is passed to let the service decide."""
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).replace(microsecond=0)
    end = now.replace(microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_response = GpuDeviceSingleMetricResponse(
        gpu_devices=[],
        range=MetricsTimeRange(start=start, end=end),
    )

    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    node_id = uuid4()

    with (
        patch("app.clusters.router.get_node_gpu_junction_temperature", return_value=mock_response) as mock_svc,
        patch(
            "app.clusters.router.get_cluster_and_node_by_ids",
            new_callable=AsyncMock,
            return_value=(Cluster(id=cluster_id, name="test-cluster"), MagicMock(spec=ClusterNode, name="worker-1")),
        ),
        TestClient(app) as client,
    ):
        response = client.get(
            f"/v1/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/junction?start={start_iso}&end={end_iso}"
        )

    assert response.status_code == status.HTTP_200_OK
    assert mock_svc.call_args[1]["step"] is None
