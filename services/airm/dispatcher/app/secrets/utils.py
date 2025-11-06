# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

from airm.messaging.schemas import ProjectSecretStatus, ProjectSecretsUpdateMessage
from airm.secrets.constants import (
    PROJECT_SECRET_ID_LABEL,
)

from ..utilities.attribute_utils import get_attr_or_key


def _build_metadata(
    namespace: str, secret_name: str, project_secret_id: str, existing_metadata: dict | None = None
) -> dict:
    metadata: dict = {"name": secret_name, "namespace": namespace}

    labels = {}
    if existing_metadata:
        labels.update(existing_metadata.get("labels", {}))
        annotations = existing_metadata.get("annotations")
        if annotations:
            metadata["annotations"] = annotations

    labels[PROJECT_SECRET_ID_LABEL] = project_secret_id
    metadata["labels"] = labels
    return metadata


def patch_external_secret_manifest(
    namespace: str,
    secret_name: str,
    manifest: dict,
    project_secret_id: str,
):
    patched_manifest = deepcopy(manifest)
    existing_metadata = get_attr_or_key(patched_manifest, "metadata", {})
    patched_manifest["metadata"] = _build_metadata(
        namespace=namespace,
        secret_name=secret_name,
        project_secret_id=project_secret_id,
        existing_metadata=existing_metadata if isinstance(existing_metadata, dict) else None,
    )
    return patched_manifest


def patch_kubernetes_secret_manifest(
    namespace: str,
    secret_name: str,
    manifest: dict,
    project_secret_id: str,
):
    patched_manifest = deepcopy(manifest)
    existing_metadata = get_attr_or_key(patched_manifest, "metadata", {})
    patched_manifest["metadata"] = _build_metadata(
        namespace=namespace,
        secret_name=secret_name,
        project_secret_id=project_secret_id,
        existing_metadata=existing_metadata if isinstance(existing_metadata, dict) else None,
    )
    return patched_manifest


def extract_project_secret_id(item: dict) -> UUID | None:
    metadata = get_attr_or_key(item, "metadata", {})
    labels = get_attr_or_key(metadata, "labels", {})
    project_secret_id_str = get_attr_or_key(labels, PROJECT_SECRET_ID_LABEL, None)
    return UUID(project_secret_id_str) if project_secret_id_str else None


def create_project_secret_status_message(
    project_secret_id: UUID,
    status: ProjectSecretStatus,
    status_reason: str | None = None,
) -> ProjectSecretsUpdateMessage:
    return ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret_id,
        status=status,
        status_reason=status_reason,
        updated_at=datetime.now(UTC),
    )


def get_status_for_external_secret(resource, event_type) -> tuple[ProjectSecretStatus | None, str]:
    if event_type == "DELETED":
        return ProjectSecretStatus.DELETED, "Resource has been removed from the cluster."

    resource_status = get_attr_or_key(resource, "status", {})

    # Try to extract condition status from resource

    conditions = get_attr_or_key(resource_status, "conditions", [])

    if conditions:
        for condition in conditions:
            cond_type = condition.get("type") if isinstance(condition, dict) else getattr(condition, "type", None)
            cond_status = condition.get("status") if isinstance(condition, dict) else getattr(condition, "status", None)
            cond_reason = condition.get("reason") if isinstance(condition, dict) else getattr(condition, "reason", None)
            cond_message = (
                condition.get("message") if isinstance(condition, dict) else getattr(condition, "message", None)
            )

            if cond_type == "Ready":
                if cond_status == "True":
                    return ProjectSecretStatus.SYNCED, cond_message or "Secret is ready."
                elif cond_status == "False":
                    return ProjectSecretStatus.SYNCED_ERROR, cond_message or cond_reason or "Secret is not ready."
                elif cond_status == "Unknown":
                    return ProjectSecretStatus.UNKNOWN, cond_message or "Secret readiness is unknown."
    return None, "Secret status could not be determined."


def get_status_for_kubernetes_secret(resource, event_type) -> tuple[ProjectSecretStatus | None, str]:
    if event_type == "DELETED":
        return ProjectSecretStatus.DELETED, "Secret has been deleted from the cluster."

    if event_type in {"ADDED", "MODIFIED"}:
        return ProjectSecretStatus.SYNCED, "Secret is present in the cluster."

    return ProjectSecretStatus.UNKNOWN, f"Secret event '{event_type}' reported."
