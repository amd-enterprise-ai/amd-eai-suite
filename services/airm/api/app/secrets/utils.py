# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import yaml

from airm.messaging.schemas import ProjectSecretStatus, SecretsComponentKind

from .enums import SecretStatus, SecretType
from .models import ProjectSecret


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
    project_secrets: list[ProjectSecret],
) -> tuple[SecretStatus, str | None]:
    # Deleting flow first
    if current_status == SecretStatus.DELETING:
        if not project_secrets:
            return SecretStatus.DELETED, None
        if any(ps.status == ProjectSecretStatus.DELETE_FAILED for ps in project_secrets):
            return SecretStatus.DELETE_FAILED, "Some project secrets failed to be deleted"
        return SecretStatus.DELETING, None

    # Non-deleting flow
    if not project_secrets:
        return SecretStatus.UNASSIGNED, None

    if any(ps.status == ProjectSecretStatus.DELETE_FAILED for ps in project_secrets):
        return SecretStatus.DELETE_FAILED, "Some project secrets failed to be deleted"

    # Any FAILED → status = FAILED; optionally list project names
    if any(ps.status == ProjectSecretStatus.FAILED for ps in project_secrets):
        return SecretStatus.FAILED, "Some project secrets are in a failed state"

    # Any SYNCED_ERROR or UNKNOWN → status = SYNCED_ERROR; optionally list names
    if any(ps.status in (ProjectSecretStatus.SYNCED_ERROR, ProjectSecretStatus.UNKNOWN) for ps in project_secrets):
        return SecretStatus.SYNCED_ERROR, "Some project secrets have failed to sync"

    # All synced
    if all(ps.status == ProjectSecretStatus.SYNCED for ps in project_secrets):
        return SecretStatus.SYNCED, None

    # Unsolicited delete
    if any(ps.status == ProjectSecretStatus.DELETED for ps in project_secrets):
        return SecretStatus.SYNCED_ERROR, "One or more project secrets have been deleted unexpectedly."

    # Partially synced
    if any(ps.status == ProjectSecretStatus.SYNCED for ps in project_secrets):
        return SecretStatus.PARTIALLY_SYNCED, None

    # Fallback
    return SecretStatus.SYNCED_ERROR, "Unknown Project secret states detected."


_SECRET_TYPE_TO_COMPONENT_KIND_MAP: dict[SecretType, SecretsComponentKind] = {
    SecretType.EXTERNAL: SecretsComponentKind.EXTERNAL_SECRET,
    SecretType.KUBERNETES_SECRET: SecretsComponentKind.KUBERNETES_SECRET,
}


def map_secret_type_to_component_kind(secret_type: SecretType | str) -> SecretsComponentKind:
    secret_type_enum = SecretType(secret_type)

    try:
        return _SECRET_TYPE_TO_COMPONENT_KIND_MAP[secret_type_enum]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"Unhandled secret type: {secret_type_enum}") from exc
