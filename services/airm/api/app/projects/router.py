# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from prometheus_api_client import PrometheusConnect
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import SecretKind

from ..clusters.service import get_cluster_by_id, get_cluster_with_resources
from ..messaging.sender import MessageSender, get_message_sender
from ..metrics.schemas import (
    MetricsScalarWithRange,
    MetricsTimeseries,
    WorkloadsWithMetrics,
)
from ..metrics.service import (
    get_average_wait_time_for_project as get_average_wait_time_for_project_from_ds,
)
from ..metrics.service import (
    get_avg_gpu_idle_time_for_project as get_avg_gpu_idle_time_for_project_from_ds,
)
from ..metrics.service import (
    get_gpu_device_utilization_timeseries_for_project as get_gpu_device_utilization_timeseries_for_project_from_ds,
)
from ..metrics.service import (
    get_gpu_memory_utilization_timeseries_for_project as get_gpu_memory_utilization_timeseries_for_project_from_ds,
)
from ..metrics.service import (
    get_prometheus_client,
    get_workloads_metrics_by_project,
)
from ..metrics.utils import validate_datetime_range
from ..namespaces.service import create_namespace_for_project
from ..organizations.models import Organization
from ..secrets.enums import SecretUseCase
from ..secrets.models import OrganizationScopedSecret, ProjectScopedSecret
from ..secrets.repository import (
    get_organization_scoped_secret_in_organization,
    get_organization_secret_assignment,
    get_secret_in_organization,
)
from ..secrets.schemas import ProjectSecretIn, ProjectSecretsWithParentSecret, SecretWithProjects
from ..secrets.service import (
    add_organization_secret_assignments,
    create_project_scoped_secret_in_organization,
    delete_project_scoped_secret,
    ensure_can_remove_secret_from_projects,
    get_project_secrets_in_project,
    remove_organization_secret_assignments,
)
from ..storages.repository import get_project_storage, get_storage_in_organization
from ..storages.schemas import ProjectStoragesWithParentStorage
from ..storages.service import (
    assign_projects_to_storage,
    get_project_storages_in_project,
    submit_delete_project_storage,
)
from ..utilities.collections.dependencies import (
    get_filter_query_params,
    get_pagination_query_params,
    get_sort_query_params,
)
from ..utilities.collections.schemas import (
    FilterCondition,
    PaginationConditions,
    SortCondition,
)
from ..utilities.database import get_session
from ..utilities.enums import Roles
from ..utilities.exceptions import NotFoundException, ValidationException
from ..utilities.keycloak_admin import (
    KeycloakAdmin,
    get_kc_admin,
)
from ..utilities.security import (
    auth_token_claimset,
    ensure_platform_administrator,
    ensure_user_can_view_project,
    get_projects_accessible_to_user,
    get_user_email,
    get_user_organization,
    is_user_in_role,
    validate_and_get_project_from_query,
)
from ..workloads.schemas import ProjectWorkloadsStats, Workloads
from ..workloads.service import (
    get_stats_for_workloads_in_project,
    get_workloads_by_project,
)
from .models import Project
from .repository import get_project_in_organization
from .repository import update_project as update_project_in_db
from .schemas import (
    ProjectAddUsers,
    ProjectCreate,
    ProjectEdit,
    ProjectResponse,
    Projects,
    ProjectsWithResourceAllocation,
    ProjectWithUsers,
)
from .service import (
    add_users_to_project_and_keycloak_group,
    create_quota,
    get_project_by_id,
    get_project_with_users,
    get_projects_with_resource_allocation,
    remove_user_from_project_and_keycloak_group,
    submit_delete_project,
    update_project_quota,
)
from .service import create_project as create_project_in_db
from .service import get_submittable_projects as get_submittable_projects_from_db

router = APIRouter(tags=["Projects"])


@router.get(
    "/projects/submittable",
    operation_id="get_submittable_projects",
    summary="List projects where user can submit workloads",
    description="""
        List projects where the authenticated user can submit workloads. Regular users
        see only projects they're members of, platform administrators see all organization
        projects. Project membership determines workload submission rights.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Projects,
)
async def get_submittable_projects(
    projects: list[Project] = Depends(get_projects_accessible_to_user),
) -> Projects:
    return await get_submittable_projects_from_db(projects)


@router.get(
    "/projects",
    operation_id="get_projects",
    summary="List all projects in organization (admin only)",
    description="""
        List all projects in the organization with resource allocation and quota information.
        Shows GPU allocation, CPU allocation with percentages, and memory allocation with percentages.
        Requires platform administrator role.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ProjectsWithResourceAllocation,
)
async def get_projects(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
) -> ProjectsWithResourceAllocation:
    return await get_projects_with_resource_allocation(session, organization)


@router.get(
    "/projects/{project_id}",
    operation_id="get_project",
    summary="Get a project by ID",
    status_code=status.HTTP_200_OK,
    response_model=ProjectWithUsers,
)
async def get_project(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    project_id: UUID = Path(description="The ID of the project to be retrieved"),
) -> ProjectWithUsers:
    project = await get_project_by_id(session, organization.id, project_id)
    return await get_project_with_users(kc_admin, session, organization, project)


@router.post(
    "/projects",
    operation_id="create_project",
    summary="Create a new project",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
)
async def create_project(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    session: AsyncSession = Depends(get_session),
    project_in: ProjectCreate = Body(description="The project to be created in the user's organization"),
) -> ProjectResponse:
    cluster = await get_cluster_by_id(session, organization.id, project_in.cluster_id)

    project_db = await create_project_in_db(
        kc_admin=kc_admin,
        session=session,
        cluster=cluster,
        project=project_in,
        creator=user,
    )
    await create_quota(session, project_db, cluster, project_in.quota, user, message_sender)
    await create_namespace_for_project(session, project_db, cluster.id, user, message_sender)
    return ProjectResponse.model_validate(project_db)


@router.put(
    "/projects/{project_id}",
    operation_id="update_project",
    summary="Update a project",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
)
async def update_project(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The ID of the project to be updated"),
    project_edit: ProjectEdit = Body(description="The updated project details"),
) -> ProjectResponse:
    project_db = await get_project_by_id(session, organization.id, project_id)

    project_updated = await update_project_in_db(session, project_db, project_edit, user)

    await update_project_quota(session, project_db, project_db.cluster, project_edit.quota, user, message_sender)
    return ProjectResponse.model_validate(project_updated)


@router.delete(
    "/projects/{project_id}",
    operation_id="delete_project",
    summary="Delete a project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The ID of the project to be deleted"),
) -> None:
    project = await get_project_by_id(session, organization.id, project_id)

    cluster_with_resources = await get_cluster_with_resources(session, project.cluster)
    gpu_vendor = cluster_with_resources.gpu_info.vendor if cluster_with_resources.gpu_info else None

    await submit_delete_project(session, project, user, gpu_vendor, message_sender)


@router.post(
    "/projects/{project_id}/users",
    operation_id="add_users_to_project",
    summary="Add existing users to a project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_users_to_project(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The ID of the project to which users are to be added"),
    project_add_users: ProjectAddUsers = Body(description="The IDs of the users to be added to the project"),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
) -> None:
    project = await get_project_by_id(session, organization.id, project_id)
    await add_users_to_project_and_keycloak_group(
        kc_admin=kc_admin,
        session=session,
        project=project,
        user_ids=project_add_users.user_ids,
    )


@router.delete(
    "/projects/{project_id}/users/{user_id}",
    operation_id="remove_user_from_project",
    summary="Remove a user from a project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_user_from_project(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The ID of the project from which the user is to be removed"),
    user_id: UUID = Path(description="The ID of the user to be removed from the project"),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
) -> None:
    project = await get_project_by_id(session, organization.id, project_id)
    await remove_user_from_project_and_keycloak_group(
        kc_admin=kc_admin, session=session, project=project, user_id=user_id
    )


@router.get(
    "/projects/{project_id}/workloads",
    operation_id="get_cluster_workloads",
    summary="Get workloads for the cluster",
    status_code=status.HTTP_200_OK,
    response_model=Workloads,
)
async def get_project_workloads(
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    project_id: UUID = Path(description="The ID of the project for which to retrieve workloads"),
) -> Workloads:
    await validate_and_get_project_from_query(accessible_projects, project_id)
    return await get_workloads_by_project(session, project_id)


@router.get(
    "/projects/{project_id}/workloads/stats",
    operation_id="get_project_workload_stats",
    summary="Get workload statistics for a specific project",
    status_code=status.HTTP_200_OK,
    response_model=ProjectWorkloadsStats,
)
async def get_project_workload_stats(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The ID of the project from which to retrieve workload statistics"),
) -> ProjectWorkloadsStats:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException(f"Project with ID {project_id} not found in your organization")

    return await get_stats_for_workloads_in_project(session, project)


@router.get(
    "/projects/{project_id}/metrics/gpu_device_utilization",
    operation_id="get_gpu_device_utilization_timeseries_for_project",
    summary="Get project GPU utilization timeseries",
    description="""
        Retrieve GPU compute utilization metrics for a specific project over time.
        Shows percentage of GPU compute capacity used by project workloads during
        specified time period. Essential for resource planning and cost optimization.
    """,
    status_code=status.HTTP_200_OK,
    response_model=MetricsTimeseries,
)
async def get_gpu_device_utilization_timeseries_for_project(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    project_id: UUID = Path(description="The ID of the project for which to return metrics"),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    validate_datetime_range(start, end)

    return await get_gpu_device_utilization_timeseries_for_project_from_ds(
        start=start, end=end, project=project, prometheus_client=prometheus_client
    )


@router.get(
    "/projects/{project_id}/metrics/gpu_memory_utilization",
    operation_id="get_gpu_memory_utilization_timeseries_for_project",
    summary="Get project GPU memory timeseries",
    description="""
        Retrieve GPU memory usage metrics for a specific project over time.
        Shows memory allocation and utilization patterns for project workloads.
        Critical for understanding memory requirements and optimizing resource allocation.
    """,
    status_code=status.HTTP_200_OK,
    response_model=MetricsTimeseries,
)
async def get_gpu_memory_utilization_timeseries_for_project(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    project_id: UUID = Path(description="The ID of the project for which to return metrics"),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    validate_datetime_range(start, end)

    return await get_gpu_memory_utilization_timeseries_for_project_from_ds(
        start=start, end=end, project=project, prometheus_client=prometheus_client
    )


@router.get(
    "/projects/{project_id}/workloads/metrics",
    operation_id="get_project_workloads_metrics",
    summary="Get project workload metrics",
    description="""
        Retrieve comprehensive metrics for all workloads in a specific project.
        Includes resource usage, execution times, and performance statistics.
        Essential for project-level resource optimization and workload analysis.
    """,
    status_code=status.HTTP_200_OK,
    response_model=WorkloadsWithMetrics,
)
async def get_project_workloads_metrics(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The unique ID of the project to retrieve workloads for"),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    pagination_params: PaginationConditions = Depends(get_pagination_query_params),
    sort_params: list[SortCondition] | None = Depends(get_sort_query_params),
    filter_params: list[FilterCondition] | None = Depends(get_filter_query_params),
) -> WorkloadsWithMetrics:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    if sort_params is None:
        sort_params = []

    if filter_params is None:
        filter_params = []

    return await get_workloads_metrics_by_project(
        session,
        project,
        prometheus_client,
        pagination_params,
        sort_params,
        filter_params,
    )


@router.get(
    "/projects/{project_id}/metrics/average_wait_time",
    operation_id="get_average_wait_time_for_project",
    summary="Get project average wait time",
    description="""
        Calculate average workload queue wait time for a project over specified period.
        Measures time from workload submission to execution start. Key indicator for
        resource availability and queue efficiency within the project.
    """,
    status_code=status.HTTP_200_OK,
    response_model=MetricsScalarWithRange,
)
async def get_average_wait_time_for_project(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    project_id: UUID = Path(description="The ID of the project for which to return average wait time metric"),
    start: AwareDatetime = Query(..., description="The start timestamp used to calculate the average wait time"),
    end: AwareDatetime = Query(..., description="The end timestamp used to calculate the average wait time"),
    session: AsyncSession = Depends(get_session),
) -> MetricsScalarWithRange:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    validate_datetime_range(start, end)

    return await get_average_wait_time_for_project_from_ds(session, start=start, end=end, project=project)


@router.get(
    "/projects/{project_id}/metrics/average_gpu_idle_time",
    operation_id="get_avg_gpu_idle_time_for_project",
    summary="Get project GPU idle time",
    description="""
        Calculate average GPU idle time for a project over specified period.
        Measures unused GPU capacity within allocated resources. Helps identify
        optimization opportunities and resource allocation efficiency.
    """,
    status_code=status.HTTP_200_OK,
    response_model=MetricsScalarWithRange,
)
async def get_avg_gpu_idle_time_for_project(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    project_id: UUID = Path(description="The ID of the project for which to return Average GPU Idle time metric"),
    start: AwareDatetime = Query(
        ...,
        description="The start timestamp used to calculate the Average GPU idle time",
    ),
    end: AwareDatetime = Query(
        ...,
        description="The end timestamp used to calculate the the Average GPU idle time",
    ),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsScalarWithRange:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    validate_datetime_range(start, end)

    return await get_avg_gpu_idle_time_for_project_from_ds(
        start=start, end=end, project=project, prometheus_client=prometheus_client
    )


@router.get(
    "/projects/{project_id}/secrets",
    operation_id="get_project_secrets",
    summary="Retrieve secrets for a specific project",
    status_code=status.HTTP_200_OK,
    response_model=ProjectSecretsWithParentSecret,
)
async def get_project_secrets(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The unique ID of the project to retrieve secrets for"),
    use_case: SecretUseCase | None = Query(None, description="Filter secrets by use case"),
    secret_type: SecretKind | None = Query(None, description="Filter secrets by type"),
) -> ProjectSecretsWithParentSecret:
    project = await get_project_in_organization(session, organization.id, project_id)

    if not project:
        raise NotFoundException("Project not found")

    return await get_project_secrets_in_project(session, organization, project, secret_type, use_case)


@router.put(
    "/projects/{project_id}/secrets/{secret_id}/assign",
    operation_id="assign_project_secrets",
    summary="Assign secret for a specific project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_project_secrets(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The unique ID of the project to retrieve secrets for"),
    secret_id: UUID = Path(description="The ID of the secret to be assigned to the project"),
) -> None:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    org_secret = await get_organization_scoped_secret_in_organization(session, organization.id, secret_id)
    if not org_secret:
        raise NotFoundException("Secret not found")

    assigned_secret = await get_organization_secret_assignment(session, secret_id, project_id)
    if assigned_secret:
        raise ValidationException("Secret already assigned to this Project")

    await add_organization_secret_assignments(session, organization.id, org_secret, [project_id], user, message_sender)


@router.delete(
    "/projects/{project_id}/secrets/{secret_id}",
    operation_id="delete_project_secret",
    summary="Delete secret for a specific project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_secret(
    claimset: dict = Depends(auth_token_claimset),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    project_id: UUID = Path(description="The unique ID of the project to retrieve secrets for"),
    secret_id: UUID = Path(description="The ID of the secret to be unassigned from the project"),
) -> None:
    # Platform admins can delete secrets from any project
    # Regular users can only delete secrets from projects they are members of
    if not is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        await validate_and_get_project_from_query(accessible_projects, project_id)

    secret = await get_secret_in_organization(session, organization.id, secret_id)

    if not secret:
        raise NotFoundException("Secret not found")

    await ensure_can_remove_secret_from_projects(session, [project_id], secret_id)

    if isinstance(secret, ProjectScopedSecret):
        await delete_project_scoped_secret(session, secret, user, message_sender)
    elif isinstance(secret, OrganizationScopedSecret):
        await remove_organization_secret_assignments(session, secret, [project_id], message_sender)
    else:
        raise ValidationException("Unknown secret type for deletion")


@router.get(
    "/projects/{project_id}/storages",
    operation_id="get_project_storages",
    summary="Retrieve storages for a specific project",
    status_code=status.HTTP_200_OK,
    response_model=ProjectStoragesWithParentStorage,
)
async def get_project_storages(
    _: None = Depends(ensure_user_can_view_project),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The unique ID of the project to retrieve storages for"),
) -> ProjectStoragesWithParentStorage:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    return await get_project_storages_in_project(session, organization, project)


@router.put(
    "/projects/{project_id}/storages/{storage_id}/assign",
    operation_id="assign_project_storages",
    summary="Assign storage for a specific project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_project_storages(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The unique ID of the project to assign a storage to"),
    storage_id: UUID = Path(description="The ID of the storage to be assigned to the project"),
) -> None:
    project = await get_project_in_organization(session, organization.id, project_id)
    if not project:
        raise NotFoundException("Project not found")

    storage = await get_storage_in_organization(session, organization.id, storage_id)
    if not storage:
        raise NotFoundException("Storage not found")

    project_storage = await get_project_storage(session, storage_id, project_id)
    if project_storage:
        raise ValidationException("Storage already assigned to this Project")

    await assign_projects_to_storage(session, organization.id, storage, [project_id], user, message_sender)


@router.delete(
    "/projects/{project_id}/storages/{storage_id}",
    operation_id="delete_project_storages",
    summary="Delete storage for a specific project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_storage(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    project_id: UUID = Path(description="The unique ID of the project to retrieve storages for"),
    storage_id: UUID = Path(description="The ID of the storage to be unassigned from the project"),
) -> None:
    project_storage = await get_project_storage(session, storage_id, project_id)

    if not project_storage:
        raise NotFoundException("Project Storage not found")

    await submit_delete_project_storage(session, organization.id, project_storage, user, message_sender)


@router.post(
    "/projects/{project_id}/secrets",
    operation_id="create_project_secret",
    summary="Create a new project-scoped secret",
    status_code=status.HTTP_201_CREATED,
    response_model=SecretWithProjects,
)
async def create_project_secret(
    claimset: dict = Depends(auth_token_claimset),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    project_id: UUID = Path(description="The ID of the project to create the secret in"),
    secret_in: ProjectSecretIn = Body(description="The project-scoped secret to be created"),
) -> SecretWithProjects:
    if not is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        await validate_and_get_project_from_query(accessible_projects, project_id)

    project_secret = await create_project_scoped_secret_in_organization(
        session, organization.id, project_id, user, secret_in, message_sender
    )
    return project_secret
