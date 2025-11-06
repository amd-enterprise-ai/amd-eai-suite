# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workspaces service tests."""

from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus
from app.charts.config import VSCODE_CHART_NAME
from app.utilities.exceptions import ConflictException
from app.workloads.enums import WorkloadType
from app.workspaces.enums import WorkspaceType
from app.workspaces.schemas import DevelopmentWorkspaceRequest
from app.workspaces.service import (
    check_workspace_availability_per_project,
    create_development_workspace,
    get_chart_by_workspace_type,
)
from tests import factory


@pytest.mark.asyncio
async def test_get_chart_by_workspace_type_success(db_session: AsyncSession):
    """Test getting chart by workspace type"""
    env = await factory.create_full_test_environment(db_session)

    workspace_chart = await factory.create_chart(
        db_session,
        name="vscode-workspace",
        chart_type=WorkloadType.WORKSPACE,
    )

    with patch("app.workspaces.service.get_chart") as mock_get_chart:
        mock_get_chart.return_value = workspace_chart

        result = await get_chart_by_workspace_type(db_session, WorkspaceType.VSCODE)

    assert result is not None
    assert result.id == workspace_chart.id
    assert result.name == "vscode-workspace"

    mock_get_chart.assert_called_once()


@pytest.mark.asyncio
async def test_create_development_workspace_success(db_session: AsyncSession):
    """Test successful workspace creation with mocked external dependencies."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name=VSCODE_CHART_NAME)

    request = DevelopmentWorkspaceRequest(
        image="test/image:latest",
        gpus=1,
        memory_per_gpu=8.0,
        cpu_per_gpu=2.0,
        imagePullSecrets=["secret"],
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

        result = await create_development_workspace(
            db_session,
            env.user,
            request,
            "token",
            env.project,
            WorkspaceType.VSCODE,
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
async def test_create_development_workspace_mlflow_conflict(db_session: AsyncSession):
    """Test MLFlow workspace creation blocked by existing running workspace."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    # Create existing running MLFlow workspace
    await factory.create_chart_workload(
        db_session,
        env.project,
        chart,
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING.value,
    )

    request = DevelopmentWorkspaceRequest()

    with pytest.raises(ConflictException, match="Mlflow workspace already running in this project"):
        await create_development_workspace(
            db_session,
            env.user,
            request,
            "token",
            env.project,
            WorkspaceType.MLFLOW,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("workspace_type", [WorkspaceType.JUPYTERLAB, WorkspaceType.COMFYUI])
async def test_create_development_workspace_url_suffixes(db_session: AsyncSession, workspace_type: WorkspaceType):
    """Test workspace creation URL suffix logic for different workspace types."""
    from app.workspaces.enums import workspace_type_chart_name_mapping

    env = await factory.create_full_test_environment(db_session)
    chart_name = workspace_type_chart_name_mapping[workspace_type]
    chart = await factory.create_chart(db_session, name=chart_name)

    request = DevelopmentWorkspaceRequest()

    with (
        patch("app.workspaces.service.insert_workload") as mock_insert,
        patch("app.workspaces.service.render_helm_template") as mock_render,
        patch("app.workspaces.service.get_workload_host_from_HTTPRoute_manifest") as mock_external_host,
        patch("app.workspaces.service.get_workload_internal_host") as mock_internal_host,
        patch("app.workspaces.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.workspaces.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_workload = await factory.create_chart_workload(
            db_session,
            env.project,
            chart,
            workload_type=WorkloadType.WORKSPACE,
            user_inputs={"metadata": {"project_id": str(env.project.id)}},  # Add metadata
        )
        mock_insert.return_value = mock_workload

        mock_render.return_value = "manifest"
        mock_external_host.return_value = "host.example.com"
        mock_internal_host.return_value = "internal.svc.cluster.local"
        mock_validate.return_value = {"key": "value"}

        result = await create_development_workspace(
            db_session,
            env.user,
            request,
            "token",
            env.project,
            workspace_type,
        )

        # Just verify the function completes successfully
        assert result.id == mock_workload.id


@pytest.mark.asyncio
async def test_create_development_workspace_mlflow_success(db_session: AsyncSession):
    """Test successful MLFlow workspace creation without conflicts."""
    env = await factory.create_full_test_environment(db_session)
    chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    request = DevelopmentWorkspaceRequest()

    with (
        patch("app.workspaces.service.check_workspace_availability_per_project", return_value=True),
        patch("app.workspaces.service.insert_workload") as mock_insert,
        patch("app.workspaces.service.render_helm_template") as mock_render,
        patch("app.workspaces.service.get_workload_host_from_HTTPRoute_manifest") as mock_external_host,
        patch("app.workspaces.service.get_workload_internal_host") as mock_internal_host,
        patch("app.workspaces.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.workspaces.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_workload = await factory.create_chart_workload(
            db_session,
            env.project,
            chart,
            workload_type=WorkloadType.WORKSPACE,
            user_inputs={"metadata": {"project_id": str(env.project.id)}},
        )
        mock_insert.return_value = mock_workload

        mock_render.return_value = "manifest"
        mock_external_host.return_value = "host.example.com"
        mock_internal_host.return_value = "internal.svc.cluster.local"
        mock_validate.return_value = {"key": "value"}

        result = await create_development_workspace(
            db_session,
            env.user,
            request,
            "token",
            env.project,
            WorkspaceType.MLFLOW,
        )

        assert result.id == mock_workload.id


@pytest.mark.asyncio
async def test_check_workspace_availability_project_scoped_running_blocks(db_session: AsyncSession):
    """Test that running MLFlow workspace blocks new MLFlow creation."""
    env = await factory.create_basic_test_environment(db_session)

    # Create MLFlow chart
    mlflow_chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    # Create running MLFlow workspace
    await factory.create_chart_workload(
        db_session,
        env.project,
        mlflow_chart,
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING.value,
    )

    # MLFlow should not be available now
    assert not await check_workspace_availability_per_project(db_session, env.project.id, WorkspaceType.MLFLOW)


@pytest.mark.asyncio
async def test_check_workspace_availability_project_scoped_failed_allows(db_session: AsyncSession):
    """Test that failed MLFlow workspace allows new MLFlow creation."""
    env = await factory.create_basic_test_environment(db_session)

    # Create MLFlow chart
    mlflow_chart = await factory.create_chart(db_session, name="dev-tracking-mlflow")

    # Create failed MLFlow workspace
    await factory.create_chart_workload(
        db_session,
        env.project,
        mlflow_chart,
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.FAILED.value,
    )

    # MLFlow should be available since previous one failed
    assert await check_workspace_availability_per_project(db_session, env.project.id, WorkspaceType.MLFLOW)
