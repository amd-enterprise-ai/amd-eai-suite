# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ConfigMapStatus, ProjectSecretStatus, ProjectStorageStatus

from ..projects.enums import ProjectStatus
from ..projects.repository import get_project_in_organization
from ..utilities.exceptions import ValidationException
from .enums import StorageStatus
from .models import ProjectStorage as ProjectStorageModel


async def verify_projects_ready(
    session: AsyncSession,
    organization_id: UUID,
    project_ids: Iterable[UUID],
) -> None:
    if not project_ids:
        return

    for project_id in project_ids:
        project = await get_project_in_organization(session, organization_id, project_id)

        if not project:
            raise ValidationException(f"project id={project_id} not found")
        elif project.status != ProjectStatus.READY:
            raise ValidationException(f"project id={project_id} not READY")


async def resolve_project_storage_composite_status(configmap, project_secret, project_storage):
    configmap_status = getattr(configmap, "status", None)
    configmap_reason = getattr(configmap, "status_reason", None)
    secret_status = getattr(project_secret, "status", None)
    secret_reason = getattr(project_secret, "status_reason", None)

    reasons = []
    if configmap_reason:
        reasons.append(f"configmap: {configmap_reason}")
    if secret_reason:
        reasons.append(f"secret: {secret_reason}")
    reason_text = "; ".join(reasons)

    # Priority 1: Any component failed -> ProjectStorage failed
    if configmap_status == ConfigMapStatus.FAILED or secret_status == ProjectSecretStatus.FAILED:
        failed_components = []
        if configmap_status == ConfigMapStatus.FAILED:
            failed_components.append("configmap")
        if secret_status == ProjectSecretStatus.FAILED:
            failed_components.append("secret")
        return ProjectStorageStatus.FAILED, f"Failed components: {', '.join(failed_components)}. {reason_text}"

    # Priority 2: Both components synced -> ProjectStorage synced
    if configmap_status == ConfigMapStatus.ADDED and secret_status == ProjectSecretStatus.SYNCED:
        return ProjectStorageStatus.SYNCED, f"All components synced. {reason_text}"

    # Priority 3: Both components pending -> ProjectStorage pending
    if configmap_status == ConfigMapStatus.ADDED and secret_status == ProjectSecretStatus.PENDING:
        return ProjectStorageStatus.PENDING, f"Project secret pending. {reason_text}"

    # Priority 4: Mixed states (one synced, one pending) -> Partially synced
    if (configmap_status == ConfigMapStatus.ADDED and secret_status == ProjectSecretStatus.PENDING) or (
        configmap_status == ConfigMapStatus.FAILED and secret_status == ProjectSecretStatus.SYNCED
    ):
        return (ProjectStorageStatus.SYNCED_ERROR, f"Mixed component states. {reason_text}")

    # Default: Unknown/unexpected state -> Failed
    return ProjectStorageStatus.FAILED, f"Unknown component states detected. {reason_text}"


def resolve_storage_status(
    current_status: StorageStatus,
    project_storages: list[ProjectStorageModel],
) -> tuple[StorageStatus, str | None]:
    # Deleting flow first
    if current_status == StorageStatus.DELETING:
        if not project_storages:
            return StorageStatus.DELETED, None
        if any(ps.status == ProjectStorageStatus.DELETE_FAILED for ps in project_storages):
            return StorageStatus.DELETE_FAILED, "Some project storages failed to be deleted"
        return StorageStatus.DELETING, None

    # Non-deleting flow
    if not project_storages:
        return StorageStatus.UNASSIGNED, None

    if any(ps.status == ProjectStorageStatus.DELETE_FAILED for ps in project_storages):
        return StorageStatus.DELETE_FAILED, "Some project storages failed to be deleted"

    # Any FAILED → status = FAILED; optionally list project names
    if any(ps.status == ProjectStorageStatus.FAILED for ps in project_storages):
        return StorageStatus.FAILED, "Some project storages are in a failed state"

    # Any SYNCED_ERROR or UNKNOWN → status = SYNCED_ERROR; optionally list names
    if any(ps.status in (ProjectStorageStatus.SYNCED_ERROR, ProjectStorageStatus.UNKNOWN) for ps in project_storages):
        return StorageStatus.SYNCED_ERROR, "Some project storages have failed to sync"

    # All synced
    if all(ps.status == ProjectStorageStatus.SYNCED for ps in project_storages):
        return StorageStatus.SYNCED, None

    # Unsolicited delete
    if any(ps.status == ProjectStorageStatus.DELETED for ps in project_storages):
        return StorageStatus.SYNCED_ERROR, "One or more project storages have been deleted unexpectedly."

    # Partially synced
    if any(ps.status == ProjectStorageStatus.SYNCED for ps in project_storages):
        return StorageStatus.PARTIALLY_SYNCED, None

    # Fallback
    return StorageStatus.SYNCED_ERROR, "Unknown Project storage states detected."
