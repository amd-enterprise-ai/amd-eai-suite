# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    ConfigMapStatus,
    ProjectS3StorageCreateMessage,
    ProjectSecretsCreateMessage,
    ProjectStorageDeleteMessage,
    ProjectStorageStatus,
    ProjectStorageUpdateMessage,
)

from ..clusters.models import Cluster
from ..messaging.publisher import submit_message_to_cluster_queue
from ..organizations.models import Organization
from ..projects.models import Project
from ..projects.schemas import ProjectResponse
from ..secrets.repository import create_project_secret, get_project_secret
from ..secrets.utils import map_secret_type_to_component_kind
from ..utilities.exceptions import ConflictException, NotFoundException
from .enums import StorageStatus
from .models import ProjectStorage as ProjectStorageModel
from .models import Storage as StorageModel
from .repository import (
    assign_storage_to_projects,
    create_project_storage_configmap,
    delete_project_storage,
    get_configmap_by_project_storage_id,
    get_project_storage,
    get_project_storage_by_id,
    get_storage_by_secret_id,
    get_storage_in_organization,
    get_storages_in_organization,
    update_project_storage_configmap_status,
    update_project_storage_status,
)
from .repository import create_storage as create_storage_in_db
from .repository import delete_storage as delete_storage_in_db
from .repository import update_project_storage_status as update_project_storage_status_in_db
from .repository import update_storage_status as update_storage_status_in_db
from .schemas import ProjectStorage as ProjectStorageSchema
from .schemas import (
    ProjectStoragesWithParentStorage,
    ProjectStorageWithParentStorage,
    StorageIn,
    StorageResponse,
    Storages,
    StorageWithProjects,
)
from .utils import resolve_project_storage_composite_status, resolve_storage_status, verify_projects_ready


async def get_storages_with_assigned_project_storages(
    session: AsyncSession, organization: Organization, project: ProjectResponse = None
) -> Storages:
    storages = await get_storages_in_organization(session, organization.id, project.id if project is not None else None)

    return Storages(
        storages=[
            StorageWithProjects(
                id=storage.id,
                name=storage.name,
                type=storage.type,
                secret_id=storage.secret_id,
                scope=storage.scope,
                status=storage.status,
                status_reason=storage.status_reason,
                created_at=storage.created_at,
                updated_at=storage.updated_at,
                created_by=storage.created_by,
                updated_by=storage.updated_by,
                project_storages=[
                    ProjectStorageSchema(
                        id=ps.id,
                        project_id=ps.project_id,
                        project_name=ps.project.name if ps.project else None,
                        status=ps.status,
                        status_reason=ps.status_reason,
                        created_at=ps.created_at,
                        updated_at=ps.updated_at,
                        created_by=ps.created_by,
                        updated_by=ps.updated_by,
                    )
                    for ps in storage.project_storages
                ],
            )
            for storage in storages
        ]
    )


async def get_project_storages_in_project(
    session: AsyncSession, organization: Organization, project: Project
) -> ProjectStoragesWithParentStorage:
    storages = await get_storages_in_organization(session, organization.id, project.id)

    project_storages = []
    for storage in storages:
        for ps in storage.project_storages:
            if ps:  # Only include if ps in secret.project_secrets is satisfied
                project_storages.append(
                    ProjectStorageWithParentStorage(
                        id=ps.id,
                        created_at=ps.created_at,
                        updated_at=ps.updated_at,
                        created_by=ps.created_by,
                        updated_by=ps.updated_by,
                        project_id=ps.project.id if ps.project else None,
                        project_name=ps.project.name if ps.project else None,
                        status=ps.status,
                        status_reason=ps.status_reason,
                        storage=StorageResponse.model_validate(storage),
                    )
                )
    return ProjectStoragesWithParentStorage(project_storages=project_storages)


async def create_storage_in_organization(
    session: AsyncSession,
    organization_id: UUID,
    user_email: str,
    storage_in: StorageIn,
) -> StorageWithProjects:
    initial_status = StorageStatus.PENDING if storage_in.project_ids else StorageStatus.UNASSIGNED
    storage = await create_storage_in_db(session, organization_id, storage_in, initial_status, user_email)

    if storage_in.project_ids:
        # verify all projects exist and are in the ready state
        await verify_projects_ready(session, organization_id, storage_in.project_ids)

        for pid in storage_in.project_ids:
            # Ensure the project secret exists
            project_secret = await ensure_project_secret_exists(session, storage_in.secret_id, pid, user_email)
            ps = await _assign_and_get_project_storage(session, storage.id, pid, user_email)
            await _publish_storage_create(ps, storage, project_secret)

    await session.refresh(storage)

    return StorageWithProjects(
        id=storage.id,
        name=storage.name,
        type=storage.type,
        secret_id=storage.secret_id,
        scope=storage.scope,
        status=storage.status,
        status_reason=storage.status_reason,
        created_at=storage.created_at,
        updated_at=storage.updated_at,
        created_by=storage.created_by,
        updated_by=storage.updated_by,
        project_storages=[
            ProjectStorageSchema(
                id=ps.id,
                project_id=ps.project_id,
                project_name=ps.project.name if ps.project else None,
                status=ps.status,
                status_reason=ps.status_reason,
                created_at=ps.created_at,
                updated_at=ps.updated_at,
                created_by=ps.created_by,
                updated_by=ps.updated_by,
            )
            for ps in storage.project_storages
        ],
    )


async def submit_delete_storage(session: AsyncSession, storage: StorageModel, user: str):
    if storage.status == StorageStatus.PENDING:
        raise ConflictException("Storage is in PENDING state and cannot be deleted")
    elif storage.status == StorageStatus.DELETING:
        raise ConflictException("Storage is already marked for deletion")

    await update_storage_status_in_db(session, storage, StorageStatus.DELETING, None, user)

    if not storage.project_storages:
        await delete_storage_in_db(session, storage)
    else:
        for project_storage in storage.project_storages:
            # Set the status to DELETING for each project storage
            await update_project_storage_status_in_db(
                session, project_storage, ProjectStorageStatus.DELETING, None, user
            )

            # Submit a message to the cluster queue to handle deletion
            message = ProjectStorageDeleteMessage(
                message_type="project_storage_delete",
                project_storage_id=project_storage.id,
                project_name=project_storage.project.name,
            )

            await submit_message_to_cluster_queue(project_storage.project.cluster_id, message)


async def submit_delete_project_storage(
    session: AsyncSession, organization_id: UUID, project_storage: ProjectStorageModel, user: str
):
    if project_storage.status == ProjectStorageStatus.DELETING:
        raise ConflictException("Project Storage is already marked for deletion")

    parent_storage = await get_storage_in_organization(session, organization_id, project_storage.storage_id)
    if not parent_storage:
        raise NotFoundException("Storage not found")

    # update the project storage status to PENDING state to indcate project unassignment is in progress
    await update_storage_status_in_db(session, parent_storage, StorageStatus.PENDING, None, user, datetime.now(UTC))

    await update_project_storage_status_in_db(
        session, project_storage, ProjectStorageStatus.DELETING, None, user, datetime.now(UTC)
    )

    # Submit a message to the cluster queue to handle deletion
    message = ProjectStorageDeleteMessage(
        message_type="project_storage_delete",
        project_storage_id=project_storage.id,
        project_name=project_storage.project.name,
    )
    await submit_message_to_cluster_queue(project_storage.project.cluster_id, message)


async def update_project_storage_assignments(
    session: AsyncSession, user_email: str, organization_id: UUID, storage: StorageModel, project_ids: list[UUID]
) -> None:
    current_project_ids = {ps.project_id for ps in storage.project_storages}
    new_project_ids = set(project_ids)

    to_add = new_project_ids - current_project_ids
    to_remove = current_project_ids - new_project_ids

    if not to_add and not to_remove:
        raise ValueError("No changes in project assignments")

    await update_storage_status_in_db(
        session,
        storage,
        StorageStatus.PENDING,
        None,
        user_email,
    )

    # Send create messages for new project assignments
    if to_add:
        await assign_projects_to_storage(session, organization_id, storage, list(to_add), user_email)

    # Send delete messages for removed project assignments
    for pid in to_remove:
        project_storage = await get_project_storage(session, storage.id, pid)

        if not project_storage or not project_storage.project:
            raise ValueError(f"Project ID {pid} is not assigned to the storage")

        await update_project_storage_status_in_db(
            session, project_storage, ProjectStorageStatus.DELETING, None, "system"
        )
        delete_message = ProjectStorageDeleteMessage(
            message_type="project_storage_delete",
            project_storage_id=project_storage.id,
            project_name=project_storage.project.name,
        )
        await submit_message_to_cluster_queue(project_storage.project.cluster_id, delete_message)


# Ensure the project secret exists, creating it if necessary and publishing a creation message to the cluster queue
async def ensure_project_secret_exists(
    session: AsyncSession,
    secret_id: UUID,
    project_id: UUID,
    user_email: str,
):
    project_secret = await get_project_secret(session, secret_id, project_id)

    if not project_secret:
        project_secret = await create_project_secret(session, secret_id, project_id, user_email)

        message = ProjectSecretsCreateMessage(
            message_type="project_secrets_create",
            project_name=project_secret.project.name,
            project_secret_id=project_secret.id,
            secret_name=project_secret.secret.name,
            manifest=project_secret.secret.manifest,
            secret_type=map_secret_type_to_component_kind(project_secret.secret.type),
        )
        await submit_message_to_cluster_queue(project_secret.project.cluster_id, message)

    return project_secret


async def _assign_and_get_project_storage(
    session: AsyncSession,
    storage_id: UUID,
    project_id: UUID,
    user_email: str,
):
    await assign_storage_to_projects(
        session=session,
        storage_id=storage_id,
        project_ids=[project_id],
        user_email=user_email,
    )
    ps = await get_project_storage(session, storage_id, project_id)

    if not ps:
        raise ConflictException(f"Failed to create project storage for project {project_id}")

    await create_project_storage_configmap(
        session=session,
        project_storage_id=ps.id,
        user_email=user_email,
    )

    return ps


async def assign_projects_to_storage(session, organization_id, storage, project_ids, user_email):
    await verify_projects_ready(session, organization_id, project_ids)

    for pid in project_ids:
        project_secret = await ensure_project_secret_exists(session, storage.secret_id, pid, user_email)
        ps = await _assign_and_get_project_storage(session, storage.id, pid, user_email)
        await _publish_storage_create(ps, storage, project_secret)


async def _publish_storage_create(project_storage, storage, project_secret):
    msg = ProjectS3StorageCreateMessage(
        message_type="project_s3_storage_create",
        project_storage_id=project_storage.id,
        project_name=project_storage.project.name,
        storage_name=storage.name,
        secret_name=project_secret.secret.name,
        bucket_url=storage.bucket_url,
        access_key_name=storage.access_key_name,
        secret_key_name=storage.secret_key_name,
    )
    await submit_message_to_cluster_queue(project_storage.project.cluster_id, msg)


async def update_configmap_status(
    session: AsyncSession, cluster: Cluster, message: ProjectStorageUpdateMessage
) -> None:
    configmap = await get_configmap_by_project_storage_id(session, cluster.organization_id, message.project_storage_id)
    if not configmap:
        raise NotFoundException(
            f"ProjectStorageConfigmap for project_storage_id {message.project_storage_id} not found."
        )

    project_storage = await get_project_storage_by_id(session, message.project_storage_id)
    if not project_storage:
        raise NotFoundException(f"ProjectStorage with id {message.project_storage_id} not found.")

    if message.status == ConfigMapStatus.DELETED:
        await delete_project_storage(session, project_storage)
        await update_storage_overall_status(session, cluster.organization_id, project_storage.storage_id)
        return

    await update_project_storage_configmap_status(session, configmap, message.status, message.status_reason, "system")

    await update_project_storage_composite_status(session, cluster.organization_id, project_storage)


async def update_project_storage_secret_status(
    session: AsyncSession, secret_id: UUID, project_storage: ProjectStorageModel
) -> None:
    storage = await get_storage_by_secret_id(session, secret_id)
    if not storage:
        raise NotFoundException(f"Storage with secret_id {secret_id} not found.")

    await update_project_storage_composite_status(session, storage.organization_id, project_storage)


async def update_project_storage_composite_status(
    session: AsyncSession, organization_id: UUID, project_storage: ProjectStorageModel
) -> None:
    configmap = await get_configmap_by_project_storage_id(session, organization_id, project_storage.id)
    if not configmap:
        raise NotFoundException(f"ProjectStorageConfigmap for project_storage_id {project_storage.id} not found.")

    await session.refresh(project_storage, ["storage"])
    secret_id = project_storage.storage.secret_id

    project_secret = await get_project_secret(session, secret_id, project_storage.project_id)
    if not project_secret:
        raise NotFoundException(
            f"ProjectSecret for secret_id {secret_id} and project_id {project_storage.project_id} not found."
        )

    composite_status, composite_reason = await resolve_project_storage_composite_status(
        configmap, project_secret, project_storage
    )

    await update_project_storage_status(session, project_storage, composite_status, composite_reason, "system")
    await update_storage_overall_status(session, organization_id, project_storage.storage_id)


async def update_storage_overall_status(session: AsyncSession, organization_id: UUID, storage_id: UUID) -> None:
    storage = await get_storage_in_organization(session, organization_id, storage_id)

    if storage is None:
        logger.error(f"Storage {storage_id} not found")
        return

    storage_status, storage_reason = resolve_storage_status(storage.status, storage.project_storages)
    if storage_status == StorageStatus.DELETED:
        logger.info(f"Deleting storage {storage.name} since it was marked for deletion and criteria was met")
        await delete_storage_in_db(session, storage)
        return
    elif storage.status != storage_status:
        await update_storage_status_in_db(
            session,
            storage,
            storage_status,
            storage_reason,
            "system",
        )
