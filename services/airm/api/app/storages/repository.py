# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from airm.messaging.schemas import ConfigMapStatus, ProjectStorageStatus

from ..secrets.repository import ProjectSecret
from ..utilities.exceptions import ConflictException
from ..utilities.models import set_updated_fields
from .enums import StorageStatus
from .models import ProjectStorage, ProjectStorageConfigmap, Storage
from .schemas import StorageIn


async def get_storage_in_organization(session: AsyncSession, organization_id: UUID, storage_id: UUID) -> Storage | None:
    result = await session.execute(
        select(Storage).where(Storage.id == storage_id, Storage.organization_id == organization_id)
    )
    return result.unique().scalar_one_or_none()


async def get_storages_in_organization(
    session: AsyncSession, organization_id: UUID, project_id: UUID | None = None
) -> list[Storage]:
    query = select(Storage).where(Storage.organization_id == organization_id)

    if project_id is not None:
        query = (
            query.join(ProjectStorage, Storage.id == ProjectStorage.storage_id)
            .where(ProjectStorage.project_id == project_id)
            .options(
                selectinload(Storage.project_storages).selectinload(ProjectStorage.project),
                with_loader_criteria(ProjectStorage, ProjectStorage.project_id == project_id),
            )
        )
    else:
        query = query.options(selectinload(Storage.project_storages).selectinload(ProjectStorage.project))

    result = await session.execute(query)
    return result.unique().scalars().all()


async def assign_storage_to_projects(
    session: AsyncSession,
    storage_id: UUID,
    project_ids: list[UUID],
    user_email: str,
):
    for project_id in project_ids:
        project_storage = ProjectStorage(
            project_id=project_id,
            storage_id=storage_id,
            status=ProjectStorageStatus.PENDING,
            created_by=user_email,
            updated_by=user_email,
        )
        session.add(project_storage)

    await session.flush()


async def create_storage(
    session: AsyncSession,
    organization_id: UUID,
    storage_in: StorageIn,
    storage_status: StorageStatus,
    creator: str,
) -> Storage:
    new_storage = Storage(
        **storage_in.model_dump(exclude={"project_ids", "spec"}),
        organization_id=organization_id,
        status=storage_status,
        bucket_url=str(storage_in.spec.bucket_url),
        access_key_name=storage_in.spec.access_key_name,
        secret_key_name=storage_in.spec.secret_key_name,
        created_by=creator,
        updated_by=creator,
    )

    session.add(new_storage)
    try:
        await session.flush()
        return new_storage
    except IntegrityError as e:
        error_message = str(e)
        if "uq_storage_org_name" in error_message or "name" in error_message.lower():
            raise ConflictException(f"A storage with the name '{storage_in.name}' already exists in the organization")
        raise e


async def get_project_storage(session: AsyncSession, storage_id: UUID, project_id: UUID) -> ProjectStorage | None:
    result = await session.execute(
        select(ProjectStorage).where(ProjectStorage.storage_id == storage_id, ProjectStorage.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def create_project_storage(
    session: AsyncSession,
    storage_id: UUID,
    project_id: UUID,
    user_email: str,
) -> ProjectStorage:
    project_storage = ProjectStorage(
        project_id=project_id,
        storage_id=storage_id,
        status=ProjectStorageStatus.PENDING,
        created_by=user_email,
        updated_by=user_email,
    )
    session.add(project_storage)
    await session.flush()

    # Re-select with eager loading to avoid async lazy-load problems later
    result = await session.execute(
        select(ProjectStorage)
        .options(
            selectinload(ProjectStorage.project),
            selectinload(ProjectStorage.storage),
        )
        .where(ProjectStorage.id == project_storage.id)
    )
    return result.scalar_one()


async def create_project_storage_configmap(
    session: AsyncSession,
    project_storage_id: UUID,
    user_email: str,
) -> ProjectStorageConfigmap:
    project_storage_configmap = ProjectStorageConfigmap(
        project_storage_id=project_storage_id,
        status=ConfigMapStatus.ADDED,
        created_by=user_email,
        updated_by=user_email,
    )
    session.add(project_storage_configmap)
    await session.flush()
    return project_storage_configmap


async def update_storage_status(
    session: AsyncSession,
    storage: Storage,
    status: StorageStatus,
    status_reason: str | None,
    updated_by: str,
    updated_at: datetime | None = None,
):
    storage.status = status
    storage.status_reason = status_reason
    set_updated_fields(storage, updated_by, updated_at)
    await session.flush()


async def update_project_storage_configmap_status(
    session: AsyncSession,
    configmap: ProjectStorageConfigmap,
    status: ConfigMapStatus,
    status_reason: str,
    updated_by: str,
) -> None:
    configmap.status = status
    configmap.status_reason = status_reason
    set_updated_fields(configmap, updated_by)
    await session.flush()


async def get_configmap_by_project_storage_id(
    session: AsyncSession, organization_id: UUID, project_storage_id: UUID
) -> ProjectStorageConfigmap | None:
    result = await session.execute(
        select(ProjectStorageConfigmap)
        .join(ProjectStorage, ProjectStorageConfigmap.project_storage_id == ProjectStorage.id)
        .join(Storage, ProjectStorage.storage_id == Storage.id)
        .where(
            ProjectStorageConfigmap.project_storage_id == project_storage_id, Storage.organization_id == organization_id
        )
    )
    return result.scalars().first()


async def update_project_storage_status(
    session: AsyncSession,
    project_storage: ProjectStorage,
    status: ProjectStorageStatus,
    status_reason: str | None,
    updated_by: str,
    updated_at: datetime | None = None,
):
    project_storage.status = status
    project_storage.status_reason = status_reason
    set_updated_fields(project_storage, updated_by, updated_at)
    await session.flush()


async def delete_storage(session: AsyncSession, storage: Storage):
    await session.delete(storage)
    await session.flush()


async def delete_project_storage(session: AsyncSession, project_storage: ProjectStorage):
    storage = project_storage.storage

    await session.delete(project_storage)
    await session.flush()

    # Expire the cached 'project_storages' relationship so it's reloaded on next access.
    # SQLAlchemy keeps relationship collections cached in memory (identity map),
    # so even though the ProjectStorage was deleted and flushed, the old in-memory
    # list on 'storage.project_storages' still includes it until expired or refreshed.
    session.expire(storage, ["project_storages"])


async def get_storage_by_secret_id(session: AsyncSession, secret_id: UUID) -> Storage | None:
    result = await session.execute(select(Storage).where(Storage.secret_id == secret_id))
    return result.scalars().first()


async def get_project_storage_by_id(session: AsyncSession, project_storage_id: UUID) -> ProjectStorage | None:
    result = await session.execute(
        select(ProjectStorage)
        .options(selectinload(ProjectStorage.storage))
        .where(ProjectStorage.id == project_storage_id)
    )
    return result.scalar_one_or_none()


async def get_project_storages_by_project_secret(
    session: AsyncSession, project_secret: ProjectSecret
) -> list[ProjectStorage]:
    result = await session.execute(
        select(ProjectStorage)
        .join(Storage, ProjectStorage.storage_id == Storage.id)
        .where(Storage.secret_id == project_secret.secret_id, ProjectStorage.project_id == project_secret.project_id)
    )
    return result.scalars().all()


# Retrieve all ProjectStorage entries for a list of project IDs, including their associated Storage details
async def get_project_storages_by_project_ids_secret(
    session: AsyncSession, project_ids: list[UUID], secret_id: UUID
) -> list[ProjectStorage]:
    if not project_ids:
        return []

    result = await session.execute(
        select(ProjectStorage)
        .join(Storage, ProjectStorage.storage_id == Storage.id)
        .options(selectinload(ProjectStorage.storage))
        .where(
            ProjectStorage.project_id.in_(project_ids),
            Storage.secret_id == secret_id,
        )
        .order_by(ProjectStorage.project_id)
    )
    return result.scalars().all()
