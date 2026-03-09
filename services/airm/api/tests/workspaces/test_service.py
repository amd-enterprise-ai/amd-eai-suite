# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workspaces service tests."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus
from app.charts.config import VSCODE_CHART_NAME
from app.utilities.exceptions import ConflictException
from app.workloads.enums import WorkloadType
from app.workspaces.enums import WorkspaceType, workspace_type_chart_name_mapping
from app.workspaces.schemas import DevelopmentWorkspaceRequest
from app.workspaces.service import (
    check_workspace_availability_per_project,
    create_development_workspace,
    get_chart_by_workspace_type,
)
from tests import factory


@pytest.mark.asyncio
async def test_get_chart_by_workspace_type_success(db_session: AsyncSession) -> None:
    """Test getting chart by workspace type"""
    env = await factory.create_full_test_environment(db_session)

    workspace_chart = await factory.create_chart(db_session, name="vscode-workspace", chart_type=WorkloadType.WORKSPACE)

    with patch("app.workspaces.service.get_chart") as mock_get_chart:
        mock_get_chart.return_value = workspace_chart

        result = await get_chart_by_workspace_type(db_session, WorkspaceType.VSCODE)

    assert result is not None
    assert result.id == workspace_chart.id
    assert result.name == "vscode-workspace"

    mock_get_chart.assert_called_once()


@pytest.mark.asyncio
async def test_create_development_workspace_success(db_session: AsyncSession) -> None:
    """Test successful workspace creation with mocked external dependencies."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name=VSCODE_CHART_NAME)

    request = DevelopmentWorkspaceRequest(
        image="test/image:latest", gpus=1, memory_per_gpu=8.0, cpu_per_gpu=2.0, imagePullSecrets=["secret"]
    )

    with (
        patch("app.workspaces.service.render_helm_template") as mock_render,
        patch("app.workspaces.service.get_workload_host_from_HTTPRoute_manifest") as mock_external_host,
        patch("app.workspaces.service.get_workload_internal_host") as mock_internal_host,
        patch("app.workspaces.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.workspaces.service.extract_components_and_submit_workload") as mock_extract,
    ):
        # Mock external services
        mock_render.return_value = "manifest"
        mock_external_host.return_value = "host.example.com"
        mock_internal_host.return_value = "internal.svc.cluster.local"
        mock_validate.return_value = {"key": "value"}
        mock_message_sender = AsyncMock()

        result = await create_development_workspace(
            db_session, env.user, request, "token", env.project, WorkspaceType.VSCODE, mock_message_sender
        )

        # Verify workspace was created successfully (would fail with AttributeError if chart not loaded)
        assert result.id is not None
        assert result.type == WorkloadType.WORKSPACE
        assert result.chart_id == chart.id

        # Verify name and display_name were generated (proves chart relationship was loaded)
        assert result.name is not None
        assert result.name.startswith("mw-")
        assert result.display_name is not None

        # Verify external services were called
        mock_extract.assert_called_once()


@pytest.mark.asyncio
async def test_create_development_workspace_with_image_pull_secrets(db_session: AsyncSession) -> None:
    """Test that image_pull_secrets are properly included in user_inputs and passed to Helm."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name=VSCODE_CHART_NAME)

    request = DevelopmentWorkspaceRequest(
        image_pull_secrets=["minio-credentials-fetcher", "docker-registry-secret"],
        gpus=1,
        memory_per_gpu=8.0,
        cpu_per_gpu=2.0,
    )

    with (
        patch("app.workspaces.service.render_helm_template") as mock_render,
        patch("app.workspaces.service.get_workload_host_from_HTTPRoute_manifest") as mock_external_host,
        patch("app.workspaces.service.get_workload_internal_host") as mock_internal_host,
        patch("app.workspaces.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.workspaces.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_render.return_value = "manifest"
        mock_external_host.return_value = "host.example.com"
        mock_internal_host.return_value = "internal.svc.cluster.local"
        mock_validate.return_value = {"key": "value"}
        mock_message_sender = AsyncMock()

        result = await create_development_workspace(
            db_session, env.user, request, "token", env.project, WorkspaceType.VSCODE, mock_message_sender
        )

        # Verify workspace was created
        assert result.id is not None

        # Verify imagePullSecrets are in user_inputs (camelCase for Helm compatibility)
        assert result.user_inputs is not None
        assert "imagePullSecrets" in result.user_inputs
        assert result.user_inputs["imagePullSecrets"] == ["minio-credentials-fetcher", "docker-registry-secret"]

        # Verify render_helm_template was called with user_inputs containing imagePullSecrets
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        overlays_values = call_args.kwargs["overlays_values"]
        assert len(overlays_values) > 0
        assert overlays_values[0]["imagePullSecrets"] == ["minio-credentials-fetcher", "docker-registry-secret"]


@pytest.mark.asyncio
async def test_create_development_workspace_without_image_pull_secrets(db_session: AsyncSession) -> None:
    """Test that workspaces can be created without image_pull_secrets (empty list by default)."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name=VSCODE_CHART_NAME)

    request = DevelopmentWorkspaceRequest(gpus=1, memory_per_gpu=8.0, cpu_per_gpu=2.0)

    with (
        patch("app.workspaces.service.render_helm_template") as mock_render,
        patch("app.workspaces.service.get_workload_host_from_HTTPRoute_manifest") as mock_external_host,
        patch("app.workspaces.service.get_workload_internal_host") as mock_internal_host,
        patch("app.workspaces.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.workspaces.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_render.return_value = "manifest"
        mock_external_host.return_value = "host.example.com"
        mock_internal_host.return_value = "internal.svc.cluster.local"
        mock_validate.return_value = {"key": "value"}
        mock_message_sender = AsyncMock()

        result = await create_development_workspace(
            db_session, env.user, request, "token", env.project, WorkspaceType.VSCODE, mock_message_sender
        )

        # Verify workspace was created
        assert result.id is not None

        # Verify imagePullSecrets is empty list (default, camelCase for Helm compatibility)
        assert result.user_inputs is not None
        assert "imagePullSecrets" in result.user_inputs
        assert result.user_inputs["imagePullSecrets"] == []


@pytest.mark.asyncio
async def test_create_development_workspace_mlflow_conflict(db_session: AsyncSession) -> None:
    """Test MLFlow workspace creation blocked by existing running workspace."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    # Create existing running MLFlow workspace
    await factory.create_chart_workload(
        db_session, env.project, chart, workload_type=WorkloadType.WORKSPACE, status=WorkloadStatus.RUNNING.value
    )

    request = DevelopmentWorkspaceRequest()
    mock_message_sender = AsyncMock()

    with pytest.raises(ConflictException) as exc_info:
        await create_development_workspace(
            db_session, env.user, request, "token", env.project, WorkspaceType.MLFLOW, mock_message_sender
        )

    assert "already running" in str(exc_info.value.message).lower()


@pytest.mark.parametrize(
    "workspace_type,expected_suffix",
    [
        (WorkspaceType.VSCODE, "/?folder=/workload"),
        (WorkspaceType.JUPYTERLAB, "/lab"),
        (WorkspaceType.COMFYUI, "/"),
    ],
)
@pytest.mark.asyncio
async def test_create_development_workspace_url_suffixes(
    db_session: AsyncSession, workspace_type: WorkspaceType, expected_suffix: str
) -> None:
    """Test that different workspace types get correct URL suffixes."""
    env = await factory.create_full_test_environment(db_session)
    chart_name = workspace_type_chart_name_mapping[workspace_type]
    chart = await factory.create_chart(db_session, name=chart_name)

    request = DevelopmentWorkspaceRequest()

    with (
        patch("app.workspaces.service.render_helm_template") as mock_render,
        patch("app.workspaces.service.get_workload_host_from_HTTPRoute_manifest") as mock_external_host,
        patch("app.workspaces.service.get_workload_internal_host") as mock_internal_host,
        patch("app.workspaces.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.workspaces.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_render.return_value = "manifest"
        mock_external_host.return_value = "https://cluster.example.com/path"
        mock_internal_host.return_value = "service.namespace.svc.cluster.local"
        mock_validate.return_value = {"key": "value"}
        mock_message_sender = AsyncMock()

        result = await create_development_workspace(
            db_session, env.user, request, "token", env.project, workspace_type, mock_message_sender
        )

        assert result.output is not None
        assert "external_host" in result.output
        assert result.output["external_host"].endswith(expected_suffix)
        assert "internal_host" in result.output
        assert result.output["internal_host"].endswith(expected_suffix)


@pytest.mark.asyncio
async def test_create_development_workspace_mlflow_success(db_session: AsyncSession) -> None:
    """Test successful MLFlow workspace creation when no existing workspace."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    request = DevelopmentWorkspaceRequest()

    with (
        patch("app.workspaces.service.render_helm_template") as mock_render,
        patch("app.workspaces.service.get_workload_host_from_HTTPRoute_manifest") as mock_external_host,
        patch("app.workspaces.service.get_workload_internal_host") as mock_internal_host,
        patch("app.workspaces.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.workspaces.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_render.return_value = "manifest"
        mock_external_host.return_value = "https://cluster.example.com/path"
        mock_internal_host.return_value = "service.namespace.svc.cluster.local"
        mock_validate.return_value = {"key": "value"}
        mock_message_sender = AsyncMock()

        result = await create_development_workspace(
            db_session, env.user, request, "token", env.project, WorkspaceType.MLFLOW, mock_message_sender
        )

        assert result.id is not None
        assert result.type == WorkloadType.WORKSPACE


@pytest.mark.asyncio
async def test_check_workspace_availability_project_scoped_running_blocks(db_session: AsyncSession) -> None:
    """Test that running project-scoped workspace blocks new creation."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    # Create running workspace
    await factory.create_chart_workload(
        db_session, env.project, chart, workload_type=WorkloadType.WORKSPACE, status=WorkloadStatus.RUNNING.value
    )

    result = await check_workspace_availability_per_project(db_session, env.project.id, WorkspaceType.MLFLOW)

    assert result is False


@pytest.mark.asyncio
async def test_check_workspace_availability_project_scoped_failed_allows(db_session: AsyncSession) -> None:
    """Test that failed project-scoped workspace allows new creation."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    # Create failed workspace
    await factory.create_chart_workload(
        db_session, env.project, chart, workload_type=WorkloadType.WORKSPACE, status=WorkloadStatus.FAILED.value
    )

    result = await check_workspace_availability_per_project(db_session, env.project.id, WorkspaceType.MLFLOW)

    assert result is True
