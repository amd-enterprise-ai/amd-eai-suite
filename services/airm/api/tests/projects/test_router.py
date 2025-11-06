# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from airm.messaging.schemas import ProjectSecretStatus, ProjectStorageStatus, WorkloadStatus
from app import app  # type: ignore
from app.clusters.schemas import (  # Add import for ClusterStatus
    ClusterResources,
    ClusterResponse,
    ClusterWithResources,
)
from app.metrics.schemas import (
    Datapoint,
    DatapointsWithMetadata,
    DateRange,
    MetricsScalarWithRange,
    MetricsTimeseries,
    ProjectDatapointMetadata,
    TimeseriesRange,
    WorkloadsWithMetrics,
    WorkloadWithMetrics,
)
from app.organizations.models import Organization
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.projects.schemas import (
    ProjectAddUsers,
    ProjectCreate,
    ProjectEdit,
    ProjectResponse,
    Projects,
    ProjectsWithResourceAllocation,
    ProjectWithClusterAndQuota,
    ProjectWithResourceAllocation,
    ProjectWithUsers,
)
from app.quotas.schemas import QuotaBase, QuotaResponse  # Add import for QuotaCreate
from app.secrets.enums import SecretScope, SecretStatus, SecretType, SecretUseCase
from app.secrets.models import ProjectSecret as ProjectSecretModel
from app.secrets.schemas import (
    ProjectSecretsWithParentSecret,
    ProjectSecretWithParentSecret,
    SecretResponse,
)
from app.storages.enums import StorageScope, StorageStatus, StorageType
from app.storages.models import ProjectStorage as ProjectStorageModel
from app.storages.schemas import ProjectStoragesWithParentStorage, ProjectStorageWithParentStorage, StorageResponse
from app.users.schemas import InvitedUser, UserResponse
from app.utilities.database import get_session
from app.utilities.exceptions import ConflictException, NotFoundException, ValidationException
from app.utilities.security import (
    Roles,
    auth_token_claimset,
    ensure_platform_administrator,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    get_user_organization,
)
from app.workloads.schemas import ProjectWorkloadsStats, WorkloadStatusCount, WorkloadType

COMMON_METRICS_TIMESERIES = MetricsTimeseries(
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
                    status="Pending",
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
                    status="Pending",
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


# Helper function to create a valid ProjectCreate instance
def get_test_project_with_quota(name="project", description="A test project", cluster_id=None):
    if cluster_id is None:
        cluster_id = uuid4()

    return ProjectCreate(
        name=name,
        description=description,
        cluster_id=cluster_id,
        status=ProjectStatus.READY,
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,  # 1 GB
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
            gpu_count=0,
        ),
    )


# Reusable test data

COMMON_CLUSTER_WITH_RESOURCES = ClusterWithResources(
    id=uuid4(),
    name="TestCluster",
    base_url="http://test-cluster.example.com",
    last_heartbeat_at=datetime.now(tz=UTC),
    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    created_by="test@example.com",
    updated_by="test@example.com",
    available_resources=ClusterResources(
        cpu_milli_cores=10000,  # 10 cores
        memory_bytes=8 * 1024 * 1024 * 1024,  # 8 GB
        ephemeral_storage_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
        gpu_count=0,
    ),
    allocated_resources=ClusterResources(
        cpu_milli_cores=0,
        memory_bytes=0,
        ephemeral_storage_bytes=0,
        gpu_count=0,
    ),
    total_node_count=1,
    available_node_count=1,
    assigned_quota_count=0,
    gpu_info=None,
)

COMMON_QUOTA = QuotaResponse(
    id=uuid4(),
    cpu_milli_cores=1000,
    memory_bytes=1024 * 1024 * 1024,  # 1 GB
    ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
    gpu_count=0,
    status="Pending",
    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    created_by="test@example.com",
    updated_by="test@example.com",
)

COMMON_PROJECT_OUT = ProjectWithClusterAndQuota(
    id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
    name="project1",
    description="Description 1",
    cluster_id=uuid4(),
    created_at=datetime.now(tz=UTC),
    updated_at=datetime.now(tz=UTC),
    created_by="test_user",
    updated_by="test_user",
    status="Pending",
    status_reason="Creating",
    cluster=ClusterResponse(
        id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
        name="cluster1",
        base_url="http://cluster1.example.com",
        last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
    quota=QuotaResponse(
        id=uuid4(),
        cpu_milli_cores=1000,
        memory_bytes=1024 * 1024 * 1024,
        ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
        gpu_count=0,
        status="Pending",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        description="project quota",
    ),
)

COMMON_SECRET = SecretResponse(
    id=uuid4(),
    name="secretname",
    type=SecretType.EXTERNAL,
    scope=SecretScope.ORGANIZATION,
    status=SecretStatus.SYNCED,
    status_reason=None,
    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    created_by="test@example.com",
    updated_by="test@example.com",
)

COMMON_STORAGE = StorageResponse(
    id=uuid4(),
    name="storagename",
    secret_id=COMMON_SECRET.id,
    type=StorageType.S3,
    scope=StorageScope.ORGANIZATION,
    status=StorageStatus.SYNCED,
    status_reason=None,
    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    created_by="test@example.com",
    updated_by="test@example.com",
)

COMMON_PROJECT_SECRET = ProjectSecretWithParentSecret(
    id=uuid4(),
    secret=COMMON_SECRET,
    project_id=uuid4(),
    project_name="Name",
    status=ProjectSecretStatus.SYNCED,
    status_reason=None,
    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    created_by="test@example.com",
    updated_by="test@example.com",
)

COMMON_PROJECT_STORAGE = ProjectStorageWithParentStorage(
    id=uuid4(),
    storage=COMMON_STORAGE,
    project_id=uuid4(),
    project_name="Name",
    status=ProjectStorageStatus.SYNCED,
    status_reason=None,
    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
    created_by="test@example.com",
    updated_by="test@example.com",
)


@pytest.mark.asyncio
@patch(
    "app.projects.router.create_project_in_db",
    return_value=Project(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="project",
        description="Description 1",
        cluster_id="b4884301-b87c-4e4a-89bc-e60f458f176d",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        status=ProjectStatus.READY,
        status_reason="Project is ready",
    ),
)
@patch(
    "app.projects.router.get_cluster_by_id",
    return_value=ClusterResponse(
        id=uuid4(),
        name="TestCluster",
        base_url="https://test-cluster.example.com",
        last_heartbeat_at=datetime.now(tz=UTC),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
@patch("app.projects.router.create_quota")
@patch("app.projects.router.create_namespace_for_project")
async def test_create_project_success(
    mock_create_namespace_for_project,
    mock_create_quota,
    mock_get_cluster_by_id,
    mock_create_project_in_db,
):
    mock_quota_db = MagicMock()
    mock_create_quota.return_value = mock_quota_db

    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    project_create = get_test_project_with_quota(name="project", description="Description 1")

    with TestClient(app) as client:
        response = client.post("/v1/projects", json=json.loads(project_create.model_dump_json()))

    assert response.status_code == status.HTTP_201_CREATED

    mock_create_project_in_db.assert_called_once()
    mock_get_cluster_by_id.assert_called_once()
    mock_create_quota.assert_called_once()
    mock_create_namespace_for_project.assert_called_once()

    mock_get_user_organization.assert_called()
    mock_get_user.assert_called()


@pytest.mark.asyncio
@patch(
    "app.projects.router.create_project_in_db",
    side_effect=ConflictException("A project with name 'project' already exists in this cluster"),
)
@patch(
    "app.projects.router.get_cluster_by_id",
    return_value=ClusterResponse(
        id=uuid4(),
        name="TestCluster",
        base_url="https://test-cluster.example.com",
        last_heartbeat_at=datetime.now(tz=UTC),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_create_project_name_conflict(_, __):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    project_create = get_test_project_with_quota(name="project", description="Description 1")

    with TestClient(app) as client:
        response = client.post("/v1/projects", json=json.loads(project_create.model_dump_json()))

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_create_project_no_user():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.side_effect = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    project_create = get_test_project_with_quota(name="project1", description="Description 1")

    with TestClient(app) as client:
        response = client.post("/v1/projects", json=json.loads(project_create.model_dump_json()))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    project_create = get_test_project_with_quota(name="project1", description="Description 1")

    with TestClient(app) as client:
        response = client.post("/v1/projects", json=json.loads(project_create.model_dump_json()))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_project_no_organization():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    project_create = get_test_project_with_quota(name="project1", description="Description 1")

    with TestClient(app) as client:
        response = client.post("/v1/projects", json=json.loads(project_create.model_dump_json()))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_project_invalid_input():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.post(
            "/v1/projects", json={"name": "project 1", "description": "Description 1", "cluster_id": str(uuid4())}
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1", description="Description 1"),
)
@patch("app.projects.router.add_users_to_project_and_keycloak_group", return_value=None)
@pytest.mark.asyncio
async def test_add_users_to_project_success(_, __):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    body = ProjectAddUsers(user_ids=["9a6898dc-c8ef-4b7c-9b45-c1841d661a51", "f8cec8de-436c-4405-957d-ee36468c72c7"])

    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users", json=json.loads(body.model_dump_json())
        )

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_add_users_to_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    body = ProjectAddUsers(user_ids=["9a6898dc-c8ef-4b7c-9b45-c1841d661a51", "f8cec8de-436c-4405-957d-ee36468c72c7"])

    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users", json=json.loads(body.model_dump_json())
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_add_users_to_project_no_organization():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    body = ProjectAddUsers(user_ids=["9a6898dc-c8ef-4b7c-9b45-c1841d661a51", "f8cec8de-436c-4405-957d-ee36468c72c7"])

    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users", json=json.loads(body.model_dump_json())
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    side_effect=NotFoundException("Project not found"),
)
@pytest.mark.asyncio
async def test_add_users_to_project_no_project_found(_):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    body = ProjectAddUsers(user_ids=["9a6898dc-c8ef-4b7c-9b45-c1841d661a51", "f8cec8de-436c-4405-957d-ee36468c72c7"])

    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users", json=json.loads(body.model_dump_json())
        )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1", description="Description 1"),
)
@patch("app.projects.router.add_users_to_project_and_keycloak_group")
async def test_add_users_to_project_value_error(add_users_to_project_and_keycloak_group, _):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    add_users_to_project_and_keycloak_group.side_effect = ValueError("Some users not found in the organization.")

    body = ProjectAddUsers(user_ids=["9a6898dc-c8ef-4b7c-9b45-c1841d661a51", "f8cec8de-436c-4405-957d-ee36468c72c7"])

    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users", json=json.loads(body.model_dump_json())
        )
    assert response.json() == {"detail": "Some users not found in the organization."}


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1", description="Description 1"),
)
@patch("app.projects.router.remove_user_from_project_and_keycloak_group", return_value=None)
@pytest.mark.asyncio
async def test_remove_user_from_project_success(_, __):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.delete(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users/9a6898dc-c8ef-4b7c-9b45-c1841d661a51"
        )

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_remove_user_from_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.delete(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users/9a6898dc-c8ef-4b7c-9b45-c1841d661a51"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_remove_user_from_project_no_organization():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.delete(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users/9a6898dc-c8ef-4b7c-9b45-c1841d661a51"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    side_effect=NotFoundException("Project not found"),
)
@pytest.mark.asyncio
async def test_remove_user_from_project_no_project_found(_):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.delete(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users/9a6898dc-c8ef-4b7c-9b45-c1841d661a51"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1", description="Description 1"),
)
@patch("app.projects.router.remove_user_from_project_and_keycloak_group")
async def test_remove_user_from_project_value_error(remove_user_from_project_and_keycloak_group, _):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    remove_user_from_project_and_keycloak_group.side_effect = ValueError("User does not belong to the project.")

    with TestClient(app) as client:
        response = client.delete(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c/users/9a6898dc-c8ef-4b7c-9b45-c1841d661a51"
        )

    assert response.json() == {"detail": "User does not belong to the project."}


@pytest.mark.asyncio
async def test_update_project_success():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_email] = lambda: "test_user"
    app.dependency_overrides[ensure_platform_administrator] = lambda: None  # Just return None is enough

    project_obj = Project(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="project1",
        description="Description 1",
        cluster_id="b4884301-b87c-4e4a-89bc-e60f458f176d",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        status=ProjectStatus.READY,
        status_reason="Project is ready",
    )

    updated_quota = QuotaBase(
        cpu_milli_cores=2000,
        memory_bytes=2 * 1024 * 1024 * 1024,
        ephemeral_storage_bytes=10 * 1024 * 1024 * 1024,
        gpu_count=1,
        description="Updated quota",
    )
    project_update = ProjectEdit(description="An updated project", quota=updated_quota)

    project_output = COMMON_PROJECT_OUT

    mock_get_project = AsyncMock()
    mock_get_project.return_value = project_obj

    mock_update_project = AsyncMock()
    mock_update_project.return_value = project_obj

    mock_update_quota = AsyncMock()
    mock_update_quota.return_value = COMMON_QUOTA

    mock_validate = MagicMock()
    mock_validate.return_value = project_output

    with (
        patch("app.projects.router.get_project_by_id", mock_get_project),
        patch("app.projects.router.update_project_in_db", mock_update_project),
        patch("app.projects.router.update_project_quota", mock_update_quota),
        TestClient(app) as client,
    ):
        response = client.put(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c", json=json.loads(project_update.model_dump_json())
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_update_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.put("/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_project_no_organization():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    project_update = ProjectEdit(
        description="Updated Description",
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,  # 1 GB
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
            gpu_count=0,
        ),
    )

    with TestClient(app) as client:
        response = client.put(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c", json=json.loads(project_update.model_dump_json())
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    side_effect=NotFoundException("Project not found"),
)
@pytest.mark.asyncio
async def test_update_project_no_project_found(_):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    project_update = ProjectEdit(
        description="Updated Description",
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,  # 1 GB
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
            gpu_count=0,
        ),
    )

    with TestClient(app) as client:
        response = client.put(
            "/v1/projects/b7c13f41-258d-44b1-a694-5dd4ccda660c", json=json.loads(project_update.model_dump_json())
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_project_invalid_input():
    # Set up authentication mocks (but don't mock the validation layer)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[get_user_email] = lambda: "test@example.com"
    app.dependency_overrides[get_session] = lambda: MagicMock()

    valid_project_id = "b7c13f41-258d-44b1-a694-5dd4ccda660c"

    with TestClient(app) as client:
        # Test 1: Description too short (min_length=2)
        response = client.put(
            f"/v1/projects/{valid_project_id}",
            json={
                "description": "a",  # Too short
                "quota": {
                    "cpu_milli_cores": 1000,
                    "memory_bytes": 1000000000,
                    "ephemeral_storage_bytes": 1000000000,
                    "gpu_count": 0,
                },
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test 2: Description too long (max_length=1024)
        response = client.put(
            f"/v1/projects/{valid_project_id}",
            json={
                "description": "x" * 1025,  # Too long
                "quota": {
                    "cpu_milli_cores": 1000,
                    "memory_bytes": 1000000000,
                    "ephemeral_storage_bytes": 1000000000,
                    "gpu_count": 0,
                },
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test 3: Missing required quota field
        response = client.put(f"/v1/projects/{valid_project_id}", json={"description": "Valid description"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test 4: Extra forbidden field
        response = client.put(
            f"/v1/projects/{valid_project_id}",
            json={
                "description": "Valid description",
                "quota": {
                    "cpu_milli_cores": 1000,
                    "memory_bytes": 1000000000,
                    "ephemeral_storage_bytes": 1000000000,
                    "gpu_count": 0,
                },
                "forbidden_field": "should not be allowed",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    side_effect=NotFoundException("Project not found"),
)
async def test_get_project_not_found(_):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_user_organization] = lambda: MagicMock(spec=Organization)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Project not found"}


@pytest.mark.asyncio
async def test_get_project_not_in_organization():
    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with TestClient(app) as client:
        response = client.get("/v1/projects/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_project_no_organization():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    with TestClient(app) as client:
        response = client.get("/v1/projects/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1", description="Description 1"),
)
@patch(
    "app.projects.router.get_project_with_users",
    return_value=ProjectWithUsers(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="project1",
        description="Description 1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        status="Pending",
        status_reason="Creating",
        users=[],
        invited_users=[
            InvitedUser(
                id="0aa18e92-002c-45b7-a06e-dcdc0277974d",
                email="user2@test.com",
                role=Roles.PLATFORM_ADMINISTRATOR.value,
                invited_at="2025-02-11T03:42:02.524263Z",
                invited_by="user1",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
            )
        ],
        cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
        cluster=ClusterResponse(
            id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
            name="cluster1",
            base_url="https://test-cluster.example.com",
            last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        quota=QuotaResponse(
            id="78f6da5c-e78c-46df-bb2d-934abd05221f",
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,  # 1 GB
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
            gpu_count=0,
            status="Pending",
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ),
)
async def test_get_project_with_invited_users_success(_, __):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    expected = {
        "name": "project1",
        "description": "Description 1",
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "cluster_id": "1ab18e82-012c-45b7-a36e-dc3c0277974d",
        "status": "Pending",
        "status_reason": "Creating",
        "users": [],
        "invited_users": [
            {
                "id": "0aa18e92-002c-45b7-a06e-dcdc0277974d",
                "email": "user2@test.com",
                "role": "Platform Administrator",
                "invited_at": "2025-02-11T03:42:02.524263Z",
                "invited_by": "user1",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            }
        ],
        "cluster": {
            "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
            "last_heartbeat_at": "2025-03-10T12:00:00Z",
            "name": "cluster1",
            "status": "unhealthy",
            "created_at": "2025-01-01T12:00:00Z",
            "created_by": "test@example.com",
            "updated_at": "2025-01-01T12:00:00Z",
            "updated_by": "test@example.com",
            "base_url": "https://test-cluster.example.com",
        },
        "quota": {
            "cpu_milli_cores": 1000,
            "ephemeral_storage_bytes": 5368709120,
            "gpu_count": 0,
            "id": "78f6da5c-e78c-46df-bb2d-934abd05221f",
            "memory_bytes": 1073741824,
            "status": "Pending",
            "status_reason": None,
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-01T12:00:00Z",
            "created_by": "test@example.com",
            "updated_by": "test@example.com",
        },
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }
    assert response_json == expected


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_project_by_id",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1", description="Description 1"),
)
@patch(
    "app.projects.router.get_project_with_users",
    return_value=ProjectWithUsers(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="project1",
        description="Description 1",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        users=[
            UserResponse(
                id="0aa18e92-002c-45b7-a06e-dcdc0277974c",
                first_name="John",
                last_name="Doe",
                email="test@test.com",
                role=Roles.PLATFORM_ADMINISTRATOR.value,
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
            )
        ],
        invited_users=[],
        cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
        status="Pending",
        status_reason="Creating",
        cluster=ClusterResponse(
            id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
            name="cluster1",
            last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
            base_url="https://example.com",
        ),
        quota=QuotaResponse(
            id="78f6da5c-e78c-46df-bb2d-934abd05221f",
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
            gpu_count=0,
            status="Pending",
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ),
)
async def test_get_project_success(_, __):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects/0aa18e92-002c-45b7-a06e-dcdb0277974c")

    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    expected = {
        "name": "project1",
        "description": "Description 1",
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "cluster_id": "1ab18e82-012c-45b7-a36e-dc3c0277974d",
        "status": "Pending",
        "status_reason": "Creating",
        "users": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "test@test.com",
                "id": "0aa18e92-002c-45b7-a06e-dcdc0277974c",
                "role": "Platform Administrator",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
                "last_active_at": None,
            }
        ],
        "cluster": {
            "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
            "last_heartbeat_at": "2025-03-10T12:00:00Z",
            "name": "cluster1",
            "status": "unhealthy",
            "created_at": "2025-01-01T12:00:00Z",
            "created_by": "test@example.com",
            "updated_at": "2025-01-01T12:00:00Z",
            "updated_by": "test@example.com",
            "base_url": "https://example.com",
        },
        "invited_users": [],
        "quota": {
            "cpu_milli_cores": 1000,
            "ephemeral_storage_bytes": 5368709120,
            "gpu_count": 0,
            "id": "78f6da5c-e78c-46df-bb2d-934abd05221f",
            "memory_bytes": 1073741824,
            "status": "Pending",
            "status_reason": None,
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-01T12:00:00Z",
            "created_by": "test@example.com",
            "updated_by": "test@example.com",
        },
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }
    assert response_json == expected


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_projects_with_resource_allocation",
    return_value=ProjectsWithResourceAllocation(
        projects=[
            ProjectWithResourceAllocation(
                id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
                name="project1",
                description="Description 1",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                cluster_id="0aa18e92-102c-45b7-a06e-dcdb0277974c",
                status="Pending",
                status_reason="Creating",
                cluster=ClusterWithResources(
                    id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    name="cluster1",
                    last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    base_url="https://example.com",
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
                    status="Pending",
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                ),
            ),
            ProjectWithResourceAllocation(
                id="65b44238-556d-4e59-82ea-ddfafc5491f3",
                name="project2",
                description="Description 2",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                cluster_id="0aa18e92-302c-45b7-a06e-dcdb0277974c",
                status="Pending",
                status_reason="Creating",
                cluster=ClusterWithResources(
                    id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    name="cluster1",
                    last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    base_url="https://example.com",
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
                    status="Pending",
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                ),
            ),
        ]
    ),
)
async def test_get_projects_success(_):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user] = lambda: MagicMock(spec_set=str)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects")

    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    expected = {
        "projects": [
            {
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "name": "project1",
                "description": "Description 1",
                "cluster_id": "0aa18e92-102c-45b7-a06e-dcdb0277974c",
                "status": "Pending",
                "status_reason": "Creating",
                "cluster": {
                    "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "base_url": "https://example.com",
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
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                },
                "gpu_allocation_percentage": 0.0,
                "gpu_allocation_exceeded": False,
                "cpu_allocation_percentage": 12.5,
                "cpu_allocation_exceeded": False,
                "memory_allocation_percentage": 6.25,
                "memory_allocation_exceeded": False,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
            {
                "id": "65b44238-556d-4e59-82ea-ddfafc5491f3",
                "name": "project2",
                "description": "Description 2",
                "cluster_id": "0aa18e92-302c-45b7-a06e-dcdb0277974c",
                "status": "Pending",
                "status_reason": "Creating",
                "cluster": {
                    "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "base_url": "https://example.com",
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
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
        ]
    }
    assert response_json == expected


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_projects_with_resource_allocation",
    return_value=ProjectsWithResourceAllocation(projects=[]),
)
@patch(
    "app.projects.router.get_user_organization",
    return_value=Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    ),
)
async def test_get_projects_no_projects(_, __):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_user_organization] = lambda: MagicMock(spec=Organization)
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"projects": []}


@pytest.mark.asyncio
async def test_get_projects_no_organization():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_projects_not_in_role():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    mock_ensure_platform_administrator = MagicMock(spec_set=[])
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get("/v1/projects")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.clusters.router.get_projects_in_cluster_with_resource_allocation",
    return_value=ProjectsWithResourceAllocation(
        projects=[
            ProjectWithResourceAllocation(
                id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
                name="project1",
                description="Description 1",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                cluster_id="0aa18e92-102c-45b7-a06e-dcdb0277974c",
                status="Pending",
                status_reason="Creating",
                cluster=ClusterWithResources(
                    id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    name="cluster1",
                    last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    base_url="https://example.com",
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
                    status="Pending",
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                ),
            ),
            ProjectWithClusterAndQuota(
                id="65b44238-556d-4e59-82ea-ddfafc5491f3",
                name="project2",
                description="Description 2",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                cluster_id="0aa18e92-302c-45b7-a06e-dcdb0277974c",
                status="Pending",
                status_reason="Creating",
                cluster=ClusterWithResources(
                    id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    name="cluster1",
                    last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    base_url="https://example.com",
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
                    status="Pending",
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
    return_value=ClusterResponse(
        base_url="https://test-cluster.example.com",
        id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
        name="cluster1",
        last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
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
    response_json = response.json()
    expected = {
        "projects": [
            {
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "name": "project1",
                "description": "Description 1",
                "cluster_id": "0aa18e92-102c-45b7-a06e-dcdb0277974c",
                "status": "Pending",
                "status_reason": "Creating",
                "cluster": {
                    "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "base_url": "https://example.com",
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
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                },
                "gpu_allocation_percentage": 0.0,
                "gpu_allocation_exceeded": False,
                "cpu_allocation_percentage": 12.5,
                "cpu_allocation_exceeded": False,
                "memory_allocation_percentage": 6.25,
                "memory_allocation_exceeded": False,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
            {
                "id": "65b44238-556d-4e59-82ea-ddfafc5491f3",
                "name": "project2",
                "description": "Description 2",
                "cluster_id": "0aa18e92-302c-45b7-a06e-dcdb0277974c",
                "status": "Pending",
                "status_reason": "Creating",
                "cluster": {
                    "id": "e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "base_url": "https://example.com",
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
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
        ]
    }
    assert response_json == expected


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
async def test_get_submittable_projects_no_user():
    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    mock_get_projects_accessible_to_user = MagicMock(spec_set=str)
    mock_get_projects_accessible_to_user.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: mock_get_projects_accessible_to_user()
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock(spec_set=dict)

    with TestClient(app) as client:
        response = client.get("/v1/projects/submittable")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.projects.router.get_submittable_projects_from_db",
    return_value=Projects(
        projects=[
            ProjectWithClusterAndQuota(
                id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
                name="project1",
                description="Description 1",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
                cluster_id=uuid4(),
                status=ProjectStatus.READY,
                cluster=ClusterResponse(
                    id="e60079a8-a2a2-4fe4-b5d6-480d03c2a666",
                    name="cluster1",
                    base_url="https://test-cluster.example.com",
                    last_heartbeat_at=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                ),
                quota=QuotaResponse(
                    id=uuid4(),
                    cpu_milli_cores=1000,
                    memory_bytes=1024 * 1024 * 1024,  # 1 GB
                    ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
                    gpu_count=0,
                    status="Pending",
                    created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                ),
            ),
        ]
    ),
)
async def test_get_submittable_projects_success(_):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/projects/submittable")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch("app.projects.router.get_project_by_id")
@patch("app.projects.router.get_cluster_with_resources")
@patch("app.projects.router.submit_delete_project")
async def test_delete_project_with_quota_success(
    mock_submit_delete_project,
    mock_get_cluster_with_resources,
    mock_get_project_by_id,
):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id=uuid4(), name="Org", keycloak_organization_id="kc"
    )
    app.dependency_overrides[get_user_email] = lambda: "test_user"
    app.dependency_overrides[ensure_platform_administrator] = lambda: None

    quota = MagicMock()
    quota.cluster = MagicMock()
    quota.cluster.gpu_info = None
    project = MagicMock()
    project.quota = quota
    project.cluster = quota.cluster
    mock_get_project_by_id.return_value = project

    mock_get_cluster_with_resources.return_value = MagicMock(gpu_info=None)

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{uuid4()}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_get_project_by_id.assert_called_once()
    mock_get_cluster_with_resources.assert_called_once_with(mock_session, project.cluster)
    mock_submit_delete_project.assert_called_once_with(mock_session, project, "test_user", None)


@pytest.mark.asyncio
@patch("app.projects.router.get_project_by_id", side_effect=NotFoundException("Project not found"))
async def test_delete_project_not_found(mock_get_project_by_id):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_user_organization] = lambda: Organization(
        id=uuid4(), name="Org", keycloak_organization_id="kc"
    )
    app.dependency_overrides[get_user_email] = lambda: "test_user"
    app.dependency_overrides[ensure_platform_administrator] = lambda: None

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{uuid4()}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Project not found"}


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_stats_for_workloads_in_project")
async def test_get_project_workload_stats_success(mock_get_stats, mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"

    mock_get_project.return_value = mock_project

    mock_get_stats.return_value = ProjectWorkloadsStats(
        name="Test Project",
        total_workloads=5,
        statusCounts=[
            WorkloadStatusCount(status=WorkloadStatus.RUNNING, count=3),
            WorkloadStatusCount(status=WorkloadStatus.PENDING, count=2),
        ],
    )

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{project_id}/workloads/stats")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["total_workloads"] == 5
    assert {sc["status"] for sc in data["statusCounts"]} == {"Running", "Pending"}


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization", return_value=None)
@patch("app.projects.router.get_stats_for_workloads_in_project", return_value=None)
async def test_get_project_workload_stats_project_not_found(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{project_id}/workloads/stats")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"Project with ID {project_id} not found in your organization"

    app.dependency_overrides = {}


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization", autospec=True)
@patch("app.projects.router.get_workloads_metrics_by_project", autospec=True)
async def test_get_project_workload_metrics_success(mock_get_metrics, mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "TestProject"

    mock_get_project.return_value = mock_project

    mock_get_metrics.return_value = WorkloadsWithMetrics(
        workloads=[
            WorkloadWithMetrics(
                id=uuid4(),
                project_id=project_id,
                cluster_id=uuid4(),
                status=WorkloadStatus.RUNNING,
                display_name="Mock Workload",
                type=WorkloadType.CUSTOM,
                gpu_count=2,
                vram=8192,
                run_time=3600,
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
        response = client.get(f"/v1/projects/{project_id}/workloads/metrics")

    assert response.status_code == 200
    data = response.json()
    assert "workloads" in data
    assert len(data["workloads"]) == 1
    assert data["workloads"][0]["display_name"] == "Mock Workload"


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization", autospec=True)
@patch("app.projects.router.get_workloads_metrics_by_project", autospec=True)
async def test_get_project_workload_metrics_project_not_found(mock_get_metrics, mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization

    project_id = uuid4()

    mock_get_project.return_value = None
    mock_get_metrics.return_value = None

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{project_id}/workloads/metrics")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"


@pytest.mark.asyncio
@patch("app.projects.router.validate_datetime_range", autospec=True)
@patch(
    "app.projects.router.get_gpu_device_utilization_timeseries_for_project_from_ds",
    return_value=COMMON_METRICS_TIMESERIES,
)
@patch(
    "app.projects.router.get_project_in_organization",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1"),
)
async def test_get_gpu_device_utilization_timeseries_for_project_success(_, __, ___):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{uuid4()}/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
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
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
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
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
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
@patch("app.projects.router.get_project_in_organization", autospec=True)
async def test_get_gpu_device_utilization_timeseries_for_project_project_not_found(mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    mock_get_project.return_value = None

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"


@pytest.mark.asyncio
async def test_get_gpu_device_utilization_timeseries_for_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    project_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_gpu_device_utilization_timeseries_for_project_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    project_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.projects.router.validate_datetime_range", autospec=True)
@patch(
    "app.projects.router.get_gpu_memory_utilization_timeseries_for_project_from_ds",
    return_value=COMMON_METRICS_TIMESERIES,
)
@patch(
    "app.projects.router.get_project_in_organization",
    return_value=Project(id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="project1"),
)
async def test_get_gpu_memory_utilization_timeseries_for_project_success(_, __, ___):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{uuid4()}/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
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
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
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
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
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
@patch("app.projects.router.get_project_in_organization", autospec=True)
async def test_get_gpu_memory_utilization_timeseries_for_project_project_not_found(mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    mock_get_project.return_value = None

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"


@pytest.mark.asyncio
async def test_get_gpu_memory_utilization_timeseries_for_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    project_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_gpu_memory_utilization_timeseries_for_project_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    project_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization", autospec=True)
@patch("app.projects.router.validate_datetime_range", autospec=True)
@patch(
    "app.projects.router.get_average_wait_time_for_project_from_ds",
    return_value=MetricsScalarWithRange(
        data=10000,
        range=DateRange(
            start=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
            end=datetime(2025, 3, 11, 12, 0, 0, tzinfo=UTC),
        ),
    ),
)
async def test_average_wait_time_for_project_success(_, __, mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"

    mock_get_project.return_value = mock_project

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/average_wait_time?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == 200
    assert response.json() == {
        "data": 10000,
        "range": {
            "start": "2025-03-10T12:00:00Z",
            "end": "2025-03-11T12:00:00Z",
        },
    }


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization", autospec=True)
async def test_get_average_wait_time_for_project_project_not_found(mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    mock_get_project.return_value = None

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/average_wait_time?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"


@pytest.mark.asyncio
async def test_get_average_wait_time_for_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    project_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/average_wait_time?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization", autospec=True)
@patch("app.projects.router.validate_datetime_range", autospec=True)
@patch(
    "app.projects.router.get_avg_gpu_idle_time_for_project_from_ds",
    return_value=MetricsScalarWithRange(
        data=20000,
        range=DateRange(
            start=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
            end=datetime(2025, 3, 11, 12, 0, 0, tzinfo=UTC),
        ),
    ),
)
async def test_get_avg_gpu_idle_time_for_project_success(_, __, mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"

    mock_get_project.return_value = mock_project

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/average_gpu_idle_time?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == 200
    assert response.json() == {
        "data": 20000,
        "range": {
            "start": "2025-03-10T12:00:00Z",
            "end": "2025-03-11T12:00:00Z",
        },
    }


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization", autospec=True)
async def test_get_avg_gpu_idle_time_for_project_project_not_found(mock_get_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    project_id = uuid4()

    mock_get_project.return_value = None

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/average_gpu_idle_time?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"


@pytest.mark.asyncio
async def test_get_avg_gpu_idle_time_for_project_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()
    project_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{project_id}/metrics/average_gpu_idle_time?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z"
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.projects.router.get_project_storages_in_project")
@patch("app.projects.router.is_user_in_role", return_value=True)
@patch("app.projects.router.get_project_in_organization", return_value=MagicMock(spec=Project))
async def test_get_project_storages_platform_admin(_, __, mock_get_project_storages_in_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    mock_get_project_storages_in_project.return_value = ProjectStoragesWithParentStorage(
        project_storages=[COMMON_PROJECT_STORAGE]
    )

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{uuid4()}/storages")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch("app.projects.router.get_project_storages_in_project")
@patch("app.projects.router.is_user_in_role", return_value=False)
@patch("app.projects.router.get_projects_accessible_to_user", return_value=MagicMock(autospec=True))
@patch("app.projects.router.validate_and_get_project_from_query", return_value=MagicMock(spec=Project))
async def test_get_project_storages_team_member(_, __, ___, mock_get_project_storages_in_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    mock_get_project_storages_in_project.return_value = ProjectStoragesWithParentStorage(
        project_storages=[COMMON_PROJECT_STORAGE]
    )

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{uuid4()}/storages")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch("app.projects.router.get_project_storages_in_project")
@patch("app.projects.router.is_user_in_role", return_value=False)
@patch("app.projects.router.get_projects_accessible_to_user", return_value=MagicMock(autospec=True))
@patch("app.projects.router.validate_and_get_project_from_query", side_effect=HTTPException(status_code=403))
async def test_get_project_storages_team_member_no_access(_, __, ___, mock_get_project_storages_in_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    mock_get_project_storages_in_project.return_value = ProjectStoragesWithParentStorage(
        project_storages=[COMMON_PROJECT_STORAGE]
    )

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{uuid4()}/storages")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.projects.router.is_user_in_role", return_value=True)
@patch("app.projects.router.get_project_in_organization", return_value=None)
async def test_get_project_storages_team_member_no_project(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{uuid4()}/storages")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.projects.router.get_project_storage", return_value=None)
@patch(
    "app.projects.router.submit_delete_project_storage",
)
async def test_delete_project_storage_not_found(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    project_id = uuid4()
    storage_id = uuid4()

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{project_id}/storages/{storage_id}")

    assert response.status_code == 404
    assert "Project Storage not found" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.projects.router.get_project_storage")
@patch(
    "app.projects.router.submit_delete_project_storage",
)
async def test_delete_project_storage_success(mock_submit_delete_project_storage, mock_get_project_storage):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock(spec_set=[])

    project_id = uuid4()
    storage_id = uuid4()

    mock_project_storage = ProjectStorageModel(
        id=uuid4(), storage_id=storage_id, project_id=project_id, status=ProjectStorageStatus.SYNCED
    )
    mock_get_project_storage.return_value = mock_project_storage

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{project_id}/storages/{storage_id}")

    assert response.status_code == 204
    mock_submit_delete_project_storage.assert_called_once()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_secrets_in_project")
@patch("app.projects.router.is_user_in_role", return_value=False)
@patch("app.projects.router.get_projects_accessible_to_user", return_value=MagicMock(autospec=True))
@patch("app.projects.router.validate_and_get_project_from_query", return_value=MagicMock(spec=Project))
async def test_get_project_secrets_team_member(_, __, ___, mock_get_project_secrets_in_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    mock_get_project_secrets_in_project.return_value = ProjectSecretsWithParentSecret(
        project_secrets=[COMMON_PROJECT_SECRET]
    )

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{uuid4()}/secrets")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch("app.projects.router.get_project_secrets_in_project")
@patch("app.projects.router.is_user_in_role", return_value=True)
@patch("app.projects.router.get_project_in_organization", new_callable=AsyncMock)
async def test_get_project_secrets_filtered_by_use_case(
    mock_get_project,
    _is_admin,
    mock_get_project_secrets_in_project,
):
    mock_project = MagicMock(spec=Project)
    mock_get_project.return_value = mock_project

    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    mock_get_project_secrets_in_project.return_value = ProjectSecretsWithParentSecret(project_secrets=[])

    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{uuid4()}/secrets",
            params={
                "use_case": SecretUseCase.HUGGING_FACE.value,
                "secret_type": SecretType.KUBERNETES_SECRET.value,
            },
        )

    assert response.status_code == status.HTTP_200_OK
    mock_get_project.assert_called_once()
    mock_get_project_secrets_in_project.assert_called_once()
    args, kwargs = mock_get_project_secrets_in_project.call_args
    # Arguments are passed positionally; ensure filters were forwarded.
    assert len(args) >= 5
    assert args[3] == SecretType.KUBERNETES_SECRET
    assert args[4] == SecretUseCase.HUGGING_FACE


@pytest.mark.asyncio
@patch("app.projects.router.get_project_secrets_in_project")
@patch("app.projects.router.is_user_in_role", return_value=False)
@patch("app.projects.router.get_projects_accessible_to_user", return_value=MagicMock(autospec=True))
@patch("app.projects.router.validate_and_get_project_from_query", side_effect=HTTPException(status_code=403))
async def test_get_project_secrets_team_member_no_access(_, __, ___, mock_get_project_secrets_in_project):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    mock_get_project_secrets_in_project.return_value = ProjectSecretsWithParentSecret(
        project_secrets=[COMMON_PROJECT_SECRET]
    )

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{uuid4()}/secrets")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.projects.router.is_user_in_role", return_value=True)
@patch("app.projects.router.get_project_in_organization", return_value=None)
async def test_get_project_secrets_team_member_no_project(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_user_organization] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/{uuid4()}/secrets")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.projects.router.get_project_secret", return_value=None)
@patch(
    "app.projects.router.submit_delete_project_secret",
)
@patch(
    "app.projects.router.ensure_can_remove_secret_from_projects",
)
async def test_delete_project_secret_not_found(_, __, ___):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    project_id = uuid4()
    secret_id = uuid4()

    # Mock project with matching ID to ensure user has access
    mock_project = MagicMock(spec=Project)
    mock_project.id = project_id

    # Mock claimset without platform admin role (regular user)
    mock_claimset = {"realm_access": {"roles": []}}

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [mock_project]
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{project_id}/secrets/{secret_id}")

    assert response.status_code == 404
    assert "Project Secret not found" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.projects.router.get_project_secret")
@patch(
    "app.projects.router.submit_delete_project_secret",
)
@patch(
    "app.projects.router.ensure_can_remove_secret_from_projects",
)
async def test_delete_project_secret_success(
    mock_ensure_can_remove_secret_from_projects, mock_submit_delete_project_secret, mock_get_project_secret
):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    project_id = uuid4()
    secret_id = uuid4()

    # Mock project with matching ID to ensure user has access
    mock_project = MagicMock(spec=Project)
    mock_project.id = project_id

    # Mock claimset without platform admin role (regular user)
    mock_claimset = {"realm_access": {"roles": []}}

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [mock_project]
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset

    mock_project_secret = ProjectSecretModel(
        id=uuid4(), secret_id=secret_id, project_id=project_id, status=ProjectSecretStatus.SYNCED
    )
    mock_get_project_secret.return_value = mock_project_secret

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{project_id}/secrets/{secret_id}")

    assert response.status_code == 204
    mock_submit_delete_project_secret.assert_called_once()
    mock_ensure_can_remove_secret_from_projects.assert_called_once()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_secret")
@patch("app.projects.router.submit_delete_project_secret")
@patch("app.projects.router.ensure_can_remove_secret_from_projects")
async def test_delete_project_secret_platform_admin_no_membership(
    mock_ensure_can_remove_secret_from_projects, mock_submit_delete_project_secret, mock_get_project_secret
):
    """Platform admins can delete secrets from any project, even if they're not members."""
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    project_id = uuid4()
    secret_id = uuid4()

    # Mock claimset WITH platform admin role
    mock_claimset = {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    # Empty accessible projects list - admin is NOT a member of this project
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: []
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset

    mock_project_secret = ProjectSecretModel(
        id=uuid4(), secret_id=secret_id, project_id=project_id, status=ProjectSecretStatus.SYNCED
    )
    mock_get_project_secret.return_value = mock_project_secret

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{project_id}/secrets/{secret_id}")

    assert response.status_code == 204
    mock_submit_delete_project_secret.assert_called_once()
    mock_ensure_can_remove_secret_from_projects.assert_called_once()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_secret")
@patch("app.projects.router.submit_delete_project_secret")
@patch("app.projects.router.ensure_can_remove_secret_from_projects")
async def test_delete_project_secret_secret_ref_by_storage_error(
    mock_ensure_can_remove_secret_from_projects,
    mock_submit_delete_project_secret,
    mock_get_project_secret,
):
    """
    When the secret is still referenced by storages in the project, the delete
    should fail and must not submit a delete message.
    """
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    # Platform admin but business rule still applies
    mock_claimset = {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset

    # Admin is not a member of the project (doesn't matter for this error path)
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: []

    project_id = uuid4()
    secret_id = uuid4()

    # The project-secret exists
    mock_project_secret = ProjectSecretModel(
        id=uuid4(), secret_id=secret_id, project_id=project_id, status=ProjectSecretStatus.SYNCED
    )
    mock_get_project_secret.return_value = mock_project_secret

    # Simulate validation failure: secret still referenced by storages
    mock_ensure_can_remove_secret_from_projects.side_effect = ValidationException(
        "Cannot remove this secret because it is still referenced by storages in the project."
    )

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/{project_id}/secrets/{secret_id}")

    assert response.status_code == 400
    mock_ensure_can_remove_secret_from_projects.assert_called_once()
    mock_submit_delete_project_secret.assert_not_called()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_secret_in_organization")
@patch("app.projects.router.get_project_secret")
@patch("app.projects.router.assign_projects_to_secret")
async def test_assign_project_secrets_success(
    mock_assign_projects_to_secret,
    mock_get_project_secret,
    mock_get_secret,
    mock_get_project,
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    # Mock get project_in_organization
    project_id = uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"
    mock_get_project.return_value = mock_project

    secret_id = uuid4()
    mock_secret = MagicMock()
    mock_secret.id = secret_id
    mock_secret.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_secret.name = "Test Secret"
    mock_get_secret.return_value = mock_secret

    mock_get_project_secret.return_value = None

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/secrets/{secret_id}/assign")

    # Assert
    assert response.status_code == 204
    mock_get_project.assert_called_once()
    mock_get_secret.assert_called_once()
    mock_get_project_secret.assert_called_once()
    mock_assign_projects_to_secret.assert_called_once()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_secret_in_organization")
@patch("app.projects.router.get_project_secret")
@patch("app.projects.router.assign_projects_to_secret")
async def test_assign_project_secrets_project_not_found(
    mock_assign_projects_to_secret,
    mock_get_project_secret,
    mock_get_secret,
    mock_get_project,
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    project_id = uuid4()
    mock_get_project.return_value = None

    secret_id = uuid4()

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/secrets/{secret_id}/assign")

    assert response.status_code == 404
    assert "Project not found" in response.json()["detail"]
    mock_get_project.assert_called_once()
    mock_get_secret.assert_not_called()
    mock_get_project_secret.assert_not_called()
    mock_assign_projects_to_secret.assert_not_called()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_secret_in_organization")
@patch("app.projects.router.get_project_secret")
@patch("app.projects.router.assign_projects_to_secret")
async def test_assign_project_secrets_secret_not_found(
    mock_assign_projects_to_secret,
    mock_get_project_secret,
    mock_get_secret,
    mock_get_project,
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    project_id = uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"
    mock_get_project.return_value = mock_project

    secret_id = uuid4()
    mock_get_secret.return_value = None

    mock_get_project_secret.return_value = None

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/secrets/{secret_id}/assign")

    assert response.status_code == 404
    mock_get_project.assert_called_once()
    mock_get_secret.assert_called_once()
    mock_get_project_secret.assert_not_called()
    mock_assign_projects_to_secret.assert_not_called()

    assert response.status_code == 404
    assert "Secret not found" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_secret_in_organization")
@patch("app.projects.router.get_project_secret")
@patch("app.projects.router.assign_projects_to_secret")
async def test_assign_project_secrets_already_assigned(
    mock_assign_projects_to_secret, mock_get_project_secret, mock_get_secret, mock_get_project
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    project_id = uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"
    mock_get_project.return_value = mock_project

    secret_id = uuid4()
    mock_secret = MagicMock()
    mock_secret.id = secret_id
    mock_secret.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_secret.name = "Test Secret"
    mock_get_secret.return_value = mock_secret

    project_secret_id = uuid4()
    project_secret = MagicMock()
    project_secret.id = project_secret_id
    project_secret.project_id = project_id
    project_secret.secret_id = secret_id
    mock_get_project_secret.return_value = project_secret

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/secrets/{secret_id}/assign")

    assert response.status_code == 400
    assert response.json()["detail"] == "Secret already assigned to this Project"
    mock_get_project.assert_called_once()
    mock_get_secret.assert_called_once()
    mock_get_project_secret.assert_called_once()
    mock_assign_projects_to_secret.assert_not_called()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_storage_in_organization")
@patch("app.projects.router.get_project_storage")
@patch("app.projects.router.assign_projects_to_storage")
async def test_assign_project_storage_success(
    mock_assign_projects_to_storage,
    mock_get_project_storage,
    mock_get_storage,
    mock_get_project,
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    # Mock get project_in_organization
    project_id = uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"
    mock_get_project.return_value = mock_project

    storage_id = uuid4()
    mock_storage = MagicMock()
    mock_storage.id = storage_id
    mock_storage.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_storage.name = "Test Storage"
    mock_get_storage.return_value = mock_storage

    mock_get_project_storage.return_value = None

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/storages/{storage_id}/assign")

    # Assert
    assert response.status_code == 204
    mock_get_project.assert_called_once()
    mock_get_storage.assert_called_once()
    mock_get_project_storage.assert_called_once()
    mock_assign_projects_to_storage.assert_called_once()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_storage_in_organization")
@patch("app.projects.router.get_project_storage")
@patch("app.projects.router.assign_projects_to_storage")
async def test_assign_project_storage_project_not_found(
    mock_assign_projects_to_storage,
    mock_get_project_storage,
    mock_get_storage,
    mock_get_project,
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    project_id = uuid4()
    mock_get_project.return_value = None

    storage_id = uuid4()
    mock_get_storage.return_value = None

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/storages/{storage_id}/assign")

    assert response.status_code == 404
    assert "Project not found" in response.json()["detail"]
    mock_get_project.assert_called_once()
    mock_get_storage.assert_not_called()
    mock_get_project_storage.assert_not_called()
    mock_assign_projects_to_storage.assert_not_called()


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_storage_in_organization")
@patch("app.projects.router.get_project_storage")
@patch("app.projects.router.assign_projects_to_storage")
async def test_assign_project_storage_storage_not_found(
    mock_assign_projects_to_storage,
    mock_get_project_storage,
    mock_get_storage,
    mock_get_project,
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    project_id = uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"
    mock_get_project.return_value = mock_project

    storage_id = uuid4()
    mock_get_storage.return_value = None

    mock_get_project_storage.return_value = None

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/storages/{storage_id}/assign")

    assert response.status_code == 404
    mock_get_project.assert_called_once()
    mock_get_storage.assert_called_once()
    mock_get_project_storage.assert_not_called()
    mock_assign_projects_to_storage.assert_not_called()

    assert response.status_code == 404
    assert "Storage not found" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.projects.router.get_project_in_organization")
@patch("app.projects.router.get_storage_in_organization")
@patch("app.projects.router.get_project_storage")
@patch("app.projects.router.assign_projects_to_storage")
async def test_assign_project_storages_already_assigned(
    mock_assign_projects_to_storage,
    mock_get_project_storage,
    mock_get_storage,
    mock_get_project,
):
    # Dependencies
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock(spec=Organization)
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    project_id = uuid4()
    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_project.name = "Test Project"
    mock_get_project.return_value = mock_project

    storage_id = uuid4()
    mock_storage = MagicMock()
    mock_storage.id = storage_id
    mock_storage.organization_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    mock_storage.name = "Test Storage"
    mock_get_storage.return_value = mock_storage

    project_storage_id = uuid4()
    project_storage = MagicMock()
    project_storage.id = project_storage_id
    project_storage.project_id = project_id
    project_storage.storage_id = storage_id
    mock_get_project_storage.return_value = project_storage

    with TestClient(app) as client:
        response = client.put(f"/v1/projects/{project_id}/storages/{storage_id}/assign")

    assert response.status_code == 400
    assert response.json()["detail"] == "Storage already assigned to this Project"
    mock_get_project.assert_called_once()
    mock_get_storage.assert_called_once()
    mock_get_project_storage.assert_called_once()
    mock_assign_projects_to_storage.assert_not_called()
