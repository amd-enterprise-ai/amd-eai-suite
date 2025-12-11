# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ProjectSecretStatus, SecretKind, SecretScope

from ..utilities.exceptions import ConflictException
from ..utilities.models import set_updated_fields
from .enums import SecretStatus, SecretUseCase
from .models import OrganizationScopedSecret, OrganizationSecretAssignment, ProjectScopedSecret, Secret
from .schemas import OrganizationSecretIn, ProjectSecretIn


async def get_secret_in_organization(session: AsyncSession, organization_id: UUID, secret_id: UUID) -> Secret | None:
    result = await session.execute(
        select(Secret).where(Secret.id == secret_id, Secret.organization_id == organization_id)
    )
    return result.unique().scalar_one_or_none()


async def get_secrets_in_organization(
    session: AsyncSession,
    organization_id: UUID,
    secret_type: SecretKind | None = None,
    use_case: SecretUseCase | None = None,
) -> list[Secret]:
    """
    Get all ORGANIZATION-scoped secrets in an organization.
    """
    query = select(Secret).where(
        Secret.organization_id == organization_id,
        Secret.scope == SecretScope.ORGANIZATION,
    )

    if secret_type is not None:
        query = query.where(Secret.type == secret_type)

    if use_case is not None:
        query = query.where(Secret.use_case == use_case)

    result = await session.execute(query)
    return result.unique().scalars().all()


async def get_secrets_for_project(
    session: AsyncSession,
    organization_id: UUID,
    project_id: UUID,
    secret_type: SecretKind | None = None,
    use_case: SecretUseCase | None = None,
) -> list[Secret]:
    # Build base query with organization filter
    query = select(Secret).where(Secret.organization_id == organization_id)

    # Add optional filters
    if secret_type is not None:
        query = query.where(Secret.type == secret_type)

    if use_case is not None:
        query = query.where(Secret.use_case == use_case)

    # Filter for secrets associated with the project:
    # 1. Secrets in organization_secret_assignments table for this project (ORGANIZATION-scoped)
    # 2. PROJECT-scoped secrets where project_id matches (need to check via ProjectScopedSecret)
    query = query.outerjoin(
        OrganizationSecretAssignment, Secret.id == OrganizationSecretAssignment.organization_secret_id
    ).where(
        or_(
            OrganizationSecretAssignment.project_id == project_id,  # ORGANIZATION secrets assigned to project
            and_(
                Secret.scope == SecretScope.PROJECT,
                ProjectScopedSecret.project_id == project_id,  # PROJECT secrets belonging to project
            ),
        )
    )

    result = await session.execute(query)
    return result.unique().scalars().all()


async def delete_secret(session: AsyncSession, secret: Secret) -> None:
    await session.delete(secret)
    await session.flush()


async def update_secret_status(
    session: AsyncSession,
    secret: Secret,
    status: SecretStatus,
    status_reason: str | None,
    updated_at: datetime,
    updated_by: str,
) -> None:
    secret.status = status
    secret.status_reason = status_reason
    set_updated_fields(secret, updated_by, updated_at)
    await session.flush()


async def update_org_assignment_status(
    session: AsyncSession,
    org_secret_assignment: OrganizationSecretAssignment,
    status: ProjectSecretStatus,
    status_reason: str | None,
    updated_at: datetime,
    updated_by: str,
) -> None:
    org_secret_assignment.status = status
    org_secret_assignment.status_reason = status_reason
    set_updated_fields(org_secret_assignment, updated_by, updated_at)
    await session.flush()


async def get_project_scoped_secret(
    session: AsyncSession,
    organization_id: UUID,
    project_id: UUID,
    secret_id: UUID,
    use_case: SecretUseCase | None = None,
) -> Secret | None:
    query = select(ProjectScopedSecret).where(
        ProjectScopedSecret.organization_id == organization_id,
        ProjectScopedSecret.project_id == project_id,
        ProjectScopedSecret.id == secret_id,
    )
    if use_case is not None:
        query = query.where(ProjectScopedSecret.use_case == use_case)
    result = await session.execute(query)
    return result.unique().scalar_one_or_none()


async def create_project_scoped_secret(
    session: AsyncSession,
    organization_id: UUID,
    project_id: UUID,
    project_secret_in: ProjectSecretIn,
    secret_status: SecretStatus,
    creator: str,
) -> ProjectScopedSecret:
    new_project_secret = ProjectScopedSecret(
        **project_secret_in.model_dump(exclude={"scope", "manifest"}),
        organization_id=organization_id,
        project_id=project_id,
        scope=SecretScope.PROJECT,
        status=secret_status,
        created_by=creator,
        updated_by=creator,
    )

    session.add(new_project_secret)
    await session.flush()
    return new_project_secret


async def create_organization_scoped_secret(
    session: AsyncSession,
    organization_id: UUID,
    secret_in: OrganizationSecretIn,
    secret_status: SecretStatus,
    creator: str,
) -> OrganizationScopedSecret:
    new_secret = OrganizationScopedSecret(
        **secret_in.model_dump(exclude={"project_ids", "scope"}),
        organization_id=organization_id,
        scope=SecretScope.ORGANIZATION,
        status=secret_status,
        created_by=creator,
        updated_by=creator,
    )
    session.add(new_secret)
    try:
        await session.flush()
        result = await session.execute(
            select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == new_secret.id)
        )
        return result.unique().scalar_one()
    except IntegrityError as e:
        error_message = str(e)
        if "secrets_name_organization_id_key" in error_message or "name" in error_message.lower():
            raise ConflictException(f"A secret with the name '{secret_in.name}' already exists in the organization")
        raise e


async def assign_organization_secret_to_projects(
    session: AsyncSession,
    secret_id: UUID,
    project_ids: list[UUID],
    user_email: str,
) -> Secret:
    result = await session.execute(select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret_id))
    secret = result.unique().scalar_one()

    existing_project_ids = {assignment.project_id for assignment in secret.organization_secret_assignments}

    for project_id in project_ids:
        if project_id in existing_project_ids:
            continue

        assignment = OrganizationSecretAssignment(
            organization_secret_id=secret_id,
            project_id=project_id,
            status=ProjectSecretStatus.PENDING,
            created_by=user_email,
            updated_by=user_email,
        )
        session.add(assignment)

    await session.flush()
    await session.refresh(secret, attribute_names=["organization_secret_assignments"])
    return secret


async def get_secret_assignment_by_id(
    session: AsyncSession, secret_assignment_id: UUID
) -> OrganizationSecretAssignment | None:
    result = await session.execute(
        select(OrganizationSecretAssignment).where(OrganizationSecretAssignment.id == secret_assignment_id)
    )
    return result.unique().scalars().one_or_none()


async def delete_secret_assignment(session: AsyncSession, secret_assignment: OrganizationSecretAssignment) -> None:
    await session.delete(secret_assignment)
    await session.flush()


async def get_organization_scoped_secret_in_organization(
    session: AsyncSession, organization_id: UUID, secret_id: UUID
) -> OrganizationScopedSecret | None:
    """Get an organization-scoped secret by ID within an organization."""
    result = await session.execute(
        select(OrganizationScopedSecret).where(
            OrganizationScopedSecret.id == secret_id, OrganizationScopedSecret.organization_id == organization_id
        )
    )
    return result.unique().scalar_one_or_none()


async def get_organization_secret_assignment(
    session: AsyncSession, secret_id: UUID, project_id: UUID
) -> OrganizationSecretAssignment | None:
    """Get a specific organization secret assignment by secret ID and project ID"""
    stmt = select(OrganizationSecretAssignment).where(
        OrganizationSecretAssignment.organization_secret_id == secret_id,
        OrganizationSecretAssignment.project_id == project_id,
    )
    result = await session.execute(stmt)
    return result.unique().scalars().one_or_none()


async def get_secret_by_id_and_use_case(
    session: AsyncSession, organization_id: UUID, secret_id: UUID, use_case: SecretUseCase
) -> ProjectScopedSecret | OrganizationScopedSecret | None:
    result = await session.execute(
        select(Secret).where(
            Secret.id == secret_id, Secret.organization_id == organization_id, Secret.use_case == use_case
        )
    )
    return result.unique().scalar_one_or_none()


async def create_organization_secret_assignment(
    session: AsyncSession,
    secret_id: UUID,
    project_id: UUID,
    user_email: str,
) -> OrganizationSecretAssignment:
    organization_secret_assignment = OrganizationSecretAssignment(
        project_id=project_id,
        organization_secret_id=secret_id,
        status=ProjectSecretStatus.PENDING,
        created_by=user_email,
        updated_by=user_email,
    )
    session.add(organization_secret_assignment)
    await session.flush()
    await session.refresh(organization_secret_assignment)
    return organization_secret_assignment
