# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus

from ..charts.models import Chart
from ..charts.service import get_chart
from ..managed_workloads.models import ManagedWorkload
from ..managed_workloads.repository import select_workloads
from ..managed_workloads.schemas import (
    ChartWorkloadCreate,
    WorkloadType,
)
from ..managed_workloads.service import extract_components_and_submit_workload, insert_workload
from ..managed_workloads.utils import (
    get_workload_host_from_HTTPRoute_manifest,
    get_workload_internal_host,
    render_helm_template,
)
from ..messaging.sender import MessageSender
from ..projects.models import Project
from ..users.models import User
from ..utilities.exceptions import ConflictException
from ..workloads.utils import validate_and_parse_workload_manifest
from .enums import WORKSPACE_USAGE_SCOPE_MAPPING, WorkspaceType, workspace_type_chart_name_mapping
from .schemas import DevelopmentWorkspaceRequest


async def check_workspace_availability_per_project(
    session: AsyncSession, project_id: UUID, workspace_type: WorkspaceType
) -> bool:
    """
    Check if a workspace of the given type can be created in the project.

    For project-scoped workspace types (like MLFlow), only one instance is allowed per project
    with status PENDING or RUNNING. Workspaces with FAILED, DELETED, or COMPLETE status
    do not prevent creation of new workspaces.

    Args:
        session: Database session
        project_id: UUID of the project
        workspace_type: Type of workspace to check

    Returns:
        True if workspace can be created, False if project-scoped and already exists
    """
    # Only check for project-scoped workspace types
    if WORKSPACE_USAGE_SCOPE_MAPPING.get(workspace_type, "user") != "project":
        return True

    # Get the target chart name for this workspace type
    target_chart_name = workspace_type_chart_name_mapping[workspace_type]

    # Check for existing workspaces of this type that are not in terminal states
    active_statuses = [WorkloadStatus.PENDING, WorkloadStatus.RUNNING]
    existing_workspaces = await select_workloads(session=session, project_id=project_id, status=active_statuses)

    # Filter by workspace type - check if any existing workspace uses the same chart
    for workspace in existing_workspaces:
        if workspace.chart and workspace.chart.name == target_chart_name:
            return False

    return True


async def get_chart_by_workspace_type(session: AsyncSession, workspace_type: WorkspaceType) -> Chart:
    chart_name = workspace_type_chart_name_mapping[workspace_type]
    return await get_chart(session=session, chart_name=chart_name)


async def create_development_workspace(
    session: AsyncSession,
    creator: User,
    request: DevelopmentWorkspaceRequest,
    token: str,
    project: Project,
    workspace_type: WorkspaceType,
    message_sender: MessageSender,
    display_name: str | None = None,
) -> ManagedWorkload:
    """Create a new development workspace."""
    # Check workspace availability for project-scoped types
    if not await check_workspace_availability_per_project(session, project.id, workspace_type):
        workspace_display_name = workspace_type.value.title()
        raise ConflictException(
            message=f"{workspace_display_name} workspace already running in this project",
            detail=f"Only one {workspace_type.value} workspace is allowed per project at a time. "
            f"Please wait for the existing workspace to complete or fail before creating a new one.",
        )

    chart = await get_chart_by_workspace_type(session, workspace_type)

    user_inputs: dict = {
        **chart.signature,
        "gpus": request.gpus,
        "memory_per_gpu": request.memory_per_gpu,
        "cpu_per_gpu": request.cpu_per_gpu,
        "imagePullSecrets": request.imagePullSecrets or [],
        "metadata": {
            **chart.signature.get("metadata", {}),
            "project_id": str(project.id),
            "user_id": str(creator.id),
            # workload_id will be filled in after the workload is created
        },
    }

    if request.image:
        user_inputs["image"] = request.image

    workload_data = ChartWorkloadCreate(
        chart_id=chart.id,
        type=WorkloadType.WORKSPACE,
        user_inputs=user_inputs,
        display_name=display_name,
    )
    workload = await insert_workload(
        session=session,
        creator=creator.email,
        project=project,
        workload_data=workload_data,
    )

    # Update the workload_id in the user inputs (need to reassign to trigger SQLAlchemy change tracking)
    workload.user_inputs = {
        **workload.user_inputs,
        "metadata": {**workload.user_inputs["metadata"], "workload_id": str(workload.id)},
    }
    await session.flush()

    # Use the updated user_inputs directly for template rendering
    manifest = await render_helm_template(
        chart,
        workload.name,
        project.name,
        overlays_values=[workload.user_inputs],
    )
    workload.manifest = manifest
    await session.flush()

    external_host = get_workload_host_from_HTTPRoute_manifest(
        manifest=manifest, cluster_base_url=project.cluster.workloads_base_url
    )
    internal_host = get_workload_internal_host(workload.name, project.name)

    suffix = ""
    match workspace_type:
        case WorkspaceType.VSCODE:
            suffix = "/?folder=/workload"
        case WorkspaceType.JUPYTERLAB:
            suffix = "/lab"
        case WorkspaceType.COMFYUI:
            suffix = "/"
        case WorkspaceType.MLFLOW:
            suffix = "/"

    if external_host:
        external_host += suffix
    if internal_host:
        internal_host += suffix

    workload.output = {"external_host": external_host, "internal_host": internal_host}
    await session.flush()

    yml_content = await validate_and_parse_workload_manifest(manifest)
    logger.debug(f"Manifest validated for workload {workload.id}.")

    logger.info(f"Submitting workload {workload.id}...")
    await extract_components_and_submit_workload(
        session, workload, project, yml_content, creator.email, token, message_sender
    )

    logger.info(f"Successfully completed managed workload submission for {workload.id}. Returning object.")
    return workload
