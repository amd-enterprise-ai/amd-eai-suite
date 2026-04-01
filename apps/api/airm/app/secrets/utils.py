# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

import yaml

from ..messaging.schemas import (
    ExternalSecretManifest,
    KubernetesSecretManifest,
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectSecretStatus,
    SecretKind,
    SecretScope,
)
from ..messaging.sender import MessageSender
from ..projects.models import Project
from ..projects.schemas import ProjectAssignment
from ..secrets.constants import (
    EXTERNAL_SECRETS_KIND,
    KUBERNETES_SECRET_KIND,
    PROJECT_SECRET_ID_LABEL,
    PROJECT_SECRET_SCOPE_LABEL,
    PROJECT_SECRET_USE_CASE_LABEL,
)
from ..utilities.exceptions import ValidationException
from .enums import SecretStatus
from .models import OrganizationScopedSecret, OrganizationSecretAssignment, ProjectScopedSecret
from .schemas import (
    BaseSecretIn,
    ProjectSecretsWithParentSecret,
    ProjectSecretWithParentSecret,
    SecretResponse,
    SecretWithProjects,
)


def add_use_case_label_to_manifest(
    manifest: KubernetesSecretManifest | ExternalSecretManifest, use_case: str
) -> KubernetesSecretManifest | ExternalSecretManifest:
    """
    Adds 'airm.silogen.com/use-case' label to a Kubernetes manifest.
    This works for both Kubernetes Secrets and ExternalSecrets.

    Args:
        manifest: The Pydantic manifest model to modify
        use_case: The use case value (will be lowercased)

    Returns:
        A new manifest with the label added
    """
    # Ensure metadata and labels exist
    if manifest.metadata.labels is None:
        manifest.metadata.labels = {}

    # Add the use case label
    manifest.metadata.labels[PROJECT_SECRET_USE_CASE_LABEL] = use_case.lower()

    return manifest


def add_scope_label_to_manifest(
    manifest: KubernetesSecretManifest | ExternalSecretManifest, scope: SecretScope
) -> KubernetesSecretManifest | ExternalSecretManifest:
    """
    Adds 'airm.silogen.com/secret-scope' label to a Kubernetes manifest.
    This works for both Kubernetes Secrets and ExternalSecrets.

    Args:
        manifest: The Pydantic manifest model to modify
        scope: The scope value (will be lowercased)

    Returns:
        A new manifest with the label added
    """
    # Ensure metadata and labels exist
    if manifest.metadata.labels is None:
        manifest.metadata.labels = {}

    # Add the scope label
    manifest.metadata.labels[PROJECT_SECRET_SCOPE_LABEL] = scope.value.lower()

    return manifest


def sanitize_external_secret_manifest(
    manifest: ExternalSecretManifest,
) -> ExternalSecretManifest:
    """
    Removes the 'namespace' field from the metadata of an ExternalSecret manifest.
    Returns a new ExternalSecretManifest with namespace removed.
    """

    manifest_dict = manifest.model_dump(by_alias=True, exclude_none=True)
    if isinstance(manifest_dict.get("metadata"), dict) and "namespace" in manifest_dict["metadata"]:
        del manifest_dict["metadata"]["namespace"]

    return ExternalSecretManifest(**manifest_dict)


def resolve_secret_status(
    current_status: SecretStatus,
    project_secrets_assignments: list[OrganizationSecretAssignment],
) -> tuple[SecretStatus, str | None]:
    """Determine the overall secret status based on current status and project secret statuses.

    Priority order (highest to lowest):
    1. DELETING - Currently deleting (when current_status is DELETING)
    2. DELETE_FAILED - Any project secret failed to delete
    3. FAILED - Any project secret in failed state
    4. SYNCED_ERROR - Any sync error, unknown state, or unexpected deletion
    5. SYNCED - All project secrets synced
    6. PARTIALLY_SYNCED - Some project secrets synced
    7. PENDING - All project secrets pending
    8. DELETED - All deleted (when current_status is DELETING and no project secrets)
    9. UNASSIGNED - No project secrets
    """
    # Handle deletion flow
    if current_status == SecretStatus.DELETING:
        if not project_secrets_assignments:
            return SecretStatus.DELETED, None
        if any(ps.status == ProjectSecretStatus.DELETE_FAILED for ps in project_secrets_assignments):
            return SecretStatus.DELETE_FAILED, "Some project secrets failed to be deleted"
        return SecretStatus.DELETING, None

    # Non-deleting flow
    if not project_secrets_assignments:
        return SecretStatus.UNASSIGNED, None

    # Priority 1: Any DELETE_FAILED → DELETE_FAILED
    if any(ps.status == ProjectSecretStatus.DELETE_FAILED for ps in project_secrets_assignments):
        return SecretStatus.DELETE_FAILED, "Some project secrets failed to be deleted"

    # Priority 2: Any FAILED → FAILED
    if any(ps.status == ProjectSecretStatus.FAILED for ps in project_secrets_assignments):
        return SecretStatus.FAILED, "Some project secrets are in a failed state"

    # Priority 3: Any SYNCED_ERROR or UNKNOWN → SYNCED_ERROR
    if any(
        ps.status in (ProjectSecretStatus.SYNCED_ERROR, ProjectSecretStatus.UNKNOWN)
        for ps in project_secrets_assignments
    ):
        return SecretStatus.SYNCED_ERROR, "Some project secrets have failed to sync"

    # Priority 3 (continued): Unexpected DELETED → SYNCED_ERROR
    if any(ps.status == ProjectSecretStatus.DELETED for ps in project_secrets_assignments):
        return SecretStatus.SYNCED_ERROR, "One or more project secrets have been deleted unexpectedly."

    # Priority 4: All SYNCED → SYNCED
    if all(ps.status == ProjectSecretStatus.SYNCED for ps in project_secrets_assignments):
        return SecretStatus.SYNCED, None

    # Priority 5: Some SYNCED → PARTIALLY_SYNCED
    if any(ps.status == ProjectSecretStatus.SYNCED for ps in project_secrets_assignments):
        return SecretStatus.PARTIALLY_SYNCED, None

    # Priority 6: All PENDING → PENDING
    if all(ps.status == ProjectSecretStatus.PENDING for ps in project_secrets_assignments):
        return SecretStatus.PENDING, None

    # Fallback for any unhandled state combinations
    return SecretStatus.SYNCED_ERROR, "Unknown Project secret states detected."


def parse_manifest_yaml_to_model(
    manifest_yaml: str, secret_type: SecretKind
) -> KubernetesSecretManifest | ExternalSecretManifest:
    """
    Parses a YAML manifest string into the appropriate Pydantic model.

    This is a thin wrapper around the package-level validate_secret_manifest function.

    Args:
        manifest_yaml: YAML string containing the manifest
        secret_type: The type of secret (KubernetesSecret or ExternalSecret)

    Returns:
        The appropriate Pydantic model instance

    Raises:
        ValidationException: if YAML is invalid or validation fails
    """
    try:
        return validate_secret_manifest(manifest_yaml, secret_type)
    except Exception as exc:
        raise ValidationException(f"Invalid Secret manifest: {exc}") from exc


def validate_and_patch_secret_manifest(
    secret_in: BaseSecretIn,
) -> KubernetesSecretManifest | ExternalSecretManifest:
    """
    Validates a secret manifest and applies labels.

    Converts YAML to Pydantic model early and works with typed objects throughout.

    Args:
        secret_in: The secret input containing manifest YAML and metadata

    Returns:
        Validated and patched Pydantic manifest model

    Raises:
        ValidationException: if manifest is invalid or missing
    """
    if not secret_in.manifest:
        raise ValidationException("Manifest must be provided for secret creation.")
    try:
        manifest_model = parse_manifest_yaml_to_model(secret_in.manifest, secret_in.type)
    except Exception as exc:
        raise ValidationException(f"Invalid Secret manifest: {exc}") from exc
    if secret_in.use_case:
        manifest_model = add_use_case_label_to_manifest(manifest_model, secret_in.use_case)

    if secret_in.scope:
        manifest_model = add_scope_label_to_manifest(manifest_model, secret_in.scope)

    return manifest_model


async def publish_project_secret_creation_message(
    secret: ProjectScopedSecret | OrganizationSecretAssignment,
    manifest_model: KubernetesSecretManifest | ExternalSecretManifest,
    message_sender: MessageSender,
    parent_secret: OrganizationScopedSecret | None = None,
) -> None:
    # deep copy to avoid modifying the original manifest
    manifest = manifest_model.model_copy(deep=True)
    secret_name = parent_secret.name if parent_secret else secret.name

    manifest.metadata.name = secret_name
    manifest.metadata.namespace = secret.project.name

    if manifest.metadata.labels is None:
        manifest.metadata.labels = {}
    manifest.metadata.labels[PROJECT_SECRET_ID_LABEL] = str(secret.id)

    if PROJECT_SECRET_SCOPE_LABEL not in manifest.metadata.labels:
        scope = SecretScope.ORGANIZATION if parent_secret else SecretScope.PROJECT
        add_scope_label_to_manifest(manifest, scope)

    message = ProjectSecretsCreateMessage(
        message_type="project_secrets_create",
        manifest=manifest,
        secret_type=parent_secret.type if parent_secret else secret.type,
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


def build_secret_response(secret: OrganizationScopedSecret | ProjectScopedSecret) -> SecretWithProjects:
    project_secrets = []

    if secret.scope == SecretScope.PROJECT:
        project_secrets = [ProjectAssignment.model_validate(secret)]
    elif secret.scope == SecretScope.ORGANIZATION:
        project_secrets = [
            ProjectAssignment.model_validate(assignment) for assignment in secret.organization_secret_assignments
        ]

    # Validate the secret and add project_secrets using model_copy
    secret_response = SecretResponse.model_validate(secret)
    return SecretWithProjects.model_validate(secret_response.model_dump() | {"project_secrets": project_secrets})


def build_project_secret_response(secrets: list, project: Project) -> ProjectSecretsWithParentSecret:
    project_secrets = []

    for secret in secrets:
        if secret.scope == SecretScope.PROJECT:
            if secret.project_id == project.id:
                # For project-scoped secrets, validate as ProjectAssignment and attach itself as the parent secret
                assignment = ProjectAssignment.model_validate(secret)
                secret_response = SecretResponse.model_validate(secret)
                project_secrets.append(
                    ProjectSecretWithParentSecret.model_validate(assignment.model_dump() | {"secret": secret_response})
                )
        else:
            for assignment in secret.organization_secret_assignments:
                if assignment.project_id == project.id:
                    # For organization secrets, validate the assignment and attach the parent secret
                    assignment_data = ProjectAssignment.model_validate(assignment)
                    secret_response = SecretResponse.model_validate(secret)
                    project_secrets.append(
                        ProjectSecretWithParentSecret.model_validate(
                            assignment_data.model_dump() | {"secret": secret_response}
                        )
                    )

    return ProjectSecretsWithParentSecret(data=project_secrets)


def _load_single_manifest(manifest_yaml: str) -> dict:
    """Load and parse a single YAML manifest."""
    try:
        manifests = list(yaml.safe_load_all(manifest_yaml))
    except yaml.YAMLError as e:
        raise ValidationException(f"Failed to load YAML: {e}")

    if len(manifests) != 1:
        raise ValidationException(f"Expected 1 manifest, but got {len(manifests)}")

    manifest = manifests[0]

    if not isinstance(manifest, dict):
        raise ValidationException("Manifest is malformed")

    return manifest


def validate_external_secret_manifest(manifest_yaml: str) -> ExternalSecretManifest:
    """
    Parses and validates an ExternalSecret manifest from YAML.

    Uses Pydantic for basic structure validation. Full validation is performed
    by the Kubernetes client in the dispatcher for comprehensive schema validation.

    Args:
        manifest_yaml: YAML string containing the manifest

    Returns:
        ExternalSecretManifest: Validated manifest as Pydantic model

    Raises:
        Exception: if YAML is invalid or validation fails
    """
    manifest_dict = _load_single_manifest(manifest_yaml)

    try:
        return ExternalSecretManifest(**manifest_dict)
    except Exception as e:
        raise Exception(f"Invalid ExternalSecret manifest: {e}")


def validate_kubernetes_secret_manifest(manifest_yaml: str) -> KubernetesSecretManifest:
    """
    Parses and validates a Kubernetes Secret manifest from YAML.

    Uses Pydantic for basic structure validation. Full validation is performed
    by the Kubernetes client in the dispatcher for comprehensive schema validation.

    Args:
        manifest_yaml: YAML string containing the manifest

    Returns:
        KubernetesSecretManifest: Validated manifest as Pydantic model

    Raises:
        Exception: if YAML is invalid or validation fails
    """
    manifest_dict = _load_single_manifest(manifest_yaml)

    try:
        return KubernetesSecretManifest(**manifest_dict)
    except Exception as e:
        raise Exception(f"Invalid Kubernetes Secret manifest: {e}")


def validate_secret_manifest(
    manifest_yaml: str, component_kind: SecretKind
) -> KubernetesSecretManifest | ExternalSecretManifest:
    """
    Universal validator for secret manifests.

    Routes to the appropriate validator based on the component kind.
    This is the package-level validator that should be used by both API and dispatcher.

    Args:
        manifest_yaml: YAML string containing the manifest
        component_kind: The SecretKind enum value

    Returns:
        KubernetesSecretManifest | ExternalSecretManifest: Validated manifest as Pydantic model

    Raises:
        Exception: if YAML is invalid or validation fails
        ValueError: if component_kind is unsupported
    """
    match component_kind:
        case SecretKind.EXTERNAL_SECRET:
            return validate_external_secret_manifest(manifest_yaml)
        case SecretKind.KUBERNETES_SECRET:
            return validate_kubernetes_secret_manifest(manifest_yaml)
        case _:
            raise ValueError(f"Unsupported component kind: {component_kind}")


def get_kubernetes_kind(component_kind: SecretKind) -> str:
    """
    Maps SecretKind enum values to actual Kubernetes resource kinds.

    This is needed because the enum uses "KubernetesSecret" but the Kubernetes API
    expects "Secret" for native Kubernetes secrets.

    Args:
        component_kind: The SecretKind enum value

    Returns:
        str: The actual Kubernetes resource kind string

    Raises:
        ValueError: if component_kind is unsupported
    """
    match component_kind:
        case SecretKind.EXTERNAL_SECRET:
            return EXTERNAL_SECRETS_KIND
        case SecretKind.KUBERNETES_SECRET:
            return KUBERNETES_SECRET_KIND
        case _:
            raise ValueError(f"Unsupported component kind: {component_kind}")
