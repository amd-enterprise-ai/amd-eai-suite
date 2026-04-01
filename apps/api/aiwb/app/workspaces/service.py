# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ConflictException

from ..charts.models import Chart
from ..charts.service import get_chart
from ..charts.utils import render_helm_template
from ..dispatch.kube_client import KubernetesClient
from ..workloads.enums import WorkloadStatus, WorkloadType
from ..workloads.models import Workload
from ..workloads.repository import create_workload
from ..workloads.utils import apply_manifest, sanitize_user_id
from .enums import (
    WORKSPACE_USAGE_SCOPE_MAPPING,
    WorkspaceType,
    WorkspaceUsageScope,
    workspace_type_chart_name_mapping,
)
from .schemas import DevelopmentWorkspaceRequest
from .utils import check_workspace_availability_per_namespace


async def get_chart_by_workspace_type(session: AsyncSession, workspace_type: WorkspaceType) -> Chart:
    chart_name = workspace_type_chart_name_mapping[workspace_type]
    return await get_chart(session=session, chart_name=chart_name)


async def create_development_workspace(
    session: AsyncSession,
    kube_client: KubernetesClient,
    submitter: str,
    namespace: str,
    request: DevelopmentWorkspaceRequest,
    workspace_type: WorkspaceType,
    display_name: str | None = None,
) -> Workload:
    """
    Create a new development workspace and deploy it to Kubernetes.

    This uses helm template + kubectl apply (same as airm services).
    """

    # Check workspace availability - per user for most types, per namespace for MLFlow
    if not await check_workspace_availability_per_namespace(session, namespace, workspace_type, submitter):
        workspace_display_name = workspace_type.value.title()
        usage_scope = WORKSPACE_USAGE_SCOPE_MAPPING.get(workspace_type, WorkspaceUsageScope.USER)

        if usage_scope == WorkspaceUsageScope.NAMESPACE:
            raise ConflictException(
                message=f"{workspace_display_name} workspace already running in this namespace",
                detail=f"Only one {workspace_type.value} workspace is allowed per namespace at a time. "
                f"Please wait for the existing workspace to complete or fail before creating a new one.",
            )
        else:
            raise ConflictException(
                message=f"You already have a {workspace_display_name} workspace running",
                detail=f"Only one {workspace_type.value} workspace is allowed per user in this namespace. "
                f"Please delete your existing workspace before creating a new one.",
            )

    chart = await get_chart_by_workspace_type(session, workspace_type)

    # user_inputs contains what the user explicitly provided (no defaults, no metadata)
    # by_alias=True converts field names using alias (e.g., image_pull_secrets -> imagePullSecrets)
    user_inputs = request.model_dump(exclude_unset=True, exclude_none=True, by_alias=True)

    workload = await create_workload(
        session=session,
        display_name=display_name or f"{workspace_type.value.title()} Workspace",
        workload_type=WorkloadType.WORKSPACE,
        chart_id=chart.id,
        namespace=namespace,
        submitter=submitter,
        status=WorkloadStatus.PENDING,
    )

    # Chart signature provides defaults, user_inputs contains only what was explicitly provided
    # Sanitize user_id to be Kubernetes-compatible (replace @ with -)
    sanitized_user_id = sanitize_user_id(submitter)

    helm_values = {
        **chart.signature,
        **user_inputs,
        "metadata": {
            **chart.signature.get("metadata", {}),
            "project_id": namespace,
            "user_id": sanitized_user_id,
            "workload_id": str(workload.id),
        },
    }

    logger.info(f"Deploying {workspace_type.value} workspace {workload.id} to namespace {namespace}")
    logger.debug(f"Helm values: {helm_values}")

    try:
        manifest = await render_helm_template(
            chart=chart,
            name=workload.name,
            namespace=namespace,
            overlays_values=[helm_values],
        )

        await apply_manifest(kube_client, manifest, workload, namespace, submitter)
        workload.manifest = manifest
        await session.flush()

        logger.info(f"Successfully deployed workspace {workload.id}")

    except Exception as e:
        logger.error(f"Failed to deploy workspace {workload.id}: {e}")
        workload.status = WorkloadStatus.FAILED
        await session.flush()
        raise

    return workload
