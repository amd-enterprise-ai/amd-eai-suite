# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.managed_workloads.schemas import ChartWorkloadResponse
from app.utilities.database import get_session
from app.utilities.exceptions import ConflictException, NotReadyException
from app.utilities.security import (
    BearerToken,
    auth_token_claimset,
    get_user,
    get_user_email,
    validate_and_get_project_from_query,
)
from app.workloads.enums import WorkloadType
from app.workspaces.enums import WorkspaceType
from tests import factory
from tests.conftest import get_test_client


def setup_test_dependencies(env, db_session, mock_claimset):
    """Set up common test dependencies."""
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: env.project
    app.dependency_overrides[get_user_email] = lambda: env.user.email
    app.dependency_overrides[get_user] = lambda: env.user
    app.dependency_overrides[BearerToken] = lambda: "test-token"


@pytest.mark.parametrize(
    "workspace_type",
    [
        WorkspaceType.VSCODE,
        WorkspaceType.JUPYTERLAB,
        WorkspaceType.MLFLOW,
    ],
)
@patch("app.workspaces.router.create_development_workspace")
@patch("app.workspaces.router.ensure_cluster_healthy")
async def test_create_workspace_success(
    mock_ensure_healthy, mock_create_workspace, workspace_type: WorkspaceType, db_session: AsyncSession, mock_claimset
):
    """Test successful workspace creation returns 201."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, chart_type=WorkloadType.WORKSPACE)
    workload = await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=chart,
        workload_type=WorkloadType.WORKSPACE,
        name=f"mw-{workspace_type.value}-test",
        display_name=f"Test {workspace_type.value.title()} Workspace",
    )

    mock_ensure_healthy.return_value = None
    mock_create_workspace.return_value = ChartWorkloadResponse.model_validate(workload)

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(
            f"/v1/workspaces/{workspace_type.value}?project_id={str(env.project.id)}",
            json={
                "image": "test-image",
                "gpus": 1,
                "memory_per_gpu": 128,
                "cpu_per_gpu": 4,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["id"] == str(workload.id)
        assert response.json()["name"] == workload.name
        assert response.json()["type"] == workload.type.value
        assert response.json()["display_name"] == workload.display_name


@patch("app.workspaces.router.ensure_cluster_healthy")
@patch("app.workspaces.router.ensure_base_url_configured")
async def test_create_workspace_base_url_not_configured(
    mock_ensure_base_url, mock_ensure_healthy, db_session: AsyncSession, mock_claimset
):
    """Test workspace creation fails with 409 when base URL not configured."""
    env = await factory.create_full_test_environment(db_session)
    mock_ensure_healthy.return_value = None
    mock_ensure_base_url.side_effect = NotReadyException("No base URL configured")

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(
            f"/v1/workspaces/{WorkspaceType.VSCODE.value}?project_id={str(env.project.id)}",
            json={"image": "test-image", "gpus": 1, "memory_per_gpu": 128, "cpu_per_gpu": 4},
        )

        assert response.status_code == status.HTTP_409_CONFLICT


@patch("app.workspaces.router.create_development_workspace")
@patch("app.workspaces.router.ensure_cluster_healthy")
async def test_create_workspace_service_conflict(
    mock_ensure_healthy, mock_create_workspace, db_session: AsyncSession, mock_claimset
):
    """Test workspace creation fails with 409 when service raises ConflictException."""
    env = await factory.create_full_test_environment(db_session)
    mock_ensure_healthy.return_value = None
    mock_create_workspace.side_effect = ConflictException(
        message="Workspace conflict",
        detail="Conflict creating workspace",
    )

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(
            f"/v1/workspaces/{WorkspaceType.MLFLOW.value}?project_id={str(env.project.id)}",
            json={"image": "test-image", "gpus": 1, "memory_per_gpu": 32, "cpu_per_gpu": 4},
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Workspace conflict" in response.json()["detail"]
