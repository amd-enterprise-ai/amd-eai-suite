# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..messaging.sender import MessageSender, get_message_sender
from ..organizations.models import Organization
from ..projects.schemas import ProjectAssignments
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException
from ..utilities.security import (
    ensure_platform_administrator,
    get_user_email,
    get_user_organization,
)
from .repository import get_storage_in_organization
from .schemas import StorageIn, Storages, StorageWithProjects
from .service import (
    create_storage_in_organization,
    get_storages_with_assigned_project_storages,
    submit_delete_storage,
    update_project_storage_assignments,
)

router = APIRouter(tags=["Storages"])


@router.get(
    "/storages",
    operation_id="get_storages",
    summary="Get storages for the user's organization",
    status_code=status.HTTP_200_OK,
    response_model=Storages,
)
async def get_storages(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
) -> Storages:
    return await get_storages_with_assigned_project_storages(session, organization)


@router.post(
    "/storages",
    operation_id="create_storage",
    summary="Create a new storage",
    status_code=status.HTTP_200_OK,
    response_model=StorageWithProjects,
)
async def create_storage(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    storage_in: StorageIn = Body(description="The storage to be created in the user's organization"),
) -> StorageWithProjects:
    storage = await create_storage_in_organization(session, organization.id, user, storage_in, message_sender)
    return storage


@router.delete(
    "/storages/{storage_id}",
    operation_id="delete_storage",
    summary="Delete a storage",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_storage(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    storage_id: UUID = Path(description="The ID of the secret to be deleted"),
) -> None:
    storage = await get_storage_in_organization(session, organization.id, storage_id)

    if not storage:
        raise NotFoundException(f"Storage with ID {storage_id} not found in your organization")

    await submit_delete_storage(session, storage, user, message_sender)


@router.put(
    "/storages/{storage_id}/assign",
    operation_id="assign_storage",
    summary="Assign a storage to a project",
    status_code=status.HTTP_200_OK,
)
async def assign_storage(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    storage_id: UUID = Path(description="The ID of the storage to be assigned"),
    storage_assign: ProjectAssignments = Body(description="The list of project IDs to be assigned to the storage"),
) -> None:
    storage = await get_storage_in_organization(session, organization.id, storage_id)

    if not storage:
        raise NotFoundException(f"Storage with ID {storage_id} not found in your organization")

    await update_project_storage_assignments(
        session, user, organization.id, storage, storage_assign.project_ids, message_sender
    )
