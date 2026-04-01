# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..messaging.schemas import ProjectSecretStatus, SecretKind, SecretScope
from ..utilities.exceptions import ConflictException
from ..utilities.models import set_updated_fields
from .enums import SecretStatus, SecretUseCase
from .models import OrganizationScopedSecret, OrganizationSecretAssignment, ProjectScopedSecret, Secret
from .schemas import OrganizationSecretIn


async def get_secret(session: AsyncSession, secret_id: UUID) -> Secret | None:
    result = await session.execute(select(Secret).where(Secret.id == secret_id))
    return result.unique().scalar_one_or_none()


async def get_secrets(
    session: AsyncSession, secret_type: SecretKind | None = None, use_case: SecretUseCase | None = None
) -> list[ProjectScopedSecret | OrganizationScopedSecret]:
    query = select(Secret)

    if secret_type is not None:
        query = query.where(Secret.type == secret_type)

    if use_case is not None:
        query = query.where(Secret.use_case == use_case)

    result = await session.execute(query)
    return result.unique().scalars().all()


async def get_secrets_for_project(
    session: AsyncSession,
    project_id: UUID,
    secret_type: SecretKind | None = None,
    use_case: SecretUseCase | None = None,
    scope: SecretScope | None = None,
) -> list[Secret]:
    query = select(Secret)

    if secret_type is not None:
        query = query.where(Secret.type == secret_type)

    if use_case is not None:
        query = query.where(Secret.use_case == use_case)

    if scope is not None:
        query = query.where(Secret.scope == scope)

    query = query.outerjoin(
        OrganizationSecretAssignment, Secret.id == OrganizationSecretAssignment.organization_secret_id
    ).where(
        or_(
            OrganizationSecretAssignment.project_id == project_id,
            and_(Secret.scope == SecretScope.PROJECT, ProjectScopedSecret.project_id == project_id),
        )
    )

    result = await session.execute(query)
    return result.unique().scalars().all()


async def delete_secret(session: AsyncSession, secret: Secret) -> None:
    await session.delete(secret)
    await session.flush()


async def update_project_scoped_secret_status(
    session: AsyncSession,
    secret: ProjectScopedSecret,
    status: ProjectSecretStatus,
    status_reason: str | None,
    updated_at: datetime,
    updated_by: str,
) -> None:
    secret.status = status
    secret.status_reason = status_reason
    set_updated_fields(secret, updated_by, updated_at)
    await session.flush()


async def update_org_scoped_secret_status(
    session: AsyncSession,
    secret: OrganizationScopedSecret,
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
    secret_id: UUID,
    use_case: SecretUseCase | None = None,
) -> ProjectScopedSecret | None:
    query = select(ProjectScopedSecret).where(
        ProjectScopedSecret.id == secret_id,
    )
    if use_case is not None:
        query = query.where(ProjectScopedSecret.use_case == use_case)
    result = await session.execute(query)
    return result.unique().scalar_one_or_none()


async def create_project_scoped_secret(
    session: AsyncSession,
    project_id: UUID,
    name: str,
    secret_type: SecretKind,
    status: SecretStatus,
    creator: str,
    secret_id: UUID | None = None,
    use_case: SecretUseCase | None = None,
) -> ProjectScopedSecret:
    new_project_secret = ProjectScopedSecret(
        id=secret_id,
        name=name,
        type=secret_type,
        scope=SecretScope.PROJECT,
        status=status,
        use_case=use_case,
        project_id=project_id,
        created_by=creator,
        updated_by=creator,
    )

    session.add(new_project_secret)
    await session.flush()
    return new_project_secret


async def create_organization_scoped_secret(
    session: AsyncSession, secret_in: OrganizationSecretIn, secret_status: SecretStatus, creator: str
) -> OrganizationScopedSecret:
    new_secret = OrganizationScopedSecret(
        **secret_in.model_dump(exclude={"project_ids", "scope"}),
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
        if "uq_secret_proj_name_type" in error_message or "name" in error_message.lower():
            raise ConflictException(f"A secret with the name '{secret_in.name}' already exists")
        raise e


async def assign_organization_secret_to_projects(
    session: AsyncSession,
    secret: OrganizationScopedSecret,
    project_ids: list[UUID],
    user_email: str,
) -> None:
    existing_project_ids = {assignment.project_id for assignment in secret.organization_secret_assignments}

    for project_id in project_ids:
        if project_id in existing_project_ids:
            continue

        assignment = OrganizationSecretAssignment(
            organization_secret_id=secret.id,
            project_id=project_id,
            status=ProjectSecretStatus.PENDING,
            created_by=user_email,
            updated_by=user_email,
        )
        session.add(assignment)

    await session.flush()
    await session.refresh(secret, attribute_names=["organization_secret_assignments"])


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


async def get_organization_scoped_secret(session: AsyncSession, secret_id: UUID) -> OrganizationScopedSecret | None:
    """Get an organization-scoped secret by ID."""
    result = await session.execute(select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret_id))
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
    session: AsyncSession, secret_id: UUID, use_case: SecretUseCase
) -> ProjectScopedSecret | OrganizationScopedSecret | None:
    result = await session.execute(select(Secret).where(Secret.id == secret_id, Secret.use_case == use_case))
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


async def get_organization_secrets_assigned_to_project(
    session: AsyncSession, project_id: UUID
) -> list[OrganizationScopedSecret]:
    """Get all organization-scoped secrets assigned to a specific project."""
    result = await session.execute(
        select(OrganizationScopedSecret)
        .join(
            OrganizationSecretAssignment,
            OrganizationScopedSecret.id == OrganizationSecretAssignment.organization_secret_id,
        )
        .where(OrganizationSecretAssignment.project_id == project_id)
        .distinct()
    )
    return result.unique().scalars().all()
