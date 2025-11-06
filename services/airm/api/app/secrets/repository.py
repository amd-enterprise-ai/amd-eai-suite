# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from airm.messaging.schemas import ProjectSecretStatus

from ..utilities.exceptions import ConflictException, ValidationException
from .enums import SecretScope, SecretStatus, SecretType, SecretUseCase
from .models import ProjectSecret, Secret
from .schemas import SecretIn


async def get_secret_in_organization(session: AsyncSession, organization_id: UUID, secret_id: UUID) -> Secret | None:
    result = await session.execute(
        select(Secret).where(Secret.id == secret_id, Secret.organization_id == organization_id)
    )
    return result.unique().scalar_one_or_none()


async def get_secrets_in_organization(
    session: AsyncSession,
    organization_id: UUID,
    project_id: UUID | None = None,
    secret_type: SecretType | None = None,
    use_case: SecretUseCase | None = None,
) -> list[Secret]:
    query = select(Secret).where(Secret.organization_id == organization_id)

    if secret_type is not None:
        query = query.where(Secret.type == secret_type)

    if use_case is not None:
        query = query.where(Secret.use_case == use_case)

    if project_id is not None:
        query = (
            query.join(ProjectSecret, Secret.id == ProjectSecret.secret_id)
            .where(ProjectSecret.project_id == project_id)
            .options(
                selectinload(Secret.project_secrets).selectinload(ProjectSecret.project),
                with_loader_criteria(ProjectSecret, ProjectSecret.project_id == project_id),
            )
        )
    else:
        query = query.options(selectinload(Secret.project_secrets).selectinload(ProjectSecret.project))

    result = await session.execute(query)
    return result.unique().scalars().all()


async def create_secret(
    session: AsyncSession,
    organization_id: UUID,
    secret_in: SecretIn,
    secret_status: SecretStatus,
    creator: str,
) -> Secret:
    new_secret = Secret(
        **secret_in.model_dump(exclude={"project_ids"}),
        organization_id=organization_id,
        status=secret_status,
        created_by=creator,
        updated_by=creator,
    )

    session.add(new_secret)
    try:
        await session.flush()
        return new_secret
    except IntegrityError as e:
        error_message = str(e)
        if "secrets_name_organization_id_key" in error_message or "name" in error_message.lower():
            raise ConflictException(f"A secret with the name '{secret_in.name}' already exists in the organization")
        raise e


async def delete_secret(session: AsyncSession, secret: Secret):
    await session.delete(secret)
    await session.flush()


async def assign_secret_to_projects(
    session: AsyncSession,
    secret_id: UUID,
    project_ids: list[UUID],
    user_email: str,
) -> Secret:
    result = await session.execute(
        select(Secret)
        .options(selectinload(Secret.project_secrets).selectinload(ProjectSecret.project))
        .where(Secret.id == secret_id)
    )
    secret = result.scalar_one()

    if secret.scope == SecretScope.PROJECT:
        if len(project_ids) > 1:
            raise ValidationException("Project-scoped secrets can only be assigned to a single project.")
        existing_project_ids = {ps.project_id for ps in secret.project_secrets}
        if existing_project_ids and project_ids:
            target = project_ids[0]
            if target not in existing_project_ids:
                raise ValidationException("Project-scoped secrets cannot be reassigned to another project.")

    for project_id in project_ids:
        project_secret = ProjectSecret(
            project_id=project_id,
            secret_id=secret_id,
            status=ProjectSecretStatus.PENDING,
            created_by=user_email,
            updated_by=user_email,
        )
        session.add(project_secret)

    await session.flush()

    await session.refresh(secret, attribute_names=["project_secrets"])
    return secret


async def create_project_secret(
    session: AsyncSession,
    secret_id: UUID,
    project_id: UUID,
    user_email: str,
) -> ProjectSecret:
    project_secret = ProjectSecret(
        project_id=project_id,
        secret_id=secret_id,
        status=ProjectSecretStatus.PENDING,
        created_by=user_email,
        updated_by=user_email,
    )
    session.add(project_secret)
    await session.flush()

    # Re-select with eager loading to avoid async lazy-load problems later
    result = await session.execute(
        select(ProjectSecret)
        .options(
            selectinload(ProjectSecret.project),
            selectinload(ProjectSecret.secret),
        )
        .where(ProjectSecret.id == project_secret.id)
    )
    return result.scalar_one()


async def update_secret_status(
    session: AsyncSession,
    secret: Secret,
    status: SecretStatus,
    status_reason: str | None,
    updated_at: datetime,
    updated_by: str,
):
    secret.status = status
    secret.status_reason = status_reason
    secret.updated_at = updated_at
    secret.updated_by = updated_by
    await session.flush()


async def update_project_secret_status(
    session: AsyncSession,
    project_secret: ProjectSecret,
    status: ProjectSecretStatus,
    status_reason: str | None,
    updated_at: datetime,
    updated_by: str,
):
    project_secret.status = status
    project_secret.status_reason = status_reason
    project_secret.updated_at = updated_at
    project_secret.updated_by = updated_by
    await session.flush()


async def delete_project_secret(session: AsyncSession, project_secret: ProjectSecret):
    await session.delete(project_secret)
    await session.flush()


async def get_project_secret(session: AsyncSession, secret_id: UUID, project_id: UUID) -> ProjectSecret | None:
    result = await session.execute(
        select(ProjectSecret)
        .options(selectinload(ProjectSecret.secret), selectinload(ProjectSecret.project))
        .where(ProjectSecret.secret_id == secret_id, ProjectSecret.project_id == project_id)
    )

    return result.scalar_one_or_none()


async def get_project_secret_by_id(session: AsyncSession, project_secret_id: UUID) -> ProjectSecret | None:
    result = await session.execute(select(ProjectSecret).where(ProjectSecret.id == project_secret_id))
    return result.scalar_one_or_none()


async def get_project_scoped_secret_by_id(
    session: AsyncSession,
    project_id: UUID,
    secret_id: UUID,
    use_case: SecretUseCase | None = None,
) -> Secret | None:
    query = (
        select(Secret)
        .join(ProjectSecret, ProjectSecret.secret_id == Secret.id)
        .where(
            ProjectSecret.project_id == project_id,
            Secret.id == secret_id,
        )
    )
    if use_case is not None:
        query = query.where(Secret.use_case == use_case)
    result = await session.execute(query)
    return result.unique().scalar_one_or_none()
