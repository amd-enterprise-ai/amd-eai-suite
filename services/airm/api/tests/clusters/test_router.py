# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from airm.messaging.schemas import GPUVendor, QuotaStatus
from app import app  # type: ignore
from app.clusters.models import Cluster
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
from app.metrics.schemas import (
    Datapoint,
    DatapointsWithMetadata,
    MetricsTimeseries,
    ProjectDatapointMetadata,
    TimeseriesRange,
)
from app.organizations.models import Organization
from app.projects.enums import ProjectStatus
from app.projects.schemas import (
    ProjectResponse,
    ProjectsWithResourceAllocation,
    ProjectWithResourceAllocation,
)
from app.quotas.schemas import QuotaResponse
from app.users.models import User
from app.utilities.database import get_session
from app.utilities.exceptions import ForbiddenException, NotFoundException
from app.utilities.security import (
    auth_token_claimset,
    create_logged_in_user_in_system,
    ensure_platform_administrator,
    get_user,
    get_user_email,
    get_user_organization,
    track_user_activity_from_token,
)
from app.workloads.schemas import WorkloadsStats

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
                Datapoint(
                    value=0.1,
                    timestamp=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                ),
                Datapoint(
                    value=0.3,
                    timestamp=datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC),
                ),
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
                Datapoint(
                    value=0.2,
                    timestamp=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                ),
                Datapoint(
                    value=0.4,
                    timestamp=datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC),
                ),
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
async def test_create_cluster_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.post(
            "/v1/clusters",
            json={"workloads_base_url": "https://example.com", "kube_api_url": "https://k8s.example.com"},
        )

    assert response.status_code == status.HTTP_201_CREATED
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
async def test_create_cluster_no_user():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock()
    mock_get_user.side_effect = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    with TestClient(app) as client:
        response = client.post("/v1/clusters", json={})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_cluster_user_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.post("/v1/clusters", json={})

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_cluster_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.post("/v1/clusters", json={"workloads_base_url": "https://example.com"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.clusters.router.create_cluster_and_queues", side_effect=Exception())
@patch("app.utilities.database.session_maker", return_value=AsyncMock())
async def test_create_cluster_exception(session_maker_mock, __):
    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    app.dependency_overrides = {}
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[create_logged_in_user_in_system] = lambda: MagicMock()
    app.dependency_overrides[track_user_activity_from_token] = lambda: MagicMock()

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
async def test_create_cluster_no_base_url(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.post("/v1/clusters", json={})

    assert response.status_code == status.HTTP_201_CREATED
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
        clusters=[
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
async def test_get_clusters_platform_admin_success(_, __, mock_datetime):
    mock_datetime.now.return_value = datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC)

    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/clusters")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "clusters": [
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
async def test_get_cluster_success(_, __, ___):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: User(
        email="user1@test.com", organization_id="org_id", keycloak_user_id="keycloak_id"
    )

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
)
@patch("app.clusters.router.validate_cluster_accessible_to_user")
async def test_get_cluster_team_member_success(_, __, ___, ____):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: User(
        email="user1@test.com", organization_id="org_id", keycloak_user_id="keycloak_id"
    )

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
async def test_get_cluster_team_member_no_access(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: User(
        email="user1@test.com", organization_id="org_id", keycloak_user_id="keycloak_id"
    )

    with TestClient(app) as client:
        response = client.get("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        workloads_base_url="https://example.com",
    ),
)
@patch("app.clusters.router.delete_cluster_for_organization", return_value=None)
async def test_delete_cluster_success(mock_delete_cluster_for_organization, mock_get_cluster_by_id):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.delete("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_get_cluster_by_id.assert_called_once()
    mock_delete_cluster_for_organization.assert_called_once()


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", side_effect=NotFoundException("Cluster not found."))
async def test_delete_cluster_not_found(mock_get_cluster_by_id):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.delete("/v1/clusters/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cluster not found."}
    mock_get_cluster_by_id.assert_called_once()


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_with_resources")
@patch("app.clusters.router.update_cluster_service")
@patch("app.clusters.router.get_cluster_by_id")
async def test_update_cluster_success(
    mock_get_cluster_by_id, mock_update_cluster_service, mock_get_cluster_with_resources
):
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

    # Setup dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id=cluster_id, name="Test Org", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_email] = lambda: "test-updater@example.com"
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    # Make request
    cluster_update = ClusterIn(
        workloads_base_url="https://updated.example.com",
        kube_api_url="https://k8s.updated.example.com",
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
async def test_update_cluster_not_found(mock_get_cluster_by_id):
    """Test cluster update when cluster is not found."""
    cluster_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    # Setup dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id=cluster_id, name="Test Org", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_email] = lambda: "test-updater@example.com"
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

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
        cluster_nodes=[
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
    return_value=Cluster(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_get_cluster_nodes_success(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    cluster_id = uuid4()

    # Mock the organization
    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "cluster_nodes": [
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
@patch(
    "app.clusters.router.get_cluster_nodes_in_db",
    return_value=ClusterNodes(cluster_nodes=[]),
)
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="cluster1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_get_cluster_nodes_no_nodes(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    cluster_id = uuid4()

    # Mock the organization
    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")
        assert response.json() == {"cluster_nodes": []}


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_cluster_by_id",
    side_effect=NotFoundException("Cluster not found."),
)
async def test_get_cluster_nodes_no_cluster(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    cluster_id = uuid4()

    # Mock the organization
    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cluster not found."}


@pytest.mark.asyncio
async def test_get_cluster_nodes_not_in_role():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    cluster_id = uuid4()

    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_cluster_nodes_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    cluster_id = uuid4()

    # Mock the organization
    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/nodes")
        assert response.status_code == status.HTTP_404_NOT_FOUND


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
async def test_get_clusters_stats_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    # Mock the organization
    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

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
async def test_get_clusters_stats_not_in_role():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    cluster_id = uuid4()

    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get("/v1/clusters/stats")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_clusters_stats_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    cluster_id = uuid4()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/clusters/stats")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_projects_in_cluster_with_resource_allocation",
    return_value=ProjectsWithResourceAllocation(
        projects=[
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
async def test_get_cluster_projects_success(_, __):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user] = lambda: MagicMock(spec_set=str)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{uuid4()}/projects")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "projects": [
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
@patch("app.clusters.router.get_cluster_by_id", side_effect=NotFoundException("Cluster not found"))
async def test_get_projects_no_cluster(_):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user] = lambda: MagicMock(spec_set=str)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{uuid4()}/projects")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_cluster_projects_not_in_role():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{uuid4()}/projects")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_stats_for_workloads_in_cluster",
    return_value=WorkloadsStats(running_workloads_count=10, pending_workloads_count=5),
)
@patch(
    "app.clusters.router.get_cluster_in_organization",
    return_value=Cluster(
        id="370e6fc1-fa23-41c7-9ad4-84863a0942f9",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_get_cluster_workload_stats_success(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    with TestClient(app) as client:
        response = client.get("/v1/clusters/370e6fc1-fa23-41c7-9ad4-84863a0942f9/workloads/stats")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"running_workloads_count": 10, "pending_workloads_count": 5}


@pytest.mark.asyncio
async def test_get_cluster_workload_stats_not_in_role():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    with TestClient(app) as client:
        response = client.get("/v1/clusters/370e6fc1-fa23-41c7-9ad4-84863a0942f9/workloads/stats")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_cluster_workload_stats_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/clusters/370e6fc1-fa23-41c7-9ad4-84863a0942f9/workloads/stats")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_cluster_workload_stats_no_cluster():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/clusters/370e6fc1-fa23-41c7-9ad4-84863a0942f9/workloads/stats")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.clusters.router.validate_datetime_range", autospec=True)
@patch(
    "app.clusters.router.get_gpu_device_utilization_timeseries_for_cluster_from_ds",
    return_value=default_timeseries_metrics,
)
@patch(
    "app.clusters.router.get_cluster_in_organization",
    return_value=Cluster(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Cluster 1"),
)
async def test_get_gpu_device_utilization_timeseries_for_cluster_success(_, __, ___):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

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
async def test_get_gpu_device_utilization_timeseries_for_cluster_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_gpu_device_utilization_timeseries_for_cluster_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@patch("app.clusters.router.get_cluster_in_organization", return_value=None, autospec=True)
@pytest.mark.asyncio
async def test_get_gpu_device_utilization_timeseries_for_cluster_no_cluster(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(
            "/v1/clusters/683124d2-2db1-4f11-b247-3522a92bca8b/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_kubeconfig_as_yaml", return_value=ClusterKubeConfig(kube_config="config"))
@patch(
    "app.clusters.router.get_cluster_by_id",
    return_value=Cluster(
        id=uuid4(),
        name="test-cluster",
        organization_id=uuid4(),
        kube_api_url="https://k8s.example.com:6443",
        workloads_base_url="https://workloads.example.com",
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_get_cluster_kubeconfig_success(_, __):
    """Test successful kubeconfig retrieval."""
    app.dependency_overrides[get_session] = lambda: MagicMock()

    cluster_id = uuid4()

    mock_organization = Organization(id=uuid4(), name="Test Org", keycloak_organization_id="test-org-123")

    app.dependency_overrides[get_user_organization] = lambda: mock_organization
    app.dependency_overrides[ensure_platform_administrator] = lambda: None

    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/kube-config")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"kube_config": "config"}


@pytest.mark.asyncio
@patch("app.clusters.router.get_cluster_by_id", side_effect=NotFoundException("Cluster not found"))
async def test_get_cluster_kubeconfig_not_found(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    mock_organization = Organization(id=uuid4(), name="Test Org", keycloak_organization_id="test-org-123")

    app.dependency_overrides[get_user_organization] = lambda: mock_organization
    app.dependency_overrides[ensure_platform_administrator] = lambda: None

    cluster_id = uuid4()
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/kube-config")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_cluster_kubeconfig_requires_admin():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    cluster_id = uuid4()
    with TestClient(app) as client:
        response = client.get(f"/v1/clusters/{cluster_id}/kube-config")

    assert response.status_code == status.HTTP_403_FORBIDDEN
