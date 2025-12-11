# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

import yaml

from airm.messaging.schemas import (
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectSecretStatus,
    SecretKind,
    SecretScope,
)
from airm.secrets.constants import PROJECT_SECRET_SCOPE_LABEL
from airm.secrets.utils import validate_secret_manifest

from ..messaging.sender import MessageSender
from ..projects.models import Project
from ..utilities.exceptions import ValidationException
from .enums import SecretStatus
from .models import OrganizationScopedSecret, OrganizationSecretAssignment, ProjectScopedSecret
from .schemas import (
    BaseSecretIn,
    ProjectSecret,
    ProjectSecretsWithParentSecret,
    ProjectSecretWithParentSecret,
    SecretResponse,
    SecretWithProjects,
)


def add_use_case_label_to_manifest(manifest: dict, use_case: str) -> dict:
    """
    Adds 'airm.silogen.com/use-case' label to a Kubernetes manifest.
    This works for both Kubernetes Secrets and ExternalSecrets.

    Args:
        manifest: The manifest dictionary to modify
        use_case: The use case value (will be lowercased)

    Returns:
        The modified manifest dictionary
    """
    metadata = manifest.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        manifest["metadata"] = metadata

    labels = metadata.get("labels")
    if not isinstance(labels, dict):
        labels = {}
        metadata["labels"] = labels

    labels["airm.silogen.com/use-case"] = use_case.lower()

    return manifest


def add_scope_label_to_manifest(manifest: dict, scope: SecretScope) -> dict:
    """
    Adds 'airm.silogen.com/secret-scope' label to a Kubernetes manifest.
    This works for both Kubernetes Secrets and ExternalSecrets.

    Args:
        manifest: The manifest dictionary to modify
        scope: The scope value (will be lowercased)

    Returns:
        The modified manifest dictionary
    """
    metadata = manifest.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        manifest["metadata"] = metadata

    labels = metadata.get("labels")
    if not isinstance(labels, dict):
        labels = {}
        metadata["labels"] = labels

    labels[PROJECT_SECRET_SCOPE_LABEL] = scope.value.lower()

    return manifest


def sanitize_external_secret_manifest(
    manifest: dict,
) -> str:
    """
    Removes the 'namespace' field from the metadata of an ExternalSecret manifest,
    and returns the cleaned manifest as a YAML string.
    """
    if isinstance(manifest.get("metadata"), dict) and "namespace" in manifest["metadata"]:
        del manifest["metadata"]["namespace"]

    return yaml.safe_dump(manifest, sort_keys=False)


def resolve_secret_status(
    current_status: SecretStatus,
    project_secrets_assignments: list[OrganizationSecretAssignment],
) -> tuple[SecretStatus, str | None]:
    # Deleting flow first
    if current_status == SecretStatus.DELETING:
        if not project_secrets_assignments:
            return SecretStatus.DELETED, None
        if any(ps.status == ProjectSecretStatus.DELETE_FAILED for ps in project_secrets_assignments):
            return SecretStatus.DELETE_FAILED, "Some project secrets failed to be deleted"
        return SecretStatus.DELETING, None

    # Non-deleting flow
    if not project_secrets_assignments:
        return SecretStatus.UNASSIGNED, None

    if any(ps.status == ProjectSecretStatus.DELETE_FAILED for ps in project_secrets_assignments):
        return SecretStatus.DELETE_FAILED, "Some project secrets failed to be deleted"

    # Any FAILED → status = FAILED; optionally list project names
    if any(ps.status == ProjectSecretStatus.FAILED for ps in project_secrets_assignments):
        return SecretStatus.FAILED, "Some project secrets are in a failed state"

    # Any SYNCED_ERROR or UNKNOWN → status = SYNCED_ERROR; optionally list names
    if any(
        ps.status in (ProjectSecretStatus.SYNCED_ERROR, ProjectSecretStatus.UNKNOWN)
        for ps in project_secrets_assignments
    ):
        return SecretStatus.SYNCED_ERROR, "Some project secrets have failed to sync"

    # All synced
    if all(ps.status == ProjectSecretStatus.SYNCED for ps in project_secrets_assignments):
        return SecretStatus.SYNCED, None

    # Unsolicited delete
    if any(ps.status == ProjectSecretStatus.DELETED for ps in project_secrets_assignments):
        return SecretStatus.SYNCED_ERROR, "One or more project secrets have been deleted unexpectedly."

    # Partially synced
    if any(ps.status == ProjectSecretStatus.SYNCED for ps in project_secrets_assignments):
        return SecretStatus.PARTIALLY_SYNCED, None

    # Fallback
    return SecretStatus.SYNCED_ERROR, "Unknown Project secret states detected."


def validate_secret_manifest_for_api(secret: BaseSecretIn, manifest_yaml: str) -> dict:
    """
    Validates a secret manifest using the universal validator.

    This is a wrapper around the package-level validate_secret_manifest function
    that extracts the component kind from the secret input.
    """
    return validate_secret_manifest(manifest_yaml, secret.type)


def validate_and_patch_secret_manifest(secret_in: BaseSecretIn) -> dict:
    if not secret_in.manifest:
        raise ValidationException("Manifest must be provided for secret creation.")
    try:
        manifest_dict = validate_secret_manifest_for_api(secret_in, secret_in.manifest)
    except Exception as exc:
        raise ValidationException(f"Invalid Secret manifest: {exc}") from exc

    if secret_in.use_case:
        manifest_dict = add_use_case_label_to_manifest(manifest_dict, secret_in.use_case.value)

    if secret_in.scope:
        manifest_dict = add_scope_label_to_manifest(manifest_dict, secret_in.scope)

    return manifest_dict


async def publish_project_secret_creation_message(
    secret: ProjectScopedSecret | OrganizationSecretAssignment,
    manifest_yaml: str,
    message_sender: MessageSender,
    parent_secret: OrganizationScopedSecret | None = None,
) -> None:
    message = ProjectSecretsCreateMessage(
        message_type="project_secrets_create",
        project_name=secret.project.name,
        project_secret_id=secret.id,
        secret_name=parent_secret.name if parent_secret else secret.name,
        manifest=manifest_yaml,
        secret_type=parent_secret.type if parent_secret else secret.type,
        secret_scope=parent_secret.scope if parent_secret else secret.scope,
    )
    await message_sender.enqueue(secret.project.cluster_id, message)


async def publish_secret_deletion_message(
    cluster_id: UUID,
    project_secret_id: UUID,
    project_name: str,
    secret_type: SecretKind,
    secret_scope: SecretScope,
    message_sender: MessageSender,
) -> None:
    message = ProjectSecretsDeleteMessage(
        message_type="project_secrets_delete",
        project_secret_id=project_secret_id,
        project_name=project_name,
        secret_type=secret_type,
        secret_scope=secret_scope,
    )
    await message_sender.enqueue(cluster_id, message)


async def publish_project_secret_deletion_message(
    assignment: OrganizationSecretAssignment,
    parent_secret: OrganizationScopedSecret,
    message_sender: MessageSender,
) -> None:
    """
    Convenience wrapper for publishing deletion message from assignment and parent secret objects.

    Args:
        assignment: OrganizationSecretAssignment with project relationship loaded
        parent_secret: The parent OrganizationScopedSecret
        message_sender: MessageSender for queueing messages
    """
    await publish_secret_deletion_message(
        cluster_id=assignment.project.cluster_id,
        project_secret_id=assignment.id,
        project_name=assignment.project.name,
        secret_type=parent_secret.type,
        secret_scope=SecretScope.ORGANIZATION,
        message_sender=message_sender,
    )


def calculate_assignment_changes(current_project_ids: set, new_project_ids: set) -> tuple[set, set]:
    to_add = new_project_ids - current_project_ids
    to_remove = current_project_ids - new_project_ids
    return to_add, to_remove


# TODO review and remove/simplify once SDA-2357 is resolved
def build_secret_response(secret: OrganizationScopedSecret | ProjectScopedSecret) -> SecretWithProjects:
    project_secrets = []

    if secret.scope == SecretScope.PROJECT:
        # For PROJECT-scoped secrets, project_id and project are always set
        project_secret_schema = ProjectSecret(
            id=secret.id,
            project_id=secret.project_id,
            project_name=secret.project.name,
            status=secret.status,
            status_reason=secret.status_reason,
            created_at=secret.created_at,
            updated_at=secret.updated_at,
            created_by=secret.created_by,
            updated_by=secret.updated_by,
        )
        project_secrets = [project_secret_schema]

    elif secret.scope == SecretScope.ORGANIZATION:
        # Use the organization_secret_assignments relationship (eagerly loaded by repository)
        project_secrets = [
            ProjectSecret(
                id=assignment.id,
                project_id=assignment.project_id,
                project_name=assignment.project.name,
                status=assignment.status,
                status_reason=assignment.status_reason,
                created_at=assignment.created_at,
                updated_at=assignment.updated_at,
                created_by=assignment.created_by,
                updated_by=assignment.updated_by,
            )
            for assignment in secret.organization_secret_assignments
        ]

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
        project_secrets=project_secrets,
    )


def build_project_secret_response(secrets: list, project: Project) -> ProjectSecretsWithParentSecret:
    project_secrets = []

    for secret in secrets:
        # Handle PROJECT-scoped secrets (where the secret itself belongs to the project)
        if secret.scope == SecretScope.PROJECT:
            if secret.project_id == project.id:
                project_secrets.append(
                    ProjectSecretWithParentSecret(
                        id=secret.id,  # Use the secret's own ID
                        created_at=secret.created_at,
                        updated_at=secret.updated_at,
                        created_by=secret.created_by,
                        updated_by=secret.updated_by,
                        project_id=secret.project_id,
                        project_name=secret.project.name,
                        status=secret.status,
                        status_reason=secret.status_reason,
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
        # Handle ORGANIZATION-scoped secrets (assigned to the project via organization_secret_assignments table)
        else:
            for assignment in secret.organization_secret_assignments:
                if assignment.project_id == project.id:  # Only include if assignment exists
                    project_secrets.append(
                        ProjectSecretWithParentSecret(
                            id=assignment.id,
                            created_at=assignment.created_at,
                            updated_at=assignment.updated_at,
                            created_by=assignment.created_by,
                            updated_by=assignment.updated_by,
                            project_id=assignment.project.id,
                            project_name=assignment.project.name,
                            status=assignment.status,
                            status_reason=assignment.status_reason,
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
