# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..clusters.schemas import ClusterResponse, ClusterStatus
from ..clusters.service import get_accessible_clusters
from ..messaging.sender import MessageSender, get_message_sender
from ..metrics.schemas import GpuDeviceSingleMetricResponse, MetricsTimeRange
from ..metrics.service import (
    get_gpu_device_junction_temperature_for_workload,
    get_gpu_device_power_usage_for_workload,
    get_gpu_device_vram_utilization_for_workload,
    get_prometheus_client,
)
from ..projects.models import Project
from ..users.models import User
from ..utilities.database import get_session
from ..utilities.enums import Roles
from ..utilities.exceptions import NotFoundException, UnhealthyException, ValidationException
from ..utilities.security import (
    BearerToken,
    auth_token_claimset,
    ensure_user_can_view_workload,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    is_user_in_role,
    validate_and_get_project_from_query,
)
from .enums import WorkloadType
from .repository import get_workload_by_id, get_workload_by_id_and_user_membership
from .schemas import WorkloadMetricsDetailsResponse, WorkloadResponse, Workloads, WorkloadsStats, WorkloadWithComponents
from .service import create_and_submit_workload as submit_workload_to_cluster
from .service import (
    get_stats_for_workloads,
    get_stats_for_workloads_in_accessible_clusters,
    get_workload_with_components,
    get_workloads_accessible_to_user,
    get_workloads_by_project,
    submit_delete_workload,
)
from .service import (
    get_workload_details as get_workload_details_from_service,
)
from .utils import validate_and_parse_workload_manifest

router = APIRouter(tags=["Workloads"])


@router.post(
    "/workloads",
    operation_id="submit_workload",
    summary="Submit a new workload",
    description="""
        Deploy a containerized workload (training, inference, workspace, or custom) to a GPU cluster.
        Requires active project with available quota, valid Kubernetes YAML manifest (max 2MB),
        and healthy cluster. Workload will be queued and scheduled based on resource availability.
    """,
    status_code=status.HTTP_200_OK,
    response_model=WorkloadResponse,
)
async def submit_workload(
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    token: str = Depends(BearerToken),
    project: Project = Depends(validate_and_get_project_from_query),
    manifest: UploadFile = File(..., description="The YAML file to be uploaded."),
    workload_type: WorkloadType = Query(WorkloadType.CUSTOM, description="Type of workload being submitted."),
    display_name: str = Query(
        ...,
        description="display name for the workload.",
        min_length=2,
        max_length=256,
        pattern=r"^[a-zA-Z0-9 _\-\.,:\(\)\[\]\+@#]+$",  # Allow alphanumeric, spaces, and some special characters
    ),
) -> WorkloadResponse:
    if manifest.size > 2 * 1024 * 1024:
        raise ValidationException("File size too large. Max size is 2 MB.")

    if ClusterResponse.model_validate(project.cluster).status is not ClusterStatus.HEALTHY:
        raise UnhealthyException(f"Cannot submit workload to cluster '{project.cluster.name}' - cluster is not healthy")

    try:
        yml_content = await validate_and_parse_workload_manifest(manifest)
    except yaml.YAMLError as ymlErr:
        raise ValidationException(f"Invalid YAML content in workload manifest: {ymlErr}")
    return await submit_workload_to_cluster(
        session, project, yml_content, user, token, workload_type, display_name, message_sender
    )


@router.delete(
    "/workloads/{workload_id}",
    operation_id="delete_workload",
    summary="Delete a submitted workload",
    description="""
        Terminate and remove a workload from the cluster. Sends deletion request to the
        cluster Agent which handles graceful shutdown. Requires project membership
        and workload ownership or administrator role.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workload(
    user: User = Depends(get_user),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    claimset: dict = Depends(auth_token_claimset),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    workload_id: UUID = Path(description="The ID of the workload to be deleted"),
) -> None:
    if is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        workload = await get_workload_by_id(session, workload_id)
    else:
        workload = await get_workload_by_id_and_user_membership(session, workload_id, accessible_projects)

    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found or access denied")

    await submit_delete_workload(session, workload, user.email, message_sender)


@router.get(
    "/workloads/stats",
    operation_id="get_workload_stats",
    summary="Get workload stats",
    description="""
        Retrieve aggregate workload statistics across accessible clusters including counts
        by status (running, pending, completed, failed). Platform administrators see statistics for
        all clusters. Regular users see statistics only for clusters accessible through their project memberships.
    """,
    status_code=status.HTTP_200_OK,
    response_model=WorkloadsStats,
)
async def get_workload_stats(
    claimset: dict = Depends(auth_token_claimset),
    session: AsyncSession = Depends(get_session),
) -> WorkloadsStats:
    if is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        return await get_stats_for_workloads(session)
    else:
        accessible_projects = await get_projects_accessible_to_user(claimset, session)
        accessible_clusters = get_accessible_clusters(accessible_projects)
        return await get_stats_for_workloads_in_accessible_clusters(session, accessible_clusters)


@router.get(
    "/workloads/{workload_id}/metrics/gpu-devices/vram-utilization",
    operation_id="get_workload_gpu_device_vram_utilization",
    summary="Get per-GPU VRAM utilization for a workload",
    description="""
        Retrieve VRAM utilization percentage over time for each GPU device of a workload.
        Platform administrators can access any workload; regular users only workloads in projects they belong to.
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_workload_gpu_device_vram_utilization(
    workload_id: UUID = Path(description="The ID of the workload"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    _: None = Depends(ensure_user_can_view_workload),
) -> GpuDeviceSingleMetricResponse:
    return await get_gpu_device_vram_utilization_for_workload(
        workload_id, prometheus_client, start=time_range.start, end=time_range.end, step=time_range.step
    )


@router.get(
    "/workloads/{workload_id}/metrics/gpu-devices/junction-temperature",
    operation_id="get_workload_gpu_device_junction_temperature",
    summary="Get per-GPU junction temperature for a workload",
    description="""
        Retrieve junction temperature (Celsius) over time for each GPU device of a workload.
        Platform administrators can access any workload; regular users only workloads in projects they belong to.
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_workload_gpu_device_junction_temperature(
    workload_id: UUID = Path(description="The ID of the workload"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    _: None = Depends(ensure_user_can_view_workload),
) -> GpuDeviceSingleMetricResponse:
    return await get_gpu_device_junction_temperature_for_workload(
        workload_id, prometheus_client, start=time_range.start, end=time_range.end, step=time_range.step
    )


@router.get(
    "/workloads/{workload_id}/metrics/gpu-devices/power-usage",
    operation_id="get_workload_gpu_device_power_usage",
    summary="Get per-GPU power usage for a workload",
    description="""
        Retrieve GPU power draw (watts) over time for each GPU device of a workload.
        Platform administrators can access any workload; regular users only workloads in projects they belong to.
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_workload_gpu_device_power_usage(
    workload_id: UUID = Path(description="The ID of the workload"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    _: None = Depends(ensure_user_can_view_workload),
) -> GpuDeviceSingleMetricResponse:
    return await get_gpu_device_power_usage_for_workload(
        workload_id, prometheus_client, start=time_range.start, end=time_range.end, step=time_range.step
    )


@router.get(
    "/workloads/{workload_id}/metrics",
    operation_id="get_workload_metrics",
    summary="Get workload information card details",
    description="""
        Retrieve static workload details for the information cards, including
        basic information, cluster and resources, and timeline data.
        Requires project membership for the workload's project.
    """,
    status_code=status.HTTP_200_OK,
    response_model=WorkloadMetricsDetailsResponse,
)
async def get_workload_metrics(
    workload_id: UUID = Path(description="The ID of the workload"),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    _: None = Depends(ensure_user_can_view_workload),
) -> WorkloadMetricsDetailsResponse:
    workload = await get_workload_by_id(session, workload_id)
    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found")
    return await get_workload_details_from_service(session, workload, prometheus_client)


@router.get(
    "/workloads/{workload_id}",
    operation_id="get_workload_by_id",
    summary="Get a workload by ID, including its components",
    description="""
        Retrieve detailed information about a specific workload including status,
        resource allocation, and component details (pods, services). Requires project
        membership for the workload's project.
    """,
    status_code=status.HTTP_200_OK,
    response_model=WorkloadWithComponents,
)
async def get_workload(
    session: AsyncSession = Depends(get_session),
    workload_id: UUID = Path(description="The ID of the workload to be retrieved"),
    _: None = Depends(ensure_user_can_view_workload),
) -> WorkloadWithComponents:
    workload = await get_workload_by_id(session, workload_id)

    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found or access denied")

    return await get_workload_with_components(session, workload)


@router.get(
    "/workloads",
    operation_id="get_workloads",
    summary="Get all workloads accessible to the user, optionally scoped by the specified project",
    description="""
        List workloads accessible to the authenticated user. Can be filtered by project.
        Returns workload metadata including status, creation time, and resource requests.
        Results limited to projects where the user has membership.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Workloads,
)
async def get_workloads(
    project_id: UUID | None = Query(None, description="The ID of the project for which to retrieve workloads"),
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
) -> Workloads:
    if project_id:
        await validate_and_get_project_from_query(accessible_projects, project_id)
        return await get_workloads_by_project(session, project_id)
    else:
        return await get_workloads_accessible_to_user(session, accessible_projects)
