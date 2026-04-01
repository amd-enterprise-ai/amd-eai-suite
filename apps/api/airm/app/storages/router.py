# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..messaging.sender import MessageSender, get_message_sender
from ..projects.schemas import ProjectAssignments
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException
from ..utilities.security import (
    ensure_platform_administrator,
    get_user_email,
)
from .repository import get_storage_by_id
from .schemas import StorageIn, Storages, StorageWithProjects
from .service import create_storage as create_storage_in_db
from .service import (
    get_storages_with_assigned_project_storages,
    submit_delete_storage,
    update_project_storage_assignments,
)

router = APIRouter(tags=["Storages"])


@router.get(
    "/storages",
    operation_id="get_storages",
    summary="Get storages in the system",
    description="""
        List all organization-level storage volumes. Requires platform administrator role.
        Returns storage metadata including name, type, and project assignments.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Storages,
)
async def get_storages(
    _: None = Depends(ensure_platform_administrator),
    session: AsyncSession = Depends(get_session),
) -> Storages:
    return await get_storages_with_assigned_project_storages(session)


@router.post(
    "/storages",
    operation_id="create_storage",
    summary="Create a new storage",
    description="""
        Create a new organization-level storage volume that can be assigned to projects.
        Requires platform administrator role. Storage can be mounted into workload containers
        for persistent data access.
    """,
    status_code=status.HTTP_200_OK,
    response_model=StorageWithProjects,
)
async def create_storage(
    _: None = Depends(ensure_platform_administrator),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    storage_in: StorageIn = Body(description="The storage to be created"),
) -> StorageWithProjects:
    storage = await create_storage_in_db(session, user, storage_in, message_sender)
    return storage


@router.delete(
    "/storages/{storage_id}",
    operation_id="delete_storage",
    summary="Delete a storage",
    description="""
        Remove an organization-level storage volume. Requires platform administrator role.
        Removes all project assignments and deletes the storage configuration.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_storage(
    _: None = Depends(ensure_platform_administrator),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    storage_id: UUID = Path(description="The ID of the storage to be deleted"),
) -> None:
    storage = await get_storage_by_id(session, storage_id)

    if not storage:
        raise NotFoundException(f"Storage with ID {storage_id} not found")

    await submit_delete_storage(session, storage, user, message_sender)


@router.put(
    "/storages/{storage_id}/assign",
    operation_id="assign_storage",
    summary="Assign a storage to a project",
    description="""
        Update project assignments for a storage volume. Requires platform administrator role.
        Specify project IDs to grant access; projects not listed will lose access.
    """,
    status_code=status.HTTP_200_OK,
)
async def assign_storage(
    _: None = Depends(ensure_platform_administrator),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    storage_id: UUID = Path(description="The ID of the storage to be assigned"),
    storage_assign: ProjectAssignments = Body(description="The list of project IDs to be assigned to the storage"),
) -> None:
    storage = await get_storage_by_id(session, storage_id)

    if not storage:
        raise NotFoundException(f"Storage with ID {storage_id} not found")

    await update_project_storage_assignments(session, user, storage, storage_assign.project_ids, message_sender)
