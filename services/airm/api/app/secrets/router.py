# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..messaging.sender import MessageSender, get_message_sender
from ..organizations.models import Organization
from ..projects.models import Project
from ..projects.repository import get_project_in_organization
from ..projects.schemas import ProjectAssignments
from ..storages.repository import get_storage_by_secret_id
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException, ValidationException
from ..utilities.security import (
    ensure_platform_administrator,
    get_projects_accessible_to_user,
    get_user_email,
    get_user_organization,
)
from .repository import get_organization_scoped_secret_in_organization, get_secret_in_organization
from .schemas import SecretIn, Secrets, SecretWithProjects
from .service import (
    create_organization_scoped_secret_in_organization,
    get_secrets_with_assigned_project_secrets,
    submit_delete_secret,
    update_project_secret_assignments,
)

router = APIRouter(tags=["Secrets"])


@router.get(
    "/secrets",
    operation_id="get_secrets",
    summary="Get secrets for the user's organization",
    status_code=status.HTTP_200_OK,
    response_model=Secrets,
)
async def get_secrets(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
) -> Secrets:
    return await get_secrets_with_assigned_project_secrets(
        session,
        organization,
    )


@router.post(
    "/secrets",
    operation_id="create_secret",
    summary="Create a new secret",
    status_code=status.HTTP_200_OK,
    response_model=SecretWithProjects,
)
async def create_secret(
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    secret_in: SecretIn = Body(description="The secret to be created in the user's organization"),
) -> SecretWithProjects:
    if secret_in.project_ids:
        for project_id in secret_in.project_ids:
            project = await get_project_in_organization(session, organization.id, project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project with ID {project_id} not found in your organization.",
                )
    secret = await create_organization_scoped_secret_in_organization(
        session, organization.id, user, secret_in, message_sender
    )
    return secret


@router.delete(
    "/secrets/{secret_id}",
    operation_id="delete_secret",
    summary="Delete a secret",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_secret(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    secret_id: UUID = Path(description="The ID of the secret to be deleted"),
) -> None:
    secret = await get_secret_in_organization(session, organization.id, secret_id)
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
    status_code=status.HTTP_200_OK,
)
async def assign_secret(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    secret_id: UUID = Path(description="The ID of the secret to be assigned"),
    secret_assign: ProjectAssignments = Body(description="The list of project IDs to be assigned to the secret"),
) -> None:
    org_secret = await get_organization_scoped_secret_in_organization(session, organization.id, secret_id)

    if not org_secret:
        raise NotFoundException(f"Organization secret with ID {secret_id} not found in your organization")

    await update_project_secret_assignments(
        session, user, organization.id, org_secret, secret_assign.project_ids, message_sender
    )
