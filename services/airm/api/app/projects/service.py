# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from uuid import UUID

from keycloak import KeycloakAdmin
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import NamespaceStatus, QuotaStatus

from ..clusters.models import Cluster
from ..clusters.schemas import ClusterResponse, ClusterStatus
from ..clusters.service import get_cluster_with_resources
from ..messaging.sender import MessageSender
from ..namespaces.models import Namespace
from ..namespaces.repository import get_namespace_by_project_and_cluster
from ..namespaces.service import delete_namespace_in_cluster
from ..organizations.models import Organization
from ..organizations.repository import get_organization_by_id
from ..quotas.models import Quota
from ..quotas.schemas import QuotaBase, QuotaCreate, QuotaResponse, QuotaUpdate
from ..quotas.service import create_quota_for_cluster, delete_quota_for_cluster, update_quota_for_cluster
from ..quotas.utils import validate_quota_against_available_cluster_resources
from ..users.repository import (
    get_users_in_organization_by_ids,
    get_users_in_organization_by_keycloak_ids,
)
from ..users.utils import (
    is_keycloak_user_active,
    is_keycloak_user_inactive,
    merge_invited_user_details,
    merge_user_details,
)
from ..utilities.exceptions import ConflictException, NotFoundException, UnhealthyException, ValidationException
from ..utilities.keycloak_admin import (
    assign_users_to_group,
    create_group,
    delete_group,
    get_group_members,
    get_users_in_role,
    unassign_users_from_group,
)
from ..utilities.keycloak_admin import get_users_in_organization as get_users_in_organization_from_keycloak
from ..utilities.security import (
    Roles,
)
from .constants import MAX_PROJECTS_PER_CLUSTER
from .enums import ProjectStatus
from .models import Project
from .repository import create_project as create_project_in_db
from .repository import (
    delete_project,
    get_active_project_count_per_cluster,
    get_project_by_name_in_organization,
    get_project_in_organization,
    get_projects_in_organization,
    update_project_status,
)
from .repository import get_projects_in_cluster as get_projects_in_cluster_from_db
from .schemas import (
    ProjectCreate,
    ProjectResponse,
    Projects,
    ProjectsWithResourceAllocation,
    ProjectWithResourceAllocation,
    ProjectWithUsers,
)
from .utils import ensure_project_safe_to_delete, map_to_schema, resolve_project_status


async def get_submittable_projects(accessible_projects: list[Project]) -> Projects:
    """
    Convert accessible projects to submittable projects schema.
    Projects are now passed in from Keycloak group membership.
    """
    projects_list = []
    for project in accessible_projects:
        projects_list.append(map_to_schema(project))

    return Projects(projects=projects_list)


async def get_projects_in_cluster(session: AsyncSession, cluster: ClusterResponse) -> Projects:
    projects = await get_projects_in_cluster_from_db(session, cluster.id)
    return Projects(projects=[map_to_schema(project) for project in projects])


async def get_projects_with_resource_allocation(
    session: AsyncSession, organization: Organization
) -> ProjectsWithResourceAllocation:
    """
    Get all projects in organization with resource allocation information including percentages.
    """
    projects = await get_projects_in_organization(session, organization.id)

    # Get all unique clusters and fetch their resources in parallel to avoid duplicate calls
    unique_clusters = {project.cluster.id: project.cluster for project in projects}
    cluster_resources_tasks = [get_cluster_with_resources(session, cluster) for cluster in unique_clusters.values()]
    cluster_resources_results = await asyncio.gather(*cluster_resources_tasks)

    # Map cluster IDs to their resource information
    clusters_with_resources = {
        cluster_id: resource_result
        for cluster_id, resource_result in zip(unique_clusters.keys(), cluster_resources_results)
    }

    projects_list = []
    for project in projects:
        project_schema = ProjectResponse.model_validate(project)
        project_with_allocation = ProjectWithResourceAllocation(
            **project_schema.model_dump(),
            quota=QuotaResponse.model_validate(project.quota),
            cluster=clusters_with_resources[project.cluster.id],
        )
        projects_list.append(project_with_allocation)

    return ProjectsWithResourceAllocation(projects=projects_list)


async def get_projects_in_cluster_with_resource_allocation(
    session: AsyncSession, cluster: Cluster
) -> ProjectsWithResourceAllocation:
    """
    Get projects in a specific cluster with resource allocation information.
    """
    projects = await get_projects_in_cluster_from_db(session, cluster.id)

    # Get cluster with resource information once
    cluster_with_resources = await get_cluster_with_resources(session, cluster)

    projects_list = []
    for project in projects:
        project_schema = ProjectResponse.model_validate(project)
        project_with_allocation = ProjectWithResourceAllocation(
            **project_schema.model_dump(),
            quota=QuotaResponse.model_validate(project.quota),
            cluster=cluster_with_resources,
        )
        projects_list.append(project_with_allocation)

    return ProjectsWithResourceAllocation(projects=projects_list)


async def get_project_with_users(
    kc_admin: KeycloakAdmin, session: AsyncSession, organization: Organization, project: Project
) -> ProjectWithUsers:
    """
    Get a project with users but without expensive user count calculations.
    Uses Keycloak group membership for user information.
    """
    # Get Keycloak data in parallel for better performance
    group_members, keycloak_users, platform_admin_users = await asyncio.gather(
        get_group_members(kc_admin, project.keycloak_group_id),
        get_users_in_organization_from_keycloak(
            kc_admin=kc_admin, organization_id=organization.keycloak_organization_id
        ),
        get_users_in_role(kc_admin=kc_admin, role=Roles.PLATFORM_ADMINISTRATOR.value),
    )
    platform_admins = {pa["id"] for pa in platform_admin_users}

    # Convert Keycloak group member IDs to database User objects
    group_member_ids = [member["id"] for member in group_members]
    users_in_project = await get_users_in_organization_by_keycloak_ids(session, organization.id, group_member_ids)

    # Separate active and invited users
    active_keycloak_users_by_id = {}
    invited_keycloak_users_by_id = {}

    for user in keycloak_users:
        if is_keycloak_user_active(user):
            active_keycloak_users_by_id[user["id"]] = user
        elif is_keycloak_user_inactive(user):
            invited_keycloak_users_by_id[user["id"]] = user

    active_users_in_project = [
        user for user in users_in_project if str(user.keycloak_user_id) in active_keycloak_users_by_id
    ]
    invited_users_in_project = [
        user for user in users_in_project if str(user.keycloak_user_id) in invited_keycloak_users_by_id
    ]

    return ProjectWithUsers(
        **ProjectResponse.model_validate(project).model_dump(),
        quota=QuotaResponse.model_validate(project.quota),
        cluster=ClusterResponse.model_validate(project.cluster),
        users=[
            merge_user_details(active_keycloak_users_by_id[str(user.keycloak_user_id)], user, platform_admins)
            for user in active_users_in_project
        ],
        invited_users=[
            merge_invited_user_details(invited_user, platform_admins) for invited_user in invited_users_in_project
        ],
    )


async def create_project(
    kc_admin: KeycloakAdmin, session: AsyncSession, cluster: Cluster, project: ProjectCreate, creator: str
) -> Project:
    if ClusterResponse.model_validate(cluster).status is not ClusterStatus.HEALTHY:
        raise UnhealthyException("Project cannot be created for an unhealthy cluster.")

    if await get_project_by_name_in_organization(
        session, organization_id=cluster.organization_id, project_name=project.name
    ):
        raise ConflictException(f"Project with name {project.name} already exists.")

    project_count = await get_active_project_count_per_cluster(session, cluster.id)
    # There is always a default quota "kaiwo" created on the cluster, so account for that
    if project_count >= MAX_PROJECTS_PER_CLUSTER - 1:
        raise ValidationException(f"Maximum of {MAX_PROJECTS_PER_CLUSTER - 1} projects per cluster exceeded.")

    organization = await get_organization_by_id(session, cluster.organization_id)
    assert organization is not None
    keycloak_group_id = await create_group(
        kc_admin, project.name, path=f"/{organization.name}/{project.name}", parent_id=organization.keycloak_group_id
    )

    return await create_project_in_db(
        session, cluster.organization_id, project, creator, keycloak_group_id=keycloak_group_id
    )


async def add_users_to_project_and_keycloak_group(
    kc_admin: KeycloakAdmin, session: AsyncSession, project: Project, user_ids: list[UUID]
) -> None:
    users = await get_users_in_organization_by_ids(session, project.organization_id, user_ids)

    if len(users) != len(user_ids):
        raise NotFoundException("Some users not found in the organization.")

    keycloak_user_ids = [user.keycloak_user_id for user in users]
    await assign_users_to_group(kc_admin=kc_admin, user_ids=keycloak_user_ids, group_id=project.keycloak_group_id)


async def remove_user_from_project_and_keycloak_group(
    kc_admin: KeycloakAdmin, session: AsyncSession, project: Project, user_id: UUID
) -> None:
    users = await get_users_in_organization_by_ids(
        session=session, organization_id=project.organization_id, user_ids=[user_id]
    )
    keycloak_user_ids = [user.keycloak_user_id for user in users]
    await unassign_users_from_group(kc_admin=kc_admin, user_ids=keycloak_user_ids, group_id=project.keycloak_group_id)


async def create_quota(
    session: AsyncSession,
    project: Project,
    cluster: Cluster,
    quota_data: QuotaBase,
    user: str,
    message_sender: MessageSender,
) -> Quota:
    quota_create = QuotaCreate(**quota_data.model_dump(), cluster_id=cluster.id, project_id=project.id)

    cluster_with_resources = await get_cluster_with_resources(session, cluster)
    validation_errors = validate_quota_against_available_cluster_resources(cluster_with_resources, quota_create)

    if validation_errors:
        raise ValidationException(f"Quota exceeds available cluster resources: {', '.join(validation_errors)}")

    gpu_vendor = cluster_with_resources.gpu_info.vendor if cluster_with_resources.gpu_info else None
    return await create_quota_for_cluster(session, project, cluster, gpu_vendor, quota_create, user, message_sender)


async def update_project_quota(
    session: AsyncSession,
    project: Project,
    cluster: Cluster,
    quota_edit: QuotaUpdate,
    user: str,
    message_sender: MessageSender,
) -> QuotaResponse:
    cluster_with_resources = await get_cluster_with_resources(session, cluster)
    current_quota = project.quota
    validation_errors = validate_quota_against_available_cluster_resources(
        cluster_with_resources, quota_edit, current_quota
    )

    if validation_errors:
        raise ValidationException(f"Quota exceeds available cluster resources: {', '.join(validation_errors)}")

    gpu_vendor = cluster_with_resources.gpu_info.vendor if cluster_with_resources.gpu_info else None
    quota = await update_quota_for_cluster(
        session, project.cluster, project.quota, quota_edit, gpu_vendor, user, message_sender
    )

    return quota


async def get_project_by_id(session: AsyncSession, organization_id: UUID, project_id: UUID) -> Project:
    project = await get_project_in_organization(session, organization_id, project_id)
    if not project:
        raise NotFoundException(f"Project with ID {project_id} not found in your organization")
    return project


async def update_project_status_from_components(
    kc_admin: KeycloakAdmin, session: AsyncSession, project: Project
) -> None:
    namespace = await get_namespace_by_project_and_cluster(session, project.id, project.cluster_id)

    if not namespace:
        await update_project_status(session, project, ProjectStatus.FAILED, "Namespace not found", "system")
        return

    await session.refresh(project, ["quota"])

    if not project.quota:
        await update_project_status(session, project, ProjectStatus.FAILED, "Quota not found", "system")
        return

    deleted = await delete_project_if_components_deleted(kc_admin, session, project, project.quota, namespace)
    if deleted:
        return

    project_status, status_reason = resolve_project_status(namespace, project.quota, project)

    await update_project_status(session, project, project_status, status_reason, "system")


async def submit_delete_project(
    session: AsyncSession, project: Project, user: str, gpu_vendor: str | None, message_sender: MessageSender
) -> None:
    ensure_project_safe_to_delete(project)
    await delete_quota_for_cluster(session, project.quota, project.cluster, gpu_vendor, user, message_sender)
    await delete_namespace_in_cluster(session, project, user, message_sender)
    await update_project_status(session, project, ProjectStatus.DELETING, "Project is being deleted", user)


async def delete_project_if_components_deleted(
    kc_admin: KeycloakAdmin, session: AsyncSession, project: Project, quota: Quota, namespace: Namespace
) -> bool:
    if (
        project.status == ProjectStatus.DELETING
        and quota.status == QuotaStatus.DELETED
        and namespace.status == NamespaceStatus.DELETED
    ):
        await delete_project(session, project)
        await delete_group(kc_admin, project.keycloak_group_id)
        return True
    return False
