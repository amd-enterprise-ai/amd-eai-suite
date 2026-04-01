# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for Workspaces utility functions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workspaces.enums import WorkspaceType, workspace_type_chart_name_mapping
from app.workspaces.utils import check_workspace_availability_per_namespace
from tests import factory


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_no_existing(db_session: AsyncSession) -> None:
    """Test user-scoped workspace available when no existing workspaces."""
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user1@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_different_user(db_session: AsyncSession) -> None:
    """Test user-scoped workspace available for different user."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create workspace for user1
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        submitter="user1@example.com",
    )

    # user2 should be able to create their own workspace
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user2@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_same_user_running_blocks(db_session: AsyncSession) -> None:
    """Test user-scoped workspace blocked for same user with running workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create running workspace for user1
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        submitter="user1@example.com",
    )

    # Same user should NOT be able to create another workspace
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user1@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_same_user_pending_blocks(db_session: AsyncSession) -> None:
    """Test user-scoped workspace blocked for same user with pending workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.JUPYTERLAB]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create pending workspace for user1
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.PENDING,
        submitter="user1@example.com",
    )

    # Same user should NOT be able to create another workspace
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.JUPYTERLAB, "user1@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_same_user_failed_blocks(db_session: AsyncSession) -> None:
    """Test user-scoped workspace blocked for same user with failed workspace (must delete first)."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.COMFYUI]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create failed workspace for user1
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.FAILED,
        submitter="user1@example.com",
    )

    # Same user should NOT be able to create another workspace - must delete failed one first
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.COMFYUI, "user1@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_same_user_unknown_blocks(db_session: AsyncSession) -> None:
    """Test user-scoped workspace blocked for same user with unknown status workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.UNKNOWN,
        submitter="user1@example.com",
    )

    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user1@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_same_user_deleted_allows(db_session: AsyncSession) -> None:
    """Test user-scoped workspace available for same user after deleting previous workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create deleted workspace for user1
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.DELETED,
        submitter="user1@example.com",
    )

    # Same user should be able to create new workspace since previous is deleted
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user1@example.com"
    )
    assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "terminal_status",
    [
        WorkloadStatus.COMPLETE,
        WorkloadStatus.DELETING,
    ],
)
async def test_check_workspace_availability_user_scoped_terminal_statuses_allow(
    db_session: AsyncSession, terminal_status: WorkloadStatus
) -> None:
    """Test that terminal/transitional statuses do not block workspace creation."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=terminal_status,
        submitter="user1@example.com",
    )

    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user1@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_different_namespace(db_session: AsyncSession) -> None:
    """Test user-scoped workspace scoped to namespace - same user can have workspace in different namespace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.JUPYTERLAB]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create workspace in namespace1
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="namespace1",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        submitter="user1@example.com",
    )

    # Same user should be able to create workspace in namespace2
    result = await check_workspace_availability_per_namespace(
        db_session, "namespace2", WorkspaceType.JUPYTERLAB, "user1@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_user_scoped_different_workspace_type(db_session: AsyncSession) -> None:
    """Test user can have different workspace types simultaneously."""
    vscode_chart = await factory.create_chart(
        db_session, name=workspace_type_chart_name_mapping[WorkspaceType.VSCODE], chart_type=WorkloadType.WORKSPACE
    )

    # Create VSCode workspace for user1
    await factory.create_workload(
        db_session,
        chart=vscode_chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        submitter="user1@example.com",
    )

    # Same user should be able to create JupyterLab workspace (different type)
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.JUPYTERLAB, "user1@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_namespace_scoped_pending_blocks(db_session: AsyncSession) -> None:
    """Test namespace-scoped workspace blocked by pending workspace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create pending MLFlow workspace
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.PENDING,
        submitter="user1@example.com",
    )

    # Different user should NOT be able to create MLFlow workspace (namespace-scoped)
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.MLFLOW, "user2@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_workspace_availability_namespace_scoped_different_namespace_allows(
    db_session: AsyncSession,
) -> None:
    """Test namespace-scoped workspace available in different namespace."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.MLFLOW]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create MLFlow workspace in namespace1
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="namespace1",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        submitter="user1@example.com",
    )

    # Should be able to create MLFlow workspace in namespace2
    result = await check_workspace_availability_per_namespace(
        db_session, "namespace2", WorkspaceType.MLFLOW, "user1@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_ignores_non_workspace_workloads(db_session: AsyncSession) -> None:
    """Test that non-workspace workloads are ignored in availability checks."""
    chart_name = workspace_type_chart_name_mapping[WorkspaceType.VSCODE]
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.WORKSPACE)

    # Create a FINE_TUNING workload (not a workspace)
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-namespace",
        workload_type=WorkloadType.FINE_TUNING,
        status=WorkloadStatus.RUNNING,
        submitter="user1@example.com",
    )

    # VSCode workspace should still be available (fine-tuning workload doesn't count)
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user1@example.com"
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_workspace_availability_different_chart_allows(db_session: AsyncSession) -> None:
    """Test that workloads with different charts don't block each other."""
    vscode_chart = await factory.create_chart(
        db_session, name=workspace_type_chart_name_mapping[WorkspaceType.VSCODE], chart_type=WorkloadType.WORKSPACE
    )
    # Create a chart with different name (not a workspace chart)
    other_chart = await factory.create_chart(db_session, name="other-chart", chart_type=WorkloadType.WORKSPACE)

    # Create workspace with other chart
    await factory.create_workload(
        db_session,
        chart=other_chart,
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        submitter="user1@example.com",
    )

    # VSCode workspace should be available (different chart)
    result = await check_workspace_availability_per_namespace(
        db_session, "test-namespace", WorkspaceType.VSCODE, "user1@example.com"
    )
    assert result is True
