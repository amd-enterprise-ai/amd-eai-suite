# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for Workspaces router endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from api_common.exceptions import ConflictException, NotFoundException
from app import app  # type: ignore[attr-defined]
from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.schemas import WorkloadResponse
from app.workspaces.enums import WorkspaceType
from tests.dependency_overrides import SESSION_OVERRIDES, override_dependencies


def make_workload_response(
    workspace_type: WorkspaceType = WorkspaceType.VSCODE,
    display_name: str | None = None,
) -> WorkloadResponse:
    """Create a WorkloadResponse for testing."""
    now = datetime.now(UTC)
    return WorkloadResponse(
        id=uuid4(),
        name=f"wb-{workspace_type.value}-test",
        display_name=display_name or f"Test {workspace_type.value.title()} Workspace",
        type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.PENDING,
        namespace="test-namespace",
        chart_id=None,
        manifest="",
        chart_name=None,
        created_at=now,
        updated_at=now,
        created_by="test@example.com",
        updated_by="test@example.com",
    )


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_vscode(mock_create: MagicMock) -> None:
    """Test POST /v1/projects/{project}/workspaces with vscode type returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.VSCODE)
    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/test-namespace/workspaces",
            json={
                "workspaceType": "vscode",
                "image": "test-image",
                "gpus": 1,
                "memoryPerGpu": 128,
                "cpuPerGpu": 4,
            },
        )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["type"] == WorkloadType.WORKSPACE.value


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_jupyterlab(mock_create: MagicMock) -> None:
    """Test POST /v1/projects/{project}/workspaces with jupyterlab type returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.JUPYTERLAB)
    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/test-namespace/workspaces",
            json={
                "workspaceType": "jupyterlab",
                "image": "test-image",
                "gpus": 1,
                "memoryPerGpu": 128,
                "cpuPerGpu": 4,
            },
        )
    assert response.status_code == status.HTTP_201_CREATED


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_mlflow(mock_create: MagicMock) -> None:
    """Test POST /v1/projects/{project}/workspaces with mlflow type returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.MLFLOW)
    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/test-namespace/workspaces",
            json={
                "workspaceType": "mlflow",
                "image": "test-image",
                "gpus": 1,
                "memoryPerGpu": 128,
                "cpuPerGpu": 4,
            },
        )
    assert response.status_code == status.HTTP_201_CREATED


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_conflict(mock_create: MagicMock) -> None:
    """Test workspace creation fails with 409 when service raises ConflictException."""
    mock_create.side_effect = ConflictException(
        message="MLflow workspace already running in this namespace",
        detail="Only one MLflow workspace is allowed per namespace at a time.",
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/test-namespace/workspaces",
            json={
                "workspaceType": "mlflow",
                "image": "test-image",
                "gpus": 1,
                "memoryPerGpu": 32,
                "cpuPerGpu": 4,
            },
        )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "MLflow workspace already running" in response.json()["detail"]


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_with_display_name(mock_create: MagicMock) -> None:
    """Test workspace creation with custom display name."""
    mock_create.return_value = make_workload_response(WorkspaceType.VSCODE, display_name="My Custom Workspace")
    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/test-namespace/workspaces?displayName=My%20Custom%20Workspace",
            json={"workspaceType": "vscode", "gpus": 1, "memoryPerGpu": 64, "cpuPerGpu": 2},
        )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["displayName"] == "My Custom Workspace"
    # Verify display_name was passed to service
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["display_name"] == "My Custom Workspace"


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_minimal_request(mock_create: MagicMock) -> None:
    """Test workspace creation with minimal request (using defaults)."""
    mock_create.return_value = make_workload_response(WorkspaceType.JUPYTERLAB)
    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/test-namespace/workspaces",
            json={"workspaceType": "jupyterlab"},
        )
    assert response.status_code == status.HTTP_201_CREATED
    mock_create.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_comfyui(mock_create: MagicMock) -> None:
    """Test POST /v1/projects/{project}/workspaces with comfyui type returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.COMFYUI)
    with TestClient(app) as client:
        response = client.post(
            "/v1/projects/test-namespace/workspaces",
            json={
                "workspaceType": "comfyui",
                "image": "test-image",
                "gpus": 2,
                "memoryPerGpu": 64,
                "cpuPerGpu": 8,
            },
        )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["type"] == WorkloadType.WORKSPACE.value


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.delete_development_workspace", autospec=True)
def test_delete_workspace_success(mock_delete: AsyncMock) -> None:
    """Test DELETE /v1/projects/{project}/workspaces/{id} returns 204 on success."""
    workload_id = uuid4()
    mock_delete.return_value = None

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/test-namespace/workspaces/{workload_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    mock_delete.assert_called_once()
    call_kwargs = mock_delete.call_args.kwargs
    assert call_kwargs["namespace"] == "test-namespace"
    assert call_kwargs["workload_id"] == workload_id


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.delete_development_workspace", autospec=True)
def test_delete_workspace_not_found(mock_delete: AsyncMock) -> None:
    """Test DELETE returns 404 when the workspace is missing (covers both 'unknown id'
    and 'id refers to a non-workspace workload' — the service-layer type guard."""
    workload_id = uuid4()
    mock_delete.side_effect = NotFoundException(f"Workspace {workload_id} not found")

    with TestClient(app) as client:
        response = client.delete(f"/v1/projects/test-namespace/workspaces/{workload_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
