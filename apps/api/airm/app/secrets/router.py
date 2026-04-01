# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..messaging.sender import MessageSender, get_message_sender
from ..projects.repository import get_project_by_id
from ..projects.schemas import ProjectAssignments
from ..storages.repository import get_storage_by_secret_id
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException, ValidationException
from ..utilities.security import (
    ensure_platform_administrator,
    get_user_email,
)
from .repository import get_organization_scoped_secret, get_secret
from .schemas import OrganizationSecretIn, Secrets, SecretWithProjects
from .service import (
    create_organization_scoped_secret,
    get_secrets_with_assigned_project_secrets,
    submit_delete_secret,
    update_project_secret_assignments,
)

router = APIRouter(tags=["Secrets"])


@router.get(
    "/secrets",
    operation_id="get_secrets",
    summary="Get secrets for the user's organization",
    description="""
        List all secrets, project and organization scoped. Requires platform administrator role.
        Returns secret metadata without exposing actual secret values.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Secrets,
)
async def get_secrets(
    _: None = Depends(ensure_platform_administrator),
    session: AsyncSession = Depends(get_session),
) -> Secrets:
    return await get_secrets_with_assigned_project_secrets(
        session,
    )


@router.post(
    "/secrets",
    operation_id="create_secret",
    summary="Create a new secret",
    description="""
        Create a new organization-level secret that can be assigned to projects.
        Requires platform administrator role. Secrets are stored securely and can
        be mounted into workload containers.
    """,
    status_code=status.HTTP_200_OK,
    response_model=SecretWithProjects,
)
async def create_secret(
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(ensure_platform_administrator),
    secret_in: OrganizationSecretIn = Body(description="The secret to be created"),
) -> SecretWithProjects:
    if secret_in.project_ids:
        for project_id in secret_in.project_ids:
            project = await get_project_by_id(session, project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID {project_id} not found."
                )
    secret = await create_organization_scoped_secret(session, user, secret_in, message_sender)
    return secret


@router.delete(
    "/secrets/{secret_id}",
    operation_id="delete_secret",
    summary="Delete a secret",
    description="""
        Remove an organization-level secret. Requires platform administrator role.
        Removes all project assignments and deletes the secret from secure storage.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_secret(
    _: None = Depends(ensure_platform_administrator),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    secret_id: UUID = Path(description="The ID of the secret to be deleted"),
) -> None:
    secret = await get_secret(session, secret_id)
    if not secret:
        raise NotFoundException(f"Secret with ID {secret_id} not found in your organization")

    storage = await get_storage_by_secret_id(session, secret.id)
    if storage:
        raise ValidationException(
            f"Cannot delete secret '{secret.name}' because it is currently linked to storage '{storage.name}' (ID: {storage.id})."
        )

    await submit_delete_secret(session, secret, user, message_sender)


@router.put(
    "/secrets/{secret_id}/assign",
    operation_id="assign_secret",
    summary="Assign a secret to a project",
    description="""
        Update project assignments for a secret. Requires platform administrator role.
        Specify project IDs to grant access; projects not listed will lose access.
    """,
    status_code=status.HTTP_200_OK,
)
async def assign_secret(
    _: None = Depends(ensure_platform_administrator),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    secret_id: UUID = Path(description="The ID of the secret to be assigned"),
    secret_assign: ProjectAssignments = Body(description="The list of project IDs to be assigned to the secret"),
) -> None:
    org_secret = await get_organization_scoped_secret(session, secret_id)

    if not org_secret:
        raise NotFoundException(f"Organization secret with ID {secret_id} not found")

    await update_project_secret_assignments(session, user, org_secret, secret_assign.project_ids, message_sender)
