# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from airm.messaging.schemas import QuotaStatus, WorkloadStatus
from app import app  # type: ignore
from app.clusters.models import Cluster
from app.logs.schemas import LogEntry, LogLevel
from app.logs.service import get_loki_client, get_websocket_factory
from app.organizations.models import Organization
from app.projects.models import Project
from app.quotas.models import Quota
from app.users.models import User
from app.utilities.database import get_session
from app.utilities.security import (
    BearerToken,
    auth_token_claimset,
    ensure_platform_administrator,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    get_user_organization,
    validate_and_get_project_from_query,
)
from app.workloads.enums import WorkloadType
from app.workloads.models import Workload as WorkloadModel
from app.workloads.schemas import (
    WorkloadComponent,
    Workloads,
    WorkloadsStats,
    WorkloadWithComponents,
)
from app.workloads.schemas import WorkloadResponse as WorkloadSchema

yml_content = """
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: sample-deployment
      labels:
        app: sample-app
    spec:
      replicas: 2
      selector:
        matchLabels:
          app: sample-app
      template:
        metadata:
          labels:
            app: sample-app
        spec:
          containers:
          - name: sample-container
            image: nginx:1.14.2
            ports:
            - containerPort: 80
    """


@pytest.mark.asyncio
@patch(
    "app.workloads.router.submit_workload_to_cluster",
    return_value=WorkloadSchema(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        status="Pending",
        type=WorkloadType.CUSTOM,
        display_name="SampleWorkload",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_submit_workload_success(mock_submit_workload):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    # Set up project
    project_id = "8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id=cluster_id,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        quota=Quota(
            id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
            cluster_id=cluster_id,
            project_id=project_id,
            status=QuotaStatus.PENDING,
            cpu_milli_cores=1000,
            memory_bytes=1024,
            ephemeral_storage_bytes=1024,
            gpu_count=1,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        cluster=Cluster(
            id=cluster_id,
            name="TestCluster",
            base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&display_name=SampleWorkload",
            files={"manifest": ("sample.yaml", yml_content, "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "cluster_id": "99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "project_id": "8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        "status": "Pending",
        "type": "CUSTOM",
        "display_name": "SampleWorkload",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }

    mock_submit_workload.assert_called_once()

    args, __ = mock_submit_workload.call_args
    assert args[5] == WorkloadType.CUSTOM  # workload_type
    assert args[6] == "SampleWorkload"


@patch(
    "app.workloads.router.submit_workload_to_cluster",
    return_value=WorkloadSchema(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        status="Pending",
        type=WorkloadType.FINE_TUNING,
        display_name="SampleWorkload",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_submit_workload_w_type(mock_submit_workload_to_cluster):
    project_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id=cluster_id,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        quota=Quota(
            id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
            cluster_id=cluster_id,
            project_id=project_id,
            status=QuotaStatus.PENDING,
            cpu_milli_cores=1000,
            memory_bytes=1024,
            ephemeral_storage_bytes=1024,
            gpu_count=1,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        cluster=Cluster(
            id=cluster_id,
            name="TestCluster",
            base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&display_name=SampleWorkload&workload_type=FINE_TUNING",
            files={"manifest": ("sample.yaml", yml_content, "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "cluster_id": "99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "project_id": "8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        "status": "Pending",
        "type": "FINE_TUNING",
        "display_name": "SampleWorkload",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }

    mock_submit_workload_to_cluster.assert_called_once()

    args, __ = mock_submit_workload_to_cluster.call_args
    assert args[5] == WorkloadType.FINE_TUNING  # workload_type
    assert args[6] == "SampleWorkload"


@patch(
    "app.workloads.router.submit_workload_to_cluster",
    return_value=WorkloadSchema(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        status="Pending",
        type=WorkloadType.CUSTOM,
        display_name="Sample FineTuning",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_submit_workload_display_name(mock_submit_workload_to_cluster):
    project_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id=cluster_id,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        quota=Quota(
            id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
            cluster_id=cluster_id,
            project_id=project_id,
            status=QuotaStatus.PENDING,
            cpu_milli_cores=1000,
            memory_bytes=1024,
            ephemeral_storage_bytes=1024,
            gpu_count=1,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        cluster=Cluster(
            id=cluster_id,
            name="TestCluster",
            base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&workload_type=CUSTOM&display_name=Sample%20FineTuning",
            files={"manifest": ("sample.yaml", yml_content, "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "cluster_id": "99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "project_id": "8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        "status": "Pending",
        "type": "CUSTOM",
        "display_name": "Sample FineTuning",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }

    mock_submit_workload_to_cluster.assert_called_once()

    args, __ = mock_submit_workload_to_cluster.call_args
    assert args[5] == WorkloadType.CUSTOM  # workload_type
    assert args[6] == "Sample FineTuning"  # display_name


@pytest.mark.asyncio
@patch(
    "app.workloads.router.submit_delete_workload",
    return_value=MagicMock(),
)
@patch(
    "app.workloads.router.get_workload_by_id_and_user_membership",
    return_value=WorkloadModel(
        id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="d330e767-f120-430e-854f-f28277f04de5",
        status=WorkloadStatus.RUNNING.value,
    ),
)
async def test_delete_workload_team_member(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    app.dependency_overrides[get_user] = lambda: mock_get_user()

    workload_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.delete(f"/v1/workloads/{workload_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@patch(
    "app.workloads.router.submit_delete_workload",
    return_value=MagicMock(),
)
@patch("app.workloads.router.is_user_in_role", return_value=True)
@patch(
    "app.workloads.router.get_workload_by_id_in_organization",
    return_value=WorkloadModel(
        id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="d330e767-f120-430e-854f-f28277f04de5",
        status=WorkloadStatus.RUNNING.value,
    ),
)
async def test_delete_workload_platform_admin(_, __, ___):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[get_user] = lambda: mock_get_user()

    workload_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.delete(f"/v1/workloads/{workload_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_by_id_and_user_membership", return_value=None)
async def test_delete_workload_not_found(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user] = lambda: mock_get_user()

    workload_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.delete(f"/v1/workloads/{workload_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        response.json()["detail"] == "Workload with ID 99a3f8c2-a23d-4ac6-b2a9-502305925ff3 not found or access denied"
    )


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_workload_with_components",
    return_value=WorkloadWithComponents(
        id=uuid.UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
        cluster_id=uuid.UUID("99a3f8c2-a23d-4ac6-b2a9-502305925ff3"),
        project_id=uuid.UUID("8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa"),
        type=WorkloadType.CUSTOM,
        display_name="SampleWorkload",
        status="Pending",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        components=[
            WorkloadComponent(
                id=uuid.UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
                name="sample-component",
                kind="Deployment",
                api_version="apps/v1",
                status="Running",
                status_reason="Its running!",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
            ),
            WorkloadComponent(
                id=uuid.UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
                name="sample-component-2",
                kind="Service",
                api_version="v1",
                status="Pending",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
            ),
        ],
    ),
)
@patch(
    "app.workloads.router.get_workload_by_id_and_user_membership",
    return_value=WorkloadModel(
        id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="d330e767-f120-430e-854f-f28277f04de5",
        status=WorkloadStatus.RUNNING.value,
    ),
)
async def test_get_workload_success(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user] = lambda: User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    workload_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "cluster_id": "99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        "components": [
            {
                "api_version": "apps/v1",
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "kind": "Deployment",
                "name": "sample-component",
                "status": "Running",
                "status_reason": "Its running!",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
            {
                "api_version": "v1",
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "kind": "Service",
                "name": "sample-component-2",
                "status": "Pending",
                "status_reason": None,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
        ],
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "project_id": "8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        "status": "Pending",
        "type": "CUSTOM",
        "display_name": "SampleWorkload",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_by_id_and_user_membership", return_value=None)
async def test_get_workload_not_found(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user] = lambda: User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    workload_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        response.json()["detail"] == "Workload with ID 99a3f8c2-a23d-4ac6-b2a9-502305925ff3 not found or access denied"
    )


@pytest.mark.asyncio
async def test_create_workload_project_not_found():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"
    mock_get_project = MagicMock()
    mock_get_project.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()

    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    project_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&display_name=Sample%20Workload",
            files={"manifest": ("sample.yaml", yml_content, "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_workload_file_too_large():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    project_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id=cluster_id,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        quota=Quota(
            id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
            cluster_id=cluster_id,
            project_id=project_id,
            status=QuotaStatus.PENDING,
            cpu_milli_cores=1000,
            memory_bytes=1024,
            ephemeral_storage_bytes=1024,
            gpu_count=1,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        cluster=Cluster(
            id=cluster_id,
            name="TestCluster",
            base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&display_name=Sample%20Workload",
            files={"manifest": ("sample.yaml", b"a" * (2 * 1024 * 1024 + 1), "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "File size too large. Max size is 2 MB."


@pytest.mark.asyncio
@patch("app.workloads.router.get_workloads_accessible_to_user")
async def test_get_workloads_no_project_success(get_workloads_accessible_to_user):
    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user] = lambda: User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_workload = WorkloadSchema(
        id=uuid4(),
        status="Pending",
        cluster_id=uuid4(),
        project_id=uuid4(),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    get_workloads_accessible_to_user.return_value = Workloads(workloads=[mock_workload])

    with TestClient(app) as client:
        response = client.get("/v1/workloads")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch("app.workloads.router.get_workloads_accessible_to_user", return_value=Workloads(workloads=[]))
async def test_get_workloads_no_project_empty_list(mock_get_workloads_accessible_to_user):
    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user] = lambda: User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        organization_id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_session] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/workloads")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"workloads": []}
    mock_get_workloads_accessible_to_user.assert_called_once()


@pytest.mark.asyncio
@patch("app.workloads.router.get_workloads_by_project")
@patch("app.utilities.security.validate_and_get_project_from_query")
async def test_get_workloads_with_project_success(validate_project, get_workloads_by_project):
    mock_claimset = {
        "sub": str(uuid.uuid4()),
        "email": "test@example.com",
        "preferred_username": "test-user",
        "realm_access": {"roles": ["team_member"]},
        "organization": [{"test-org": {"id": str(uuid4())}}, "test-org"],
        "groups": ["/test-project"],
    }
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [test_project]
    app.dependency_overrides[get_session] = lambda: MagicMock()

    # Mock validate_and_get_project_from_query to return a project
    project_id = UUID("99a3f8c2-a23d-4ac6-b2a9-502305925ff3")
    test_project = Project(id=project_id, name="test-project")
    validate_project.return_value = test_project

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization 1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    mock_workload = WorkloadSchema(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        status="Pending",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id=uuid4(),
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    get_workloads_by_project.return_value = Workloads(workloads=[mock_workload])

    with TestClient(app) as client:
        response = client.get("/v1/workloads?project_id=99a3f8c2-a23d-4ac6-b2a9-502305925ff3")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch(
    "app.workloads.router.validate_and_get_project_from_query",
    side_effect=HTTPException(status_code=status.HTTP_403_FORBIDDEN),
)
async def test_get_workloads_with_project_not_accessible(_):
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[auth_token_claimset] = lambda: {"email": "test@example.com"}

    with TestClient(app) as client:
        response = client.get("/v1/workloads?project_id=99a3f8c2-a23d-4ac6-b2a9-502305925ff3")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_stats_for_workloads_in_organization",
    return_value=WorkloadsStats(running_workloads_count=10, pending_workloads_count=5),
)
async def test_get_workload_stats_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization 1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    with TestClient(app) as client:
        response = client.get("/v1/workloads/stats")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"running_workloads_count": 10, "pending_workloads_count": 5}


@pytest.mark.asyncio
async def test_get_workload_stats_not_in_role():
    app.dependency_overrides[get_session] = lambda: MagicMock()
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="Organization 1",
        keycloak_organization_id="123",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

    with TestClient(app) as client:
        response = client.get("/v1/workloads/stats")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_workload_stats_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/workloads/stats")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.get_workload_logs")
async def test_get_workload_logs_success(mock_get_logs, mock_get_workload, mock_get_workload_with_components):
    """Test successful workload logs retrieval endpoint."""
    # Setup mocks
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id, status="Running")
    mock_get_workload.return_value = mock_workload

    # Mock workload with components
    mock_component = MagicMock()
    mock_component.kind.value = "Deployment"
    mock_component.name = "test-deployment"

    mock_workload_with_components = MagicMock()
    mock_workload_with_components.id = workload_id
    mock_workload_with_components.components = [mock_component]
    mock_get_workload_with_components.return_value = mock_workload_with_components

    # Create mock flat list of LogEntry objects
    mock_get_logs.return_value = [
        LogEntry(
            timestamp="2025-01-01T00:00:00Z",
            level="info",
            message="Test log message 1",
        ),
        LogEntry(
            timestamp="2025-01-01T00:01:00Z",
            level=LogLevel.debug,
            message="Test log message 2",
        ),
    ]

    # Setup app dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_user] = lambda: MagicMock(id=uuid4(), email="test@example.com")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/workloads/{workload_id}/logs?start_date=2025-01-01T00:00:00Z&end_date=2025-01-02T00:00:00Z&limit=100"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["message"] == "Test log message 1"

    # Verify service calls
    mock_get_workload.assert_called_once()
    mock_get_workload_with_components.assert_called_once()
    # Verify logs service called with workload object, not workload_id
    mock_get_logs.assert_called_once()
    call_args = mock_get_logs.call_args
    assert call_args[1]["workload"] == mock_workload_with_components
    assert "loki_client" in call_args[1]
    assert call_args[1]["limit"] == 100


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
async def test_get_workload_logs_not_found(mock_get_workload):
    """Test workload logs retrieval for non-existent workload."""
    workload_id = uuid4()
    mock_get_workload.return_value = None  # Workload not found

    # Setup app dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_user] = lambda: MagicMock(id=uuid4(), email="test@example.com")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/workloads/{workload_id}/logs?start_date=2025-01-01T00:00:00Z&end_date=2025-01-02T00:00:00Z&limit=100"
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify workload access check was called
    mock_get_workload.assert_called_once()


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.get_workload_logs")
async def test_get_workload_logs_with_level_filter(mock_get_logs, mock_get_workload, mock_get_workload_with_components):
    """Test workload logs retrieval with level filter."""
    # Setup mocks
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id, status="Running")
    mock_get_workload.return_value = mock_workload

    # Mock workload with components
    mock_component = MagicMock()
    mock_component.kind.value = "Deployment"
    mock_component.name = "test-deployment"

    mock_workload_with_components = MagicMock()
    mock_workload_with_components.id = workload_id
    mock_workload_with_components.components = [mock_component]
    mock_get_workload_with_components.return_value = mock_workload_with_components

    # Create mock filtered logs (only warning and above)
    mock_get_logs.return_value = [
        LogEntry(
            timestamp="2025-01-01T00:00:00Z",
            level=LogLevel.warning,
            message="Warning message",
        ),
        LogEntry(
            timestamp="2025-01-01T00:01:00Z",
            level=LogLevel.error,
            message="Error message",
        ),
    ]

    # Setup app dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_user] = lambda: MagicMock(id=uuid4(), email="test@example.com")

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}/logs?level=warning&limit=100")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    # Verify levels are serialized as strings
    assert data[0]["level"] == "warning"
    assert data[1]["level"] == "error"
    assert data[0]["message"] == "Warning message"
    assert data[1]["message"] == "Error message"

    # Verify service was called with level filter
    mock_get_logs.assert_called_once()
    call_args = mock_get_logs.call_args
    assert call_args[1]["level_filter"] == LogLevel.warning


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.get_workload_logs")
async def test_get_workload_logs_with_warning_synonym(
    mock_get_logs, mock_get_workload, mock_get_workload_with_components
):
    """Test workload logs retrieval with 'warning' synonym for 'warn'."""
    # Setup mocks
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id, status="Running")
    mock_get_workload.return_value = mock_workload

    # Mock workload with components
    mock_component = MagicMock()
    mock_component.kind.value = "Deployment"
    mock_component.name = "test-deployment"

    mock_workload_with_components = MagicMock()
    mock_workload_with_components.id = workload_id
    mock_workload_with_components.components = [mock_component]
    mock_get_workload_with_components.return_value = mock_workload_with_components

    # Create mock filtered logs
    mock_get_logs.return_value = [
        LogEntry(
            timestamp="2025-01-01T00:00:00Z",
            level=LogLevel.warning,
            message="Warning message",
        ),
    ]

    # Setup app dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_user] = lambda: MagicMock(id=uuid4(), email="test@example.com")

    with TestClient(app) as client:
        # Test with 'warning' synonym
        response = client.get(f"/v1/workloads/{workload_id}/logs?level=warning&limit=100")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["level"] == "warning"  # Should be serialized as enum name

    # Verify service was called with LogLevel.warning (converted from 'warning')
    mock_get_logs.assert_called_once()
    call_args = mock_get_logs.call_args
    assert call_args[1]["level_filter"] == LogLevel.warning


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.get_workload_logs")
async def test_get_workload_logs_custom_parameters(mock_get_logs, mock_get_workload, mock_get_workload_with_components):
    """Test workload logs retrieval with custom parameters."""
    # Setup mocks
    workload_id = uuid4()
    mock_workload = MagicMock(id=workload_id, status="Running")
    mock_get_workload.return_value = mock_workload

    # Mock workload with components
    mock_component = MagicMock()
    mock_component.kind.value = "Deployment"
    mock_component.name = "test-deployment-2"

    mock_workload_with_components = MagicMock()
    mock_workload_with_components.id = workload_id
    mock_workload_with_components.components = [mock_component]
    mock_get_workload_with_components.return_value = mock_workload_with_components

    # Create mock flat list
    mock_get_logs.return_value = [
        LogEntry(
            timestamp="2025-01-01T00:00:00Z",
            level="info",
            message="Test log message",
        ),
    ]

    # Setup app dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_user] = lambda: MagicMock(id=uuid4(), email="test@example.com")

    with TestClient(app) as client:
        response = client.get(
            f"/v1/workloads/{workload_id}/logs?start_date=2025-01-01T00:00:00Z&end_date=2025-01-01T12:00:00Z&limit=500"
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["message"] == "Test log message"

    # Verify service calls
    mock_get_workload.assert_called_once()
    mock_get_workload_with_components.assert_called_once()
    # Verify logs service called with workload object and custom parameters
    mock_get_logs.assert_called_once()
    call_args = mock_get_logs.call_args
    assert call_args[1]["workload"] == mock_workload_with_components
    assert "loki_client" in call_args[1]
    assert call_args[1]["limit"] == 500


# Streaming endpoint tests
@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.stream_workload_logs")
async def test_workload_logs_stream_success(mock_stream_logs, mock_get_workload, mock_get_workload_with_components):
    """Test successful workload logs streaming endpoint."""

    # Setup mocks
    workload_id = uuid4()
    mock_user = User(
        id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_workload = MagicMock(id=workload_id, status="Running")
    mock_get_workload.return_value = mock_workload

    # Mock workload with components
    mock_component = MagicMock()
    mock_component.kind.value = "Deployment"
    mock_component.name = "test-deployment"

    mock_workload_with_components = MagicMock()
    mock_workload_with_components.id = workload_id
    mock_workload_with_components.components = [mock_component]
    mock_get_workload_with_components.return_value = mock_workload_with_components

    # Mock async generator for streaming logs
    async def mock_log_generator():
        yield LogEntry(timestamp="2025-01-01T12:00:00Z", level=LogLevel.info, message="Stream log 1")
        yield LogEntry(timestamp="2025-01-01T12:00:01Z", level=LogLevel.error, message="Stream log 2")

    mock_stream_logs.return_value = mock_log_generator()

    # Create mock dependencies with consistent instances
    mock_session = AsyncMock()
    mock_loki_client = AsyncMock()
    mock_websocket_factory = AsyncMock()

    # Create mock project for accessible_projects
    mock_project = Project(id=uuid4(), name="test-project", organization_id=mock_user.organization_id)

    # Override dependencies
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [mock_project]
    app.dependency_overrides[get_loki_client] = lambda: mock_loki_client
    app.dependency_overrides[get_websocket_factory] = lambda: mock_websocket_factory

    try:
        client = TestClient(app)
        response = client.get(
            f"/v1/workloads/{workload_id}/logs/stream?start_time=2025-01-01T00:00:00Z&level=info&delay=2"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "no-cache"

        # Check that the response contains streamed data
        content = response.text
        assert "Stream log 1" in content
        assert "Stream log 2" in content
        assert "data:" in content  # SSE format

        # Verify service calls - use the actual mock instances
        mock_get_workload.assert_called_once_with(mock_session, workload_id, [mock_project])
        mock_get_workload_with_components.assert_called_once_with(mock_session, mock_workload)
        mock_stream_logs.assert_called_once()

        # Verify streaming parameters
        call_args = mock_stream_logs.call_args
        assert call_args[1]["workload"] == mock_workload_with_components
        assert call_args[1]["level_filter"] == LogLevel.info
        assert call_args[1]["delay_seconds"] == 2

    finally:
        app.dependency_overrides.clear()


@patch("app.workloads.router.get_workload_by_id_and_user_membership")
async def test_workload_logs_stream_not_found(mock_get_workload):
    """Test workload logs streaming for non-existent workload."""

    workload_id = uuid4()
    mock_user = User(
        id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    mock_get_workload.return_value = None  # Workload not found

    # Create mock project for accessible_projects
    mock_project = Project(id=uuid4(), name="test-project", organization_id=mock_user.organization_id)

    # Override dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [mock_project]
    app.dependency_overrides[get_loki_client] = lambda: AsyncMock()
    app.dependency_overrides[get_websocket_factory] = lambda: AsyncMock()

    try:
        client = TestClient(app)
        response = client.get(f"/v1/workloads/{workload_id}/logs/stream")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    finally:
        app.dependency_overrides.clear()


@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.stream_workload_logs")
async def test_workload_logs_stream_with_default_parameters(
    mock_stream_logs, mock_get_workload, mock_get_workload_with_components
):
    """Test workload logs streaming with default parameters."""

    workload_id = uuid4()
    mock_user = User(
        id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_workload = MagicMock(id=workload_id, status="Running")
    mock_get_workload.return_value = mock_workload

    mock_component = MagicMock()
    mock_component.kind.value = "Deployment"
    mock_component.name = "test-deployment"

    mock_workload_with_components = MagicMock()
    mock_workload_with_components.id = workload_id
    mock_workload_with_components.components = [mock_component]
    mock_get_workload_with_components.return_value = mock_workload_with_components

    # Mock empty stream
    async def mock_empty_generator():
        return
        yield  # This will never execute but makes it a generator

    mock_stream_logs.return_value = mock_empty_generator()

    # Create mock project for accessible_projects
    mock_project = Project(id=uuid4(), name="test-project", organization_id=mock_user.organization_id)

    # Override dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [mock_project]
    app.dependency_overrides[get_loki_client] = lambda: AsyncMock()
    app.dependency_overrides[get_websocket_factory] = lambda: AsyncMock()

    try:
        client = TestClient(app)
        response = client.get(f"/v1/workloads/{workload_id}/logs/stream")

        assert response.status_code == status.HTTP_200_OK

        # Verify default parameters were used
        call_args = mock_stream_logs.call_args
        assert call_args[1]["start_time"] is None  # Default
        assert call_args[1]["level_filter"] is None  # Default
        assert call_args[1]["delay_seconds"] == 1  # Default

    finally:
        app.dependency_overrides.clear()


@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.stream_workload_logs")
async def test_workload_logs_stream_invalid_delay(
    mock_stream_logs, mock_get_workload, mock_get_workload_with_components
):
    """Test workload logs streaming with invalid delay parameter."""

    workload_id = uuid4()
    mock_user = User(
        id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create mock project for accessible_projects
    mock_project = Project(id=uuid4(), name="test-project", organization_id=mock_user.organization_id)

    # Override dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [mock_project]
    app.dependency_overrides[get_loki_client] = lambda: AsyncMock()
    app.dependency_overrides[get_websocket_factory] = lambda: AsyncMock()

    try:
        client = TestClient(app)

        # Test delay too small
        response = client.get(f"/v1/workloads/{workload_id}/logs/stream?delay=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test delay too large
        response = client.get(f"/v1/workloads/{workload_id}/logs/stream?delay=100")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    finally:
        app.dependency_overrides.clear()


@patch("app.workloads.router.get_workload_with_components")
@patch("app.workloads.router.get_workload_by_id_and_user_membership")
@patch("app.workloads.router.stream_workload_logs")
async def test_workload_logs_stream_exception_handling(
    mock_stream_logs, mock_get_workload, mock_get_workload_with_components
):
    """Test workload logs streaming exception handling."""

    workload_id = uuid4()
    mock_user = User(
        id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_workload = MagicMock(id=workload_id, status="Running")
    mock_get_workload.return_value = mock_workload

    mock_component = MagicMock()
    mock_component.kind.value = "Deployment"
    mock_component.name = "test-deployment"

    mock_workload_with_components = MagicMock()
    mock_workload_with_components.id = workload_id
    mock_workload_with_components.components = [mock_component]
    mock_get_workload_with_components.return_value = mock_workload_with_components

    # Mock stream that raises an exception
    async def mock_error_generator():
        yield LogEntry(timestamp="2025-01-01T12:00:00Z", level=LogLevel.info, message="Before error")
        raise Exception("Streaming error")

    mock_stream_logs.return_value = mock_error_generator()

    # Create mock project for accessible_projects
    mock_project = Project(id=uuid4(), name="test-project", organization_id=mock_user.organization_id)

    # Override dependencies
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [mock_project]
    app.dependency_overrides[get_loki_client] = lambda: AsyncMock()
    app.dependency_overrides[get_websocket_factory] = lambda: AsyncMock()

    try:
        client = TestClient(app)
        response = client.get(f"/v1/workloads/{workload_id}/logs/stream")

        # Response should still be 200 as streaming started successfully
        assert response.status_code == status.HTTP_200_OK

        # Should contain both log entry and error
        content = response.text
        assert "Before error" in content
        assert "error" in content.lower()

    finally:
        app.dependency_overrides.clear()
