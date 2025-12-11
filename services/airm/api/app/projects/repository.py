# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.exceptions import ConflictException
from ..utilities.models import set_updated_fields
from .enums import ProjectStatus
from .models import Project
from .schemas import ProjectCreate, ProjectEdit


async def get_projects_in_cluster(session: AsyncSession, cluster_id: UUID) -> list[Project]:
    result = await session.execute(select(Project).where(Project.cluster_id == cluster_id).order_by(Project.created_at))
    return result.scalars().all()


async def get_projects_in_organization(session: AsyncSession, organization_id: UUID) -> list[Project]:
    result = await session.execute(
        select(Project).where(Project.organization_id == organization_id).order_by(Project.created_at)
    )
    return result.scalars().all()


async def get_project_in_organization(session: AsyncSession, organization_id: UUID, project_id: UUID) -> Project | None:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def get_project_by_name_in_organization(
    session: AsyncSession, organization_id: UUID, project_name: str
) -> Project | None:
    projects = await get_projects_by_names_in_organization(session, [project_name], organization_id)
    return projects[0] if projects else None


async def create_project(
    session: AsyncSession,
    organization_id: UUID,
    project: ProjectCreate,
    creator: str,
    keycloak_group_id: str,
    status: ProjectStatus = ProjectStatus.PENDING,
    status_reason: str = "Project is being created.",
) -> Project:
    new_project = Project(
        **project.model_dump(exclude={"quota"}),
        organization_id=organization_id,
        created_by=creator,
        updated_by=creator,
        keycloak_group_id=keycloak_group_id,
        status=status,
        status_reason=status_reason,
    )
    session.add(new_project)
    try:
        await session.flush()
        return new_project
    except IntegrityError as e:
        error_message = str(e)
        if "projects_name_organization_id_key" in error_message:
            raise ConflictException(f"A project with name '{project.name}' already exists in this organization")
        raise e


async def delete_project(session: AsyncSession, project: Project) -> None:
    await session.delete(project)
    await session.flush()


async def update_project(session: AsyncSession, project: Project, edits: ProjectEdit, updater: str) -> Project:
    for key, value in edits.model_dump(exclude={"quota"}).items():
        setattr(project, key, value)

    set_updated_fields(project, updater)

    await session.flush()
    return project


async def get_projects_by_names_in_organization(
    session: AsyncSession, project_names: list[str], organization_id: UUID
) -> list[Project]:
    """
    Get projects by their names within a specific organization.

    Args:
        session: Database session
        project_names: List of project names to match (from Keycloak group names)
        organization_id: Organization ID to filter projects (required for security)

    Returns:
        List of Project objects matching the names within the organization
    """
    if not project_names:
        return []

    query = select(Project).where(Project.name.in_(project_names), Project.organization_id == organization_id)

    result = await session.execute(query)
    projects = result.scalars().all()

    return list(projects)


async def get_all_projects(session: AsyncSession) -> list[Project]:
    result = await session.execute(select(Project))
    return result.scalars().all()


async def get_active_project_count_per_cluster(session: AsyncSession, cluster_id: UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Project)
        .where(Project.cluster_id == cluster_id, Project.status != ProjectStatus.DELETING.value)
    )
    return result.scalar_one()


async def update_project_status(
    session: AsyncSession,
    project: Project,
    status: ProjectStatus,
    status_reason: str,
    updater: str,
    updated_at: datetime | None = None,
) -> Project:
    project.status = status
    project.status_reason = status_reason
    set_updated_fields(project, updater, updated_at)
    await session.flush()
    return project
