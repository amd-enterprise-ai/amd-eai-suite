# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for Workspaces router endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from api_common.exceptions import ConflictException
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
    """Test POST /v1/namespaces/{ns}/workspaces/vscode returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.VSCODE)
    with TestClient(app) as client:
        response = client.post(
            "/v1/namespaces/test-namespace/workspaces/vscode",
            json={"image": "test-image", "gpus": 1, "memory_per_gpu": 128, "cpu_per_gpu": 4},
        )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["type"] == WorkloadType.WORKSPACE.value


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_jupyterlab(mock_create: MagicMock) -> None:
    """Test POST /v1/namespaces/{ns}/workspaces/jupyterlab returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.JUPYTERLAB)
    with TestClient(app) as client:
        response = client.post(
            "/v1/namespaces/test-namespace/workspaces/jupyterlab",
            json={"image": "test-image", "gpus": 1, "memory_per_gpu": 128, "cpu_per_gpu": 4},
        )
    assert response.status_code == status.HTTP_201_CREATED


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_mlflow(mock_create: MagicMock) -> None:
    """Test POST /v1/namespaces/{ns}/workspaces/mlflow returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.MLFLOW)
    with TestClient(app) as client:
        response = client.post(
            "/v1/namespaces/test-namespace/workspaces/mlflow",
            json={"image": "test-image", "gpus": 1, "memory_per_gpu": 128, "cpu_per_gpu": 4},
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
            "/v1/namespaces/test-namespace/workspaces/mlflow",
            json={"image": "test-image", "gpus": 1, "memory_per_gpu": 32, "cpu_per_gpu": 4},
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
            "/v1/namespaces/test-namespace/workspaces/vscode?display_name=My%20Custom%20Workspace",
            json={"gpus": 1, "memory_per_gpu": 64, "cpu_per_gpu": 2},
        )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["display_name"] == "My Custom Workspace"
    # Verify display_name was passed to service
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["display_name"] == "My Custom Workspace"


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_minimal_request(mock_create: MagicMock) -> None:
    """Test workspace creation with minimal request (using defaults)."""
    mock_create.return_value = make_workload_response(WorkspaceType.JUPYTERLAB)
    with TestClient(app) as client:
        response = client.post("/v1/namespaces/test-namespace/workspaces/jupyterlab", json={})
    assert response.status_code == status.HTTP_201_CREATED
    mock_create.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.workspaces.router.create_development_workspace", autospec=True)
def test_create_workspace_comfyui(mock_create: MagicMock) -> None:
    """Test POST /v1/namespaces/{ns}/workspaces/comfyui returns 201."""
    mock_create.return_value = make_workload_response(WorkspaceType.COMFYUI)
    with TestClient(app) as client:
        response = client.post(
            "/v1/namespaces/test-namespace/workspaces/comfyui",
            json={"image": "test-image", "gpus": 2, "memory_per_gpu": 64, "cpu_per_gpu": 8},
        )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["type"] == WorkloadType.WORKSPACE.value
