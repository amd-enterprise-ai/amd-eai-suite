# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import UUID

import yaml
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
)
from airm.secrets.utils import validate_external_secret_manifest, validate_kubernetes_secret_manifest

from ..clusters.models import Cluster
from ..messaging.publisher import submit_message_to_cluster_queue
from ..organizations.models import Organization
from ..projects.enums import ProjectStatus
from ..projects.models import Project
from ..projects.repository import get_project_in_organization
from ..storages.repository import get_project_storages_by_project_ids_secret, get_project_storages_by_project_secret
from ..storages.service import update_project_storage_secret_status
from ..utilities.exceptions import ConflictException, NotFoundException, ValidationException
from .enums import SecretScope, SecretStatus, SecretType, SecretUseCase
from .models import ProjectSecret as ProjectSecretModel
from .models import Secret as SecretModel
from .repository import (
    assign_secret_to_projects,
    get_project_scoped_secret_by_id,
    get_project_secret,
    get_project_secret_by_id,
    get_secret_in_organization,
    get_secrets_in_organization,
)
from .repository import (
    create_secret as create_secret_in_db,
)
from .repository import (
    delete_project_secret as delete_project_secret_in_db,
)
from .repository import (
    delete_secret as delete_secret_in_db,
)
from .repository import (
    update_project_secret_status as update_project_secret_status_in_db,
)
from .repository import (
    update_secret_status as update_secret_status_in_db,
)
from .schemas import ProjectSecret as ProjectSecretSchema
from .schemas import (
    ProjectSecretsWithParentSecret,
    ProjectSecretWithParentSecret,
    SecretIn,
    SecretResponse,
    Secrets,
    SecretWithProjects,
)
from .utils import (
    add_use_case_label_to_manifest,
    map_secret_type_to_component_kind,
    resolve_secret_status,
    sanitize_external_secret_manifest,
)


def _add_huggingface_labels_to_manifest(manifest_str: str, use_case: str) -> str:
    """
    Validates a Kubernetes Secret manifest and adds use-case labels for Hugging Face tokens.

    Args:
        manifest_str: YAML string containing the Kubernetes Secret manifest
        use_case: The use case value (e.g., "HUGGING_FACE")

    Returns:
        YAML string with validated manifest and added labels

    Raises:
        ValidationException: If manifest validation fails
    """
    try:
        # Validate the Kubernetes Secret manifest structure
        manifest = validate_kubernetes_secret_manifest(manifest_str)
    except Exception as exc:
        raise ValidationException(f"Invalid Kubernetes Secret manifest: {exc}") from exc

    # Add use-case label
    manifest = add_use_case_label_to_manifest(manifest, use_case)

    return yaml.safe_dump(manifest, sort_keys=False)


def _prepare_secret_input(secret_in: SecretIn) -> tuple[str, str]:
    """Validate secret payload and return (cluster_manifest, sanitized_manifest)."""
    if not secret_in.manifest:
        raise ValidationException("Manifest must be provided for secret creation.")
    if secret_in.use_case == SecretUseCase.HUGGING_FACE and secret_in.type == SecretType.KUBERNETES_SECRET:
        labeled_manifest = _add_huggingface_labels_to_manifest(secret_in.manifest, secret_in.use_case)
        return labeled_manifest, ""
    try:
        parsed_manifest = validate_external_secret_manifest(secret_in.manifest)
    except Exception as e:
        raise ValidationException(f"Invalid YAML manifest: {str(e)}")

    sanitized_manifest = sanitize_external_secret_manifest(parsed_manifest)
    return "", sanitized_manifest


async def get_secrets_with_assigned_project_secrets(
    session: AsyncSession,
    organization: Organization,
    project: Project | None = None,
    secret_type: SecretType | None = None,
    use_case: SecretUseCase | None = None,
) -> Secrets:
    secrets = await get_secrets_in_organization(
        session,
        organization.id,
        project.id if project is not None else None,
        secret_type=secret_type,
        use_case=use_case,
    )

    return Secrets(
        secrets=[
            SecretWithProjects(
                id=secret.id,
                created_at=secret.created_at,
                updated_at=secret.updated_at,
                created_by=secret.created_by,
                updated_by=secret.updated_by,
                name=secret.name,
                type=secret.type,
                scope=secret.scope,
                status=secret.status,
                status_reason=secret.status_reason,
                use_case=secret.use_case,
                project_secrets=[
                    ProjectSecretSchema(
                        id=ps.id,
                        created_at=ps.created_at,
                        updated_at=ps.updated_at,
                        created_by=ps.created_by,
                        updated_by=ps.updated_by,
                        project_id=ps.project_id,
                        project_name=ps.project.name if ps.project else None,
                        status=ps.status,
                        status_reason=ps.status_reason,
                    )
                    for ps in secret.project_secrets
                ],
            )
            for secret in secrets
        ]
    )


async def get_project_secrets_in_project(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    secret_type: SecretType | None = None,
    use_case: SecretUseCase | None = None,
) -> ProjectSecretsWithParentSecret:
    secrets = await get_secrets_in_organization(
        session,
        organization.id,
        project.id,
        secret_type=secret_type,
        use_case=use_case,
    )

    project_secrets = []
    for secret in secrets:
        for ps in secret.project_secrets:
            if ps:  # Only include if ps in secret.project_secrets is satisfied
                project_secrets.append(
                    ProjectSecretWithParentSecret(
                        id=ps.id,
                        created_at=ps.created_at,
                        updated_at=ps.updated_at,
                        created_by=ps.created_by,
                        updated_by=ps.updated_by,
                        project_id=ps.project.id if ps.project else None,
                        project_name=ps.project.name if ps.project else None,
                        status=ps.status,
                        status_reason=ps.status_reason,
                        secret=SecretResponse(
                            id=secret.id,
                            created_at=secret.created_at,
                            updated_at=secret.updated_at,
                            created_by=secret.created_by,
                            updated_by=secret.updated_by,
                            name=secret.name,
                            type=secret.type,
                            scope=secret.scope,
                            status=secret.status,
                            status_reason=secret.status_reason,
                            use_case=secret.use_case,
                        ),
                    )
                )
    return ProjectSecretsWithParentSecret(project_secrets=project_secrets)


async def create_secret_in_organization(
    session: AsyncSession,
    organization_id: UUID,
    user_email: str,
    secret_in: SecretIn,
) -> SecretWithProjects:
    cluster_manifest: str | None = None

    cluster_manifest, sanitized_manifest = _prepare_secret_input(secret_in)
    secret_in.manifest = sanitized_manifest

    # Persist the secret in the database
    if secret_in.project_ids:
        secret = await create_secret_in_db(session, organization_id, secret_in, SecretStatus.PENDING, user_email)
    else:
        secret = await create_secret_in_db(session, organization_id, secret_in, SecretStatus.UNASSIGNED, user_email)

    if secret_in.project_ids:
        # Assign to projects and fetch secret with relationships
        secret = await assign_secret_to_projects(
            session=session,
            secret_id=secret.id,
            project_ids=secret_in.project_ids,
            user_email=user_email,
        )

        # Send create messages to each cluster
        for project_secret in secret.project_secrets:
            message = ProjectSecretsCreateMessage(
                message_type="project_secrets_create",
                project_name=project_secret.project.name,
                project_secret_id=project_secret.id,
                secret_name=secret.name,
                manifest=cluster_manifest or secret.manifest,
                secret_type=map_secret_type_to_component_kind(secret.type),
            )
            await submit_message_to_cluster_queue(project_secret.project.cluster_id, message)

    else:
        await session.refresh(secret)

    return SecretWithProjects(
        id=secret.id,
        name=secret.name,
        type=secret.type,
        scope=secret.scope,
        status=secret.status,
        status_reason=secret.status_reason,
        use_case=secret.use_case,
        created_at=secret.created_at,
        updated_at=secret.updated_at,
        created_by=secret.created_by,
        updated_by=secret.updated_by,
        project_secrets=[
            ProjectSecretSchema(
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
            for ps in secret.project_secrets
        ],
    )


async def submit_delete_secret(session: AsyncSession, secret: SecretModel, user: str):
    if secret.status == SecretStatus.PENDING:
        raise ConflictException("Secret is in PENDING state and cannot be deleted")
    elif secret.status == SecretStatus.DELETING:
        raise ConflictException("Secret is already marked for deletion")

    await update_secret_status_in_db(session, secret, SecretStatus.DELETING, None, datetime.now(UTC), user)

    if not secret.project_secrets:
        await delete_secret_in_db(session, secret)
    else:
        for project_secret in secret.project_secrets:
            # Set the status to DELETING for each project secret
            await update_project_secret_status_in_db(
                session, project_secret, ProjectSecretStatus.DELETING, None, datetime.now(UTC), user
            )

            # Submit a message to the cluster queue to handle deletion
            message = ProjectSecretsDeleteMessage(
                message_type="project_secrets_delete",
                project_secret_id=project_secret.id,
                project_name=project_secret.project.name,
                secret_type=map_secret_type_to_component_kind(secret.type),
            )
            await submit_message_to_cluster_queue(project_secret.project.cluster_id, message)


async def submit_delete_project_secret(
    session: AsyncSession, organization_id: UUID, project_secret: ProjectSecretModel, user: str
):
    if project_secret.status == ProjectSecretStatus.DELETING:
        raise ConflictException("Project Secret is already marked for deletion")

    parent_secret = await get_secret_in_organization(session, organization_id, project_secret.secret_id)
    if not parent_secret:
        raise NotFoundException("Secret not found")

    # update the project secret status to PENDING state to indcate project unassignment is in progress
    await update_secret_status_in_db(session, parent_secret, SecretStatus.PENDING, None, datetime.now(UTC), user)

    await update_project_secret_status_in_db(
        session, project_secret, ProjectSecretStatus.DELETING, None, datetime.now(UTC), user
    )

    # Submit a message to the cluster queue to handle deletion
    message = ProjectSecretsDeleteMessage(
        message_type="project_secrets_delete",
        project_secret_id=project_secret.id,
        project_name=project_secret.project.name,
        secret_type=map_secret_type_to_component_kind(parent_secret.type),
    )
    await submit_message_to_cluster_queue(project_secret.project.cluster_id, message)


async def update_project_secret_assignments(
    session: AsyncSession, user_email: str, organization_id: UUID, secret: SecretModel, project_ids: list[UUID]
) -> None:
    current_project_ids = {ps.project_id for ps in secret.project_secrets}
    new_project_ids = set(project_ids)

    to_add = new_project_ids - current_project_ids
    to_remove = current_project_ids - new_project_ids

    if not to_add and not to_remove:
        raise ValueError("No changes in project assignments")

    # validate that all project IDs to be removed are not currently assigned storages
    if to_remove:
        await ensure_can_remove_secret_from_projects(session, list(to_remove), secret.id)

    await update_secret_status_in_db(
        session,
        secret,
        SecretStatus.PENDING,
        None,
        datetime.now(UTC),
        user_email,
    )

    # Send create messages for new project assignments
    if to_add:
        await assign_projects_to_secret(session, organization_id, secret, list(to_add), user_email)

    # Send delete messages for removed project assignments
    for project_id in to_remove:
        project_secret = await get_project_secret(session, secret.id, project_id)

        if not project_secret or not project_secret.project:
            raise ValueError(f"Project ID {project_id} is not assigned to the secret")

        delete_message = ProjectSecretsDeleteMessage(
            message_type="project_secrets_delete",
            project_secret_id=project_secret.id,
            project_name=project_secret.project.name,
            secret_type=map_secret_type_to_component_kind(secret.type),
        )
        await update_project_secret_status_in_db(
            session, project_secret, ProjectSecretStatus.DELETING, None, datetime.now(UTC), "system"
        )
        await submit_message_to_cluster_queue(project_secret.project.cluster_id, delete_message)


async def update_project_secret_status(session: AsyncSession, cluster: Cluster, message: ProjectSecretsUpdateMessage):
    project_secret = await get_project_secret_by_id(session, message.project_secret_id)

    if project_secret is None:
        logger.error(f"Project Secret {message.project_secret_id} not found")
        return

    secret = await get_secret_in_organization(session, cluster.organization_id, project_secret.secret_id)

    if secret is None:
        logger.error(f"Secret {project_secret.secret_id} not found")
        return

    if message.status == ProjectSecretStatus.DELETED and project_secret.status == ProjectSecretStatus.DELETING:
        await delete_project_secret_in_db(session, project_secret)
    elif project_secret.status == ProjectSecretStatus.DELETING and message.status not in (
        ProjectSecretStatus.DELETED,
        ProjectSecretStatus.DELETE_FAILED,
    ):
        # Don't update status if it's DELETING and message is not a terminal delete state
        logger.info(
            f"Skipping status update for project_secret {project_secret.id} "
            f"(current: DELETING, message: {message.status})"
        )
    else:
        await update_project_secret_status_in_db(
            session, project_secret, message.status, message.status_reason, datetime.now(UTC), "system"
        )

    await session.refresh(secret)

    # PROJECT-scoped secrets cannot exist without project assignments
    # Delete the parent secret if it's PROJECT-scoped and has no assignments
    if secret.scope == SecretScope.PROJECT and not secret.project_secrets:
        logger.info(f"Deleting PROJECT-scoped secret {secret.name} since it has no project assignments")
        await delete_secret_in_db(session, secret)
        return

    project_storages = await get_project_storages_by_project_secret(session, project_secret)
    if not project_storages:
        logger.info(f"No ProjectStorages found for ProjectSecret {project_secret.id}")
    else:
        for project_storage in project_storages:
            await update_project_storage_secret_status(session, project_secret.secret_id, project_storage)

    secret_status, status_reason = resolve_secret_status(secret.status, secret.project_secrets)
    if secret_status == SecretStatus.DELETED:
        logger.info(f"Deleting secret {secret.name} since it was marked for deletion and criteria was met")
        await delete_secret_in_db(session, secret)
        return
    elif secret.status != secret_status:
        await update_secret_status_in_db(
            session,
            project_secret.secret,
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


async def resolve_hf_token_reference(
    session: AsyncSession,
    project: Project,
    token_secret_id: UUID,
) -> SecretModel:
    secret = await get_project_scoped_secret_by_id(
        session,
        project_id=project.id,
        secret_id=token_secret_id,
        use_case=SecretUseCase.HUGGING_FACE,
    )

    if secret is None:
        raise NotFoundException("Hugging Face token reference not found for this project.")

    return secret


async def assign_projects_to_secret(session, organization_id, secret, project_ids, user_email):
    # Validate all projects first before making any database changes
    projects = []
    for project_id in project_ids:
        project = await get_project_in_organization(session, organization_id, project_id)
        if not project:
            raise ValueError(f"Project ID {project_id} does not exist in the organization")
        elif project.status != ProjectStatus.READY:
            raise ConflictException(f"Project {project.name} is not in a READY state")
        projects.append(project)

    # Assign all projects to the secret in a single operation
    await assign_secret_to_projects(
        session=session,
        secret_id=secret.id,
        project_ids=project_ids,
        user_email=user_email,
    )

    # Send create messages for each project assignment
    for project in projects:
        project_secret = await get_project_secret(session, secret.id, project.id)

        if not project_secret:
            continue

        create_message = ProjectSecretsCreateMessage(
            message_type="project_secrets_create",
            project_secret_id=project_secret.id,
            secret_name=secret.name,
            project_name=project.name,
            manifest=secret.manifest,
            secret_type=map_secret_type_to_component_kind(secret.type),
        )

        await submit_message_to_cluster_queue(project.cluster_id, create_message)
