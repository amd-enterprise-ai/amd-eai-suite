# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workspaces service tests."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ConflictException
from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.repository import get_workloads
from app.workspaces.enums import WorkspaceType, workspace_type_chart_name_mapping
from app.workspaces.schemas import DevelopmentWorkspaceRequest
from app.workspaces.service import (
    create_development_workspace,
    get_chart_by_workspace_type,
)
from app.workspaces.utils import check_workspace_availability_per_namespace
from tests import factory


@pytest.mark.asyncio
async def test_get_chart_by_workspace_type_success(db_session: AsyncSession) -> None:
    """Test getting chart by workspace type."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    workspace_chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    result = await get_chart_by_workspace_type(db_session, WorkspaceType.VSCODE)

    assert result is not None
    assert result.id == workspace_chart.id
    assert result.name == chart_name


@pytest.mark.asyncio
async def test_create_development_workspace_success(db_session: AsyncSession, mock_kube_client: AsyncMock) -> None:
    """Test successful workspace creation with mocked external dependencies."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest(
        image="test/image:latest", gpus=1, memory_per_gpu=8.0, cpu_per_gpu=2.0, image_pull_secrets=["secret"]
    )

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.VSCODE,
        )

        assert result.id is not None
        assert result.type == WorkloadType.WORKSPACE
        assert result.chart_id == chart.id
        assert result.name is not None
        assert result.name.startswith("wb-")  # New naming convention
        assert result.display_name is not None

        mock_apply.assert_called_once()


@pytest.mark.asyncio
async def test_create_development_workspace_mlflow_conflict(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test MLFlow workspace creation blocked by existing running workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create existing running MLFlow workspace
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
    )

    request = DevelopmentWorkspaceRequest()

    with pytest.raises(ConflictException, match="workspace already running"):
        await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.MLFLOW,
        )


@pytest.mark.asyncio
async def test_create_development_workspace_mlflow_success(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test successful MLFlow workspace creation without conflicts."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest()

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.MLFLOW,
        )

        assert result.id is not None
        assert result.type == WorkloadType.WORKSPACE


@pytest.mark.asyncio
async def test_check_workspace_availability_namespace_scoped_running_blocks(
    db_session: AsyncSession,
) -> None:
    """Test that running MLFlow workspace blocks new MLFlow creation."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    mlflow_chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create running MLFlow workspace
    await factory.create_workload(
        db_session,
        chart=mlflow_chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
    )

    # MLFlow should not be available now
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.MLFLOW, "test@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_workspace_availability_namespace_scoped_deleted_allows(
    db_session: AsyncSession,
) -> None:
    """Test that deleted MLFlow workspace allows new MLFlow creation."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    mlflow_chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create deleted MLFlow workspace
    await factory.create_workload(
        db_session,
        chart=mlflow_chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.DELETED,
    )

    # MLFlow should be available since previous one is deleted
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.MLFLOW, "test@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_namespace_scoped_failed_blocks(
    db_session: AsyncSession,
) -> None:
    """Test that failed MLFlow workspace blocks new MLFlow creation (must delete first)."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    mlflow_chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create failed MLFlow workspace
    await factory.create_workload(
        db_session,
        chart=mlflow_chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.FAILED,
    )

    # MLFlow should NOT be available - user must delete failed workspace first
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.MLFLOW, "test@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_create_development_workspace_vscode_user_conflict(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test VSCode workspace creation blocked by existing user workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create existing VSCode workspace for same user
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        submitter="test@example.com",
    )

    request = DevelopmentWorkspaceRequest()

    with pytest.raises(ConflictException, match="already have a.*workspace running"):
        await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.VSCODE,
        )


@pytest.mark.asyncio
async def test_create_development_workspace_vscode_success(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test successful VSCode workspace creation."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest(gpus=2, memory_per_gpu=64.0, cpu_per_gpu=8.0)

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.VSCODE,
        )

        assert result.id is not None
        assert result.type == WorkloadType.WORKSPACE
        assert result.chart_id == chart.id
        assert result.status == WorkloadStatus.PENDING


@pytest.mark.asyncio
async def test_create_development_workspace_jupyterlab_success(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test successful JupyterLab workspace creation."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.JUPYTERLAB]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest(gpus=1, memory_per_gpu=32.0)

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.JUPYTERLAB,
        )

        assert result.id is not None
        assert result.type == WorkloadType.WORKSPACE
        assert result.display_name == "Jupyterlab Workspace"


@pytest.mark.asyncio
async def test_create_development_workspace_jupyterlab_user_conflict(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test JupyterLab workspace creation blocked by existing user workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.JUPYTERLAB]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create existing JupyterLab workspace for same user
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.PENDING,
        submitter="test@example.com",
    )

    request = DevelopmentWorkspaceRequest()

    with pytest.raises(ConflictException, match="already have a.*workspace running"):
        await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.JUPYTERLAB,
        )


@pytest.mark.asyncio
async def test_create_development_workspace_comfyui_success(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test successful ComfyUI workspace creation."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.COMFYUI]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest(gpus=4, memory_per_gpu=128.0, cpu_per_gpu=16.0)

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.COMFYUI,
        )

        assert result.id is not None
        assert result.type == WorkloadType.WORKSPACE
        assert result.display_name == "Comfyui Workspace"


@pytest.mark.asyncio
async def test_create_development_workspace_deployment_failure(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test workspace creation handles deployment failure correctly."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest()

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.side_effect = Exception("Kubernetes API error")

        with pytest.raises(Exception, match="Kubernetes API error"):
            await create_development_workspace(
                session=db_session,
                kube_client=mock_kube_client,
                submitter="test@example.com",
                namespace="test-namespace",
                request=request,
                workspace_type=WorkspaceType.VSCODE,
            )

        # Verify workload was created but marked as FAILED

        workloads = await get_workloads(session=db_session, namespace="test-namespace")
        assert len(workloads) == 1
        assert workloads[0].status == WorkloadStatus.FAILED


@pytest.mark.asyncio
async def test_create_development_workspace_custom_display_name(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test workspace creation with custom display name."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest()

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.VSCODE,
            display_name="My Custom Dev Environment",
        )

        assert result.display_name == "My Custom Dev Environment"


@pytest.mark.asyncio
async def test_get_chart_by_workspace_type_jupyterlab(db_session: AsyncSession) -> None:
    """Test getting chart by workspace type for JupyterLab."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.JUPYTERLAB]
    workspace_chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    result = await get_chart_by_workspace_type(db_session, WorkspaceType.JUPYTERLAB)

    assert result is not None
    assert result.id == workspace_chart.id
    assert result.name == chart_name


@pytest.mark.asyncio
async def test_get_chart_by_workspace_type_comfyui(db_session: AsyncSession) -> None:
    """Test getting chart by workspace type for ComfyUI."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.COMFYUI]
    workspace_chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    result = await get_chart_by_workspace_type(db_session, WorkspaceType.COMFYUI)

    assert result is not None
    assert result.id == workspace_chart.id
    assert result.name == chart_name


@pytest.mark.asyncio
async def test_get_chart_by_workspace_type_mlflow(db_session: AsyncSession) -> None:
    """Test getting chart by workspace type for MLFlow."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    workspace_chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    result = await get_chart_by_workspace_type(db_session, WorkspaceType.MLFLOW)

    assert result is not None
    assert result.id == workspace_chart.id
    assert result.name == chart_name


@pytest.mark.asyncio
async def test_create_development_workspace_with_image_pull_secrets(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test workspace creation with image pull secrets converts to camelCase for Helm."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest(
        image="private-registry/my-image:latest",
        image_pull_secrets=["docker-registry-secret", "ecr-secret"],
    )

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.VSCODE,
        )

        assert result.id is not None

        # Verify render_helm_template was called with imagePullSecrets in camelCase
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        overlays_values = call_args.kwargs["overlays_values"]
        assert len(overlays_values) > 0

        # imagePullSecrets should be in camelCase for Helm template compatibility
        assert "imagePullSecrets" in overlays_values[0]
        assert overlays_values[0]["imagePullSecrets"] == ["docker-registry-secret", "ecr-secret"]

        # Ensure snake_case version is not present
        assert "image_pull_secrets" not in overlays_values[0]


@pytest.mark.asyncio
async def test_create_development_workspace_without_image_pull_secrets(
    db_session: AsyncSession, mock_kube_client: AsyncMock
) -> None:
    """Test workspace creation without image pull secrets doesn't include the field."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    request = DevelopmentWorkspaceRequest(image="public-image:latest")

    with (
        patch("app.workspaces.service.render_helm_template", autospec=True) as mock_render,
        patch("app.workspaces.service.apply_manifest", autospec=True) as mock_apply,
    ):
        mock_render.return_value = "manifest"
        mock_apply.return_value = None

        result = await create_development_workspace(
            session=db_session,
            kube_client=mock_kube_client,
            submitter="test@example.com",
            namespace="test-namespace",
            request=request,
            workspace_type=WorkspaceType.VSCODE,
        )

        assert result.id is not None

        # Verify that imagePullSecrets is not in the helm values when not provided
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        overlays_values = call_args.kwargs["overlays_values"]
        assert len(overlays_values) > 0

        # Neither camelCase nor snake_case should be present
        assert "imagePullSecrets" not in overlays_values[0]
        assert "image_pull_secrets" not in overlays_values[0]
