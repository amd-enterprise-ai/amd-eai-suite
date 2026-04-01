# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app import app  # type: ignore
from app.clusters.models import Cluster
from app.messaging.schemas import QuotaStatus, WorkloadStatus
from app.metrics.schemas import (
    Datapoint,
    DeviceMetricTimeseries,
    GpuDeviceSingleMetricResponse,
    GpuDeviceWithSingleMetric,
    MetricsTimeRange,
)
from app.projects.models import Project
from app.quotas.models import Quota
from app.users.models import User
from app.utilities.database import get_session
from app.utilities.security import (
    BearerToken,
    auth_token_claimset,
    ensure_user_can_view_workload,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    validate_and_get_project_from_query,
)
from app.workloads.enums import WorkloadType
from app.workloads.models import Workload as WorkloadModel
from app.workloads.schemas import (
    WorkloadComponent,
    WorkloadMetricsDetailsResponse,
    Workloads,
    WorkloadsStats,
    WorkloadWithComponents,
)
from app.workloads.schemas import WorkloadResponse as WorkloadSchema


async def _noop_ensure_user_can_view_workload() -> None:
    pass


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
async def test_submit_workload_success(mock_submit_workload: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()
    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    # Set up project
    project_id = "8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
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
            workloads_base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&display_name=SampleWorkload",
            files={"manifest": ("sample.yaml", yml_content, "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_200_OK
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
async def test_submit_workload_w_type(mock_submit_workload_to_cluster: MagicMock) -> None:
    project_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
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
            workloads_base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&display_name=SampleWorkload&workload_type=FINE_TUNING",
            files={"manifest": ("sample.yaml", yml_content, "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_200_OK
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
async def test_submit_workload_display_name(mock_submit_workload_to_cluster: MagicMock) -> None:
    project_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
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
            workloads_base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )
    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_get_project()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/workloads?project_id={project_id}&workload_type=CUSTOM&display_name=Sample%20FineTuning",
            files={"manifest": ("sample.yaml", yml_content, "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_200_OK
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
@patch("app.workloads.router.submit_delete_workload", return_value=MagicMock())
@patch(
    "app.workloads.router.get_workload_by_id_and_user_membership",
    return_value=WorkloadModel(
        id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="d330e767-f120-430e-854f-f28277f04de5",
        status=WorkloadStatus.RUNNING.value,
    ),
)
async def test_delete_workload_team_member(_: MagicMock, __: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
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
@patch("app.workloads.router.submit_delete_workload", return_value=MagicMock())
@patch("app.workloads.router.is_user_in_role", return_value=True)
@patch(
    "app.workloads.router.get_workload_by_id",
    return_value=WorkloadModel(
        id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="d330e767-f120-430e-854f-f28277f04de5",
        status=WorkloadStatus.RUNNING.value,
    ),
)
async def test_delete_workload_platform_admin(_: MagicMock, __: MagicMock, ___: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
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
async def test_delete_workload_not_found(_: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
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
    "app.workloads.router.get_workload_by_id",
    return_value=WorkloadModel(
        id="2aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="d330e767-f120-430e-854f-f28277f04de5",
        status=WorkloadStatus.RUNNING.value,
    ),
)
async def test_get_workload_success(_: MagicMock, __: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = lambda: None

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
@patch("app.workloads.router.get_workload_by_id", return_value=None)
async def test_get_workload_not_found(_: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = lambda: None
    workload_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        response.json()["detail"] == "Workload with ID 99a3f8c2-a23d-4ac6-b2a9-502305925ff3 not found or access denied"
    )


@pytest.mark.asyncio
async def test_create_workload_project_not_found() -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"
    mock_get_project = MagicMock()
    mock_get_project.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
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
async def test_create_workload_file_too_large() -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[BearerToken] = lambda: MagicMock()

    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"

    project_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    cluster_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"
    mock_get_project = MagicMock()
    mock_get_project.return_value = Project(
        id=project_id,
        name="project1",
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
            workloads_base_url="http://test-cluster.example.com",
            last_heartbeat_at=datetime.now(UTC),
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    )
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
async def test_get_workloads_no_project_success(get_workloads_accessible_to_user: MagicMock) -> None:
    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user] = lambda: User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
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
    get_workloads_accessible_to_user.return_value = Workloads(data=[mock_workload])

    with TestClient(app) as client:
        response = client.get("/v1/workloads")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch("app.workloads.router.get_workloads_accessible_to_user", return_value=Workloads(data=[]))
async def test_get_workloads_no_project_empty_list(mock_get_workloads_accessible_to_user: MagicMock) -> None:
    mock_get_user = MagicMock()
    mock_get_user.return_value = "test_user"
    app.dependency_overrides[get_user] = lambda: User(
        id="c5f8b631-f5a8-407a-b773-8c2e5792b325",
        email="user@email.com",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    app.dependency_overrides[get_session] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/workloads")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"data": []}
    mock_get_workloads_accessible_to_user.assert_called_once()


@pytest.mark.asyncio
@patch("app.workloads.router.get_workloads_by_project")
@patch("app.utilities.security.validate_and_get_project_from_query")
async def test_get_workloads_with_project_success(
    validate_project: MagicMock, get_workloads_by_project: MagicMock
) -> None:
    # Mock validate_and_get_project_from_query to return a project
    project_id = UUID("99a3f8c2-a23d-4ac6-b2a9-502305925ff3")
    test_project = Project(id=project_id, name="test-project")

    mock_claimset: dict = {
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
    validate_project.return_value = test_project

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
    get_workloads_by_project.return_value = Workloads(data=[mock_workload])

    with TestClient(app) as client:
        response = client.get("/v1/workloads?project_id=99a3f8c2-a23d-4ac6-b2a9-502305925ff3")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@patch(
    "app.workloads.router.validate_and_get_project_from_query",
    side_effect=HTTPException(status_code=status.HTTP_403_FORBIDDEN),
)
async def test_get_workloads_with_project_not_accessible(_: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[auth_token_claimset] = lambda: {"email": "test@example.com"}

    with TestClient(app) as client:
        response = client.get("/v1/workloads?project_id=99a3f8c2-a23d-4ac6-b2a9-502305925ff3")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_stats_for_workloads",
    return_value=WorkloadsStats(running_workloads_count=10, pending_workloads_count=5),
)
@patch("app.workloads.router.is_user_in_role", return_value=True)
async def test_get_workload_stats_admin_success(_: MagicMock, __: MagicMock) -> None:
    """Test workload stats endpoint for platform administrator."""
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/workloads/stats")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"running_workloads_count": 10, "pending_workloads_count": 5}


@pytest.mark.asyncio
@patch("app.workloads.router.get_accessible_clusters")
@patch("app.workloads.router.get_projects_accessible_to_user")
@patch(
    "app.workloads.router.get_stats_for_workloads_in_accessible_clusters",
    return_value=WorkloadsStats(running_workloads_count=3, pending_workloads_count=2),
)
@patch("app.workloads.router.is_user_in_role", return_value=False)
async def test_get_workload_stats_non_admin_success(
    _: MagicMock,
    __: MagicMock,
    ___: MagicMock,
    ____: MagicMock,
) -> None:
    """Test workload stats endpoint for non-admin user with accessible clusters."""
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/workloads/stats")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"running_workloads_count": 3, "pending_workloads_count": 2}


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_workload_by_id",
    return_value=WorkloadModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        status=WorkloadStatus.RUNNING.value,
    ),
)
@patch(
    "app.workloads.router.get_workload_details_from_service",
    return_value=WorkloadMetricsDetailsResponse(
        name="Test Workload",
        workload_id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
        created_by="test@example.com",
        cluster_name="TestCluster",
        cluster_id=UUID("99a3f8c2-a23d-4ac6-b2a9-502305925ff3"),
        nodes_in_use=1,
        gpu_devices_in_use=2,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        queue_time=3615,
        running_time=468045,
    ),
)
async def test_get_workload_details_success(_: MagicMock, __: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = _noop_ensure_user_can_view_workload

    workload_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}/metrics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Workload"
    assert data["workload_id"] == workload_id
    assert data["cluster_name"] == "TestCluster"
    assert data["nodes_in_use"] == 1
    assert data["gpu_devices_in_use"] == 2
    assert data["queue_time"] == 3615
    assert data["running_time"] == 468045


@pytest.mark.asyncio
@patch("app.workloads.router.get_workload_by_id", return_value=None)
async def test_get_workload_details_not_found(_: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = _noop_ensure_user_can_view_workload

    workload_id = "99a3f8c2-a23d-4ac6-b2a9-502305925ff3"

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}/metrics")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_workload_details_from_service",
    return_value=WorkloadMetricsDetailsResponse(
        name="Admin Workload",
        workload_id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
        created_by="admin@example.com",
        cluster_name="AdminCluster",
        cluster_id=UUID("99a3f8c2-a23d-4ac6-b2a9-502305925ff3"),
        nodes_in_use=3,
        gpu_devices_in_use=8,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        queue_time=0,
        running_time=1000,
    ),
)
@patch("app.workloads.router.is_user_in_role", return_value=True)
@patch(
    "app.workloads.router.get_workload_by_id",
    return_value=WorkloadModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        cluster_id="99a3f8c2-a23d-4ac6-b2a9-502305925ff3",
        project_id="8afa9fb8-2e96-4b23-b4fd-7f9cc58fb9aa",
        status=WorkloadStatus.RUNNING.value,
    ),
)
async def test_get_workload_details_admin(_: MagicMock, __: MagicMock, ___: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = _noop_ensure_user_can_view_workload

    workload_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}/metrics")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["gpu_devices_in_use"] == 8


# --- Tests for individual GPU device metric endpoints ---


def _single_metric_response(series_label: str, value: float) -> GpuDeviceSingleMetricResponse:
    start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC)
    return GpuDeviceSingleMetricResponse.model_construct(
        gpu_devices=[
            GpuDeviceWithSingleMetric(
                gpu_uuid="gpu-aaa",
                gpu_id="0",
                hostname="node-1",
                metric=DeviceMetricTimeseries(
                    series_label=series_label,
                    values=[Datapoint(timestamp=start, value=value)],
                ),
            ),
        ],
        range=MetricsTimeRange.model_construct(start=start, end=end),
    )


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_gpu_device_vram_utilization_for_workload",
    new_callable=AsyncMock,
    return_value=_single_metric_response("vram_utilization_pct", 65.0),
)
async def test_get_gpu_device_vram_utilization_success(_: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = _noop_ensure_user_can_view_workload
    workload_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    now = datetime.now(UTC)
    start = (now - timedelta(hours=2)).replace(microsecond=0)
    end = (now - timedelta(hours=1)).replace(microsecond=0)

    with TestClient(app) as client:
        response = client.get(
            f"/v1/workloads/{workload_id}/metrics/gpu-devices/vram-utilization",
            params={"start": start.isoformat(), "end": end.isoformat()},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["gpu_devices"]) == 1
    assert data["gpu_devices"][0]["gpu_uuid"] == "gpu-aaa"
    assert data["gpu_devices"][0]["metric"]["series_label"] == "vram_utilization_pct"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 65.0


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_gpu_device_junction_temperature_for_workload",
    new_callable=AsyncMock,
    return_value=_single_metric_response("junction_temperature_celsius", 30.0),
)
async def test_get_gpu_device_junction_temperature_success(_: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = _noop_ensure_user_can_view_workload
    workload_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    now = datetime.now(UTC)
    start = (now - timedelta(hours=2)).replace(microsecond=0)
    end = (now - timedelta(hours=1)).replace(microsecond=0)

    with TestClient(app) as client:
        response = client.get(
            f"/v1/workloads/{workload_id}/metrics/gpu-devices/junction-temperature",
            params={"start": start.isoformat(), "end": end.isoformat()},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["gpu_devices"][0]["metric"]["series_label"] == "junction_temperature_celsius"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 30.0


@pytest.mark.asyncio
@patch(
    "app.workloads.router.get_gpu_device_power_usage_for_workload",
    new_callable=AsyncMock,
    return_value=_single_metric_response("power_watts", 57.0),
)
async def test_get_gpu_device_power_usage_success(_: MagicMock) -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = _noop_ensure_user_can_view_workload
    workload_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"
    now = datetime.now(UTC)
    start = (now - timedelta(hours=2)).replace(microsecond=0)
    end = (now - timedelta(hours=1)).replace(microsecond=0)

    with TestClient(app) as client:
        response = client.get(
            f"/v1/workloads/{workload_id}/metrics/gpu-devices/power-usage",
            params={"start": start.isoformat(), "end": end.isoformat()},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["gpu_devices"][0]["metric"]["series_label"] == "power_watts"
    assert data["gpu_devices"][0]["metric"]["values"][0]["value"] == 57.0


@pytest.mark.asyncio
async def test_get_gpu_device_vram_utilization_missing_params() -> None:
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[auth_token_claimset] = lambda: MagicMock()
    app.dependency_overrides[ensure_user_can_view_workload] = _noop_ensure_user_can_view_workload
    workload_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    with TestClient(app) as client:
        response = client.get(f"/v1/workloads/{workload_id}/metrics/gpu-devices/vram-utilization")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
