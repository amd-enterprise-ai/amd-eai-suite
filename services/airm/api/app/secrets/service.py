# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import UUID

import yaml
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
    SecretKind,
    SecretScope,
)

from ..clusters.models import Cluster
from ..messaging.sender import MessageSender
from ..organizations.models import Organization
from ..projects.enums import ProjectStatus
from ..projects.models import Project
from ..projects.repository import get_project_in_organization
from ..storages.repository import get_project_storages_by_project_ids_secret, get_project_storages_by_project_secret
from ..storages.service import update_project_storage_secret_status
from ..utilities.exceptions import ConflictException, NotFoundException, ValidationException
from .enums import SecretStatus, SecretUseCase
from .models import OrganizationScopedSecret, OrganizationSecretAssignment, ProjectScopedSecret
from .models import Secret as SecretModel
from .repository import (
    assign_organization_secret_to_projects,
    create_organization_scoped_secret,
    create_project_scoped_secret,
    delete_secret_assignment,
    get_organization_secret_assignment,
    get_secret_assignment_by_id,
    get_secret_in_organization,
    get_secrets_for_project,
    get_secrets_in_organization,
    update_secret_status,
)
from .repository import (
    delete_secret as delete_secret_in_db,
)
from .repository import update_org_assignment_status as update_org_assignment_status_in_db
from .repository import (
    update_secret_status as update_secret_status_in_db,
)
from .schemas import (
    OrganizationSecretIn,
    ProjectSecretIn,
    ProjectSecretsWithParentSecret,
    Secrets,
    SecretWithProjects,
)
from .utils import (
    build_project_secret_response,
    build_secret_response,
    calculate_assignment_changes,
    publish_project_secret_creation_message,
    publish_project_secret_deletion_message,
    publish_secret_deletion_message,
    resolve_secret_status,
    sanitize_external_secret_manifest,
    validate_and_patch_secret_manifest,
)


async def get_secrets_with_assigned_project_secrets(
    session: AsyncSession,
    organization: Organization,
    secret_type: SecretKind | None = None,
    use_case: SecretUseCase | None = None,
) -> Secrets:
    """
    Get all organization-scoped secrets with their project assignments.
    """
    secrets = await get_secrets_in_organization(
        session,
        organization.id,
        secret_type=secret_type,
        use_case=use_case,
    )

    return Secrets(secrets=[build_secret_response(secret) for secret in secrets])


async def get_project_secrets_in_project(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    secret_type: SecretKind | None = None,
    use_case: SecretUseCase | None = None,
) -> ProjectSecretsWithParentSecret:
    secrets = await get_secrets_for_project(
        session,
        organization.id,
        project.id,
        secret_type=secret_type,
        use_case=use_case,
    )

    return build_project_secret_response(secrets, project)


async def submit_delete_secret(
    session: AsyncSession, secret: SecretModel, user: str, message_sender: MessageSender
) -> None:
    """
    Delete a secret (either project-scoped or organization-scoped).

    This is a convenience wrapper that delegates to the appropriate deletion method
    based on the secret type.
    """
    if isinstance(secret, ProjectScopedSecret):
        await delete_project_scoped_secret(session, secret, user, message_sender)
    elif isinstance(secret, OrganizationScopedSecret):
        await delete_organization_scoped_secret(session, secret, user, message_sender)
    else:
        raise ValidationException("Unknown secret type for deletion")


async def delete_project_scoped_secret(
    session: AsyncSession, secret: ProjectScopedSecret, user: str, message_sender: MessageSender
) -> None:
    """Delete a project-scoped secret."""
    now = datetime.now(UTC)
    await update_secret_status_in_db(session, secret, SecretStatus.DELETING, None, now, user)

    await publish_secret_deletion_message(
        secret.project.cluster_id, secret.id, secret.project.name, secret.type, SecretScope.PROJECT, message_sender
    )


async def delete_organization_scoped_secret(
    session: AsyncSession, secret: OrganizationScopedSecret, user: str, message_sender: MessageSender
) -> None:
    """Delete an organization-scoped secret from all assigned projects."""
    now = datetime.now(UTC)
    await update_secret_status_in_db(session, secret, SecretStatus.DELETING, None, now, user)

    if not secret.organization_secret_assignments:
        await delete_secret_in_db(session, secret)
    else:
        # delete the secret from all projects
        for org_assignment in secret.organization_secret_assignments:
            # Set the status to DELETING for each organization assignment
            await update_org_assignment_status_in_db(
                session, org_assignment, ProjectSecretStatus.DELETING, None, now, user
            )
            # Submit a message to the cluster queue to handle deletion
            await publish_secret_deletion_message(
                org_assignment.project.cluster_id,
                org_assignment.id,
                org_assignment.project.name,
                secret.type,
                SecretScope.ORGANIZATION,
                message_sender,
            )


async def update_project_secret_assignments(
    session: AsyncSession,
    user_email: str,
    organization_id: UUID,
    org_secret: OrganizationScopedSecret,
    project_ids: list[UUID],
    message_sender: MessageSender,
) -> None:
    current_project_ids = {assignment.project_id for assignment in org_secret.organization_secret_assignments}
    new_project_ids = set(project_ids)

    to_add, to_remove = calculate_assignment_changes(current_project_ids, new_project_ids)

    if not to_add and not to_remove:
        raise ValueError("No changes in project assignments")

    if to_remove:
        await ensure_can_remove_secret_from_projects(session, list(to_remove), org_secret.id)

    await update_secret_status(
        session,
        org_secret,
        SecretStatus.PENDING,
        None,
        datetime.now(UTC),
        user_email,
    )

    if to_add:
        await add_organization_secret_assignments(
            session, organization_id, org_secret, list[UUID](to_add), user_email, message_sender
        )

    if to_remove:
        await remove_organization_secret_assignments(session, org_secret, list[UUID](to_remove), message_sender)


async def update_project_secret_status(
    session: AsyncSession, cluster: Cluster, message: ProjectSecretsUpdateMessage
) -> None:
    if message.secret_scope == SecretScope.PROJECT:
        await _update_project_scoped_secret_status(session, cluster.organization_id, message)
    # If the secret scope is not provided due to legacy reasons, we assume it is an organization-scoped secret
    elif message.secret_scope == SecretScope.ORGANIZATION or message.secret_scope is None:
        await _update_organization_scoped_secret_status(session, cluster.organization_id, message)
    else:
        logger.error(f"Unknown secret scope: {message.secret_scope}")


async def _update_project_scoped_secret_status(
    session: AsyncSession, organization_id: UUID, message: ProjectSecretsUpdateMessage
) -> None:
    """Handle status update for project-scoped secrets."""
    project_scoped_secret = await get_secret_in_organization(session, organization_id, message.project_secret_id)

    if not project_scoped_secret:
        logger.error(f"Project-scoped secret {message.project_secret_id} not found in organization {organization_id}")
        return

    if message.status == SecretStatus.DELETED:
        logger.info(
            f"Deleting secret {project_scoped_secret.name} since it was marked for deletion and criteria was met"
        )
        await delete_secret_in_db(session, project_scoped_secret)
    elif project_scoped_secret.status != message.status:
        await update_secret_status_in_db(
            session,
            project_scoped_secret,
            message.status,
            message.status_reason,
            message.updated_at,
            "system",
        )


async def _update_organization_scoped_secret_status(
    session: AsyncSession, organization_id: UUID, message: ProjectSecretsUpdateMessage
) -> None:
    secret_assignment = await get_secret_assignment_by_id(session, message.project_secret_id)

    if secret_assignment is None:
        logger.error(f"Project Secret assignment {message.project_secret_id} not found")
        return

    parent_secret = await get_secret_in_organization(session, organization_id, secret_assignment.organization_secret_id)

    if parent_secret is None:
        logger.error(f"Secret {secret_assignment.organization_secret_id} not found")
        return

    await _update_secret_assignment_status(session, secret_assignment, message)

    # Refresh secret to get updated assignments
    await session.refresh(parent_secret)

    # Update related project storages
    await _update_related_project_storages(
        session, secret_assignment.organization_secret_id, secret_assignment.project_id
    )

    # Resolve and update the overall secret status
    await _resolve_and_update_organization_secret_status(session, parent_secret, message)


async def _update_secret_assignment_status(
    session: AsyncSession, secret_assignment: OrganizationSecretAssignment, message: ProjectSecretsUpdateMessage
) -> None:
    if message.status == ProjectSecretStatus.DELETED and secret_assignment.status == ProjectSecretStatus.DELETING:
        await delete_secret_assignment(session, secret_assignment)
    elif secret_assignment.status == ProjectSecretStatus.DELETING and message.status not in (
        ProjectSecretStatus.DELETED,
        ProjectSecretStatus.DELETE_FAILED,
    ):
        # Don't update status if it's DELETING and message is not a terminal delete state
        logger.info(
            f"Skipping status update for secret_assignment {secret_assignment.id} "
            f"(current: DELETING, message: {message.status})"
        )
    else:
        await update_org_assignment_status_in_db(
            session, secret_assignment, message.status, message.status_reason, datetime.now(UTC), "system"
        )


async def _update_related_project_storages(session: AsyncSession, secret_id: UUID, project_id: UUID) -> None:
    """Update all project storages that depend on this secret."""
    project_storages = await get_project_storages_by_project_secret(session, secret_id, project_id)

    if not project_storages:
        logger.info(f"No ProjectStorages found for secret_id: {secret_id} project_id: {project_id}")
        return

    for project_storage in project_storages:
        await update_project_storage_secret_status(session, secret_id, project_storage)


async def _resolve_and_update_organization_secret_status(
    session: AsyncSession, secret: SecretModel, message: ProjectSecretsUpdateMessage
) -> None:
    """Resolve the overall status of an organization secret and update or delete it."""
    secret_status, status_reason = resolve_secret_status(secret.status, secret.organization_secret_assignments)

    if secret_status == SecretStatus.DELETED:
        logger.info(f"Deleting secret {secret.name} since it was marked for deletion and criteria was met")
        await delete_secret_in_db(session, secret)
    elif secret.status != secret_status:
        await update_secret_status_in_db(
            session,
            secret,
            secret_status,
            status_reason,
            message.updated_at,
            "system",
        )


async def ensure_can_remove_secret_from_projects(
    session: AsyncSession,
    project_ids: list[UUID],
    secret_id: UUID,
) -> None:
    project_storages = await get_project_storages_by_project_ids_secret(session, project_ids, secret_id)

    if project_storages:
        raise ValidationException(
            "Cannot remove this secret because it is still referenced by one or more storages:"
            + ", ".join(str(ps.storage.name) for ps in project_storages)
        )


async def create_project_scoped_secret_in_organization(
    session: AsyncSession,
    organization_id: UUID,
    project_id: UUID,
    user_email: str,
    secret_in: ProjectSecretIn,
    message_sender: MessageSender,
) -> SecretWithProjects:
    project = await get_project_in_organization(session, organization_id, project_id)
    if not project:
        raise NotFoundException(f"Project with ID {project_id} not found in your organization")

    manifest_dict = validate_and_patch_secret_manifest(secret_in)

    manifest_yaml = yaml.safe_dump(manifest_dict, sort_keys=False)

    secret = await create_project_scoped_secret(
        session, organization_id, project_id, secret_in, SecretStatus.PENDING, user_email
    )

    await publish_project_secret_creation_message(secret, manifest_yaml, message_sender)

    return build_secret_response(secret)


async def create_organization_scoped_secret_in_organization(
    session: AsyncSession,
    organization_id: UUID,
    user_email: str,
    secret_in: OrganizationSecretIn,
    message_sender: MessageSender,
) -> SecretWithProjects:
    manifest_dict = validate_and_patch_secret_manifest(secret_in)

    sanitized_manifest = sanitize_external_secret_manifest(manifest_dict)

    secret_in.manifest = sanitized_manifest

    status = SecretStatus.PENDING if secret_in.project_ids else SecretStatus.UNASSIGNED
    org_secret = await create_organization_scoped_secret(session, organization_id, secret_in, status, user_email)

    if secret_in.project_ids:
        org_secret = await assign_organization_secret_to_projects(
            session=session,
            secret_id=org_secret.id,
            project_ids=secret_in.project_ids,
            user_email=user_email,
        )

        for assignment in org_secret.organization_secret_assignments:
            await publish_project_secret_creation_message(
                assignment, sanitized_manifest, message_sender, parent_secret=org_secret
            )

    return build_secret_response(org_secret)


async def add_organization_secret_assignments(
    session: AsyncSession,
    organization_id: UUID,
    org_secret: OrganizationScopedSecret,
    project_ids: list[UUID],
    user_email: str,
    message_sender: MessageSender,
) -> None:
    projects = []
    for project_id in project_ids:
        project = await get_project_in_organization(session, organization_id, project_id)
        if not project:
            raise ValueError(f"Project ID {project_id} does not exist in the organization")
        elif project.status != ProjectStatus.READY:
            raise ConflictException(f"Project {project.name} is not in a READY state")
        projects.append(project)

    await assign_organization_secret_to_projects(
        session=session,
        secret_id=org_secret.id,
        project_ids=project_ids,
        user_email=user_email,
    )

    for project in projects:
        assignment = await get_organization_secret_assignment(session, org_secret.id, project.id)

        if not assignment:
            logger.warning(f"Assignment not found for secret {org_secret.id} and project {project.id}")
            continue

        await publish_project_secret_creation_message(
            assignment, org_secret.manifest, message_sender, parent_secret=org_secret
        )


async def remove_organization_secret_assignments(
    session: AsyncSession,
    org_secret: OrganizationScopedSecret,
    project_ids: list[UUID],
    message_sender: MessageSender,
) -> None:
    for project_id in project_ids:
        assignment = await get_organization_secret_assignment(session, org_secret.id, project_id)

        if not assignment:
            raise ValueError(f"Project ID {project_id} is not assigned to the secret")

        if not assignment.project:
            logger.error(f"Assignment {assignment.id} has no project loaded")
            raise ValueError(f"Project ID {project_id} data could not be loaded")

        await update_org_assignment_status_in_db(
            session,
            assignment,
            ProjectSecretStatus.DELETING,
            None,
            datetime.now(UTC),
            "system",
        )

        await publish_project_secret_deletion_message(assignment, org_secret, message_sender)
