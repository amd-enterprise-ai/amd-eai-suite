# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from sqlalchemy.ext.asyncio import AsyncSession

from ..workloads.enums import WorkloadStatus, WorkloadType
from ..workloads.repository import get_workloads
from .enums import (
    WORKSPACE_USAGE_SCOPE_MAPPING,
    WorkspaceType,
    WorkspaceUsageScope,
    workspace_type_chart_name_mapping,
)


async def check_workspace_availability_per_namespace(
    session: AsyncSession, namespace: str, workspace_type: WorkspaceType, creator_email: str
) -> bool:
    """
    Check if a workspace of the given type can be created in the namespace.

    For namespace-scoped workspace types (like MLFlow), only one instance is allowed per namespace.
    For user-scoped workspace types (like VSCode, Jupyter, ComfyUI), only one instance per user per namespace.

    Workspaces in PENDING, RUNNING, FAILED, or UNKNOWN status block creation.
    Users must explicitly delete failed workspaces before creating a new one of the same type.

    Args:
        session: Database session
        namespace: Kubernetes namespace
        workspace_type: Type of workspace (vscode, jupyter, etc.)
        creator_email: Email of the user creating the workspace

    Returns:
        True if workspace can be created, False if limit would be exceeded
    """
    target_chart_name = workspace_type_chart_name_mapping[workspace_type]
    existing_workspaces = await get_workloads(
        session=session,
        namespace=namespace,
        workload_types=[WorkloadType.WORKSPACE],
        status_filter=[WorkloadStatus.PENDING, WorkloadStatus.RUNNING, WorkloadStatus.FAILED, WorkloadStatus.UNKNOWN],
    )

    # Filter by workspace type - check if any existing workspace uses the same chart
    usage_scope = WORKSPACE_USAGE_SCOPE_MAPPING.get(workspace_type, WorkspaceUsageScope.USER)

    for workspace in existing_workspaces:
        if workspace.chart and workspace.chart.name == target_chart_name:
            if usage_scope == WorkspaceUsageScope.NAMESPACE:
                # Namespace-scoped (e.g., MLFlow): only 1 per namespace total
                return False
            elif workspace.created_by == creator_email:
                # User-scoped: only 1 per user per namespace (including failed ones)
                return False

    return True
