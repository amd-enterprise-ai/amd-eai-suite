# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from airm.messaging.schemas import NamespaceStatus, QuotaStatus

from ..clusters.schemas import ClusterResponse
from ..namespaces.models import Namespace
from ..quotas.models import Quota
from ..quotas.schemas import QuotaResponse
from ..utilities.exceptions import ConflictException
from .enums import ProjectStatus
from .models import Project
from .schemas import ProjectResponse, ProjectWithClusterAndQuota


def map_to_schema(
    project: Project,
) -> ProjectWithClusterAndQuota:
    return ProjectWithClusterAndQuota(
        **ProjectResponse.model_validate(project).model_dump(),
        quota=QuotaResponse.model_validate(project.quota),
        cluster=ClusterResponse.model_validate(project.cluster),
    )


def ensure_project_safe_to_delete(project):
    if project.status == ProjectStatus.DELETING:
        raise ConflictException("Project is already marked for deletion")


def resolve_project_status(namespace: Namespace, quota: Quota, project: Project) -> tuple[ProjectStatus, str]:
    if project.status == ProjectStatus.DELETING:
        return ProjectStatus.DELETING, "Project is being deleted."

    component_states = [("namespace", namespace.status), ("quota", quota.status)]

    # Build reason text from components
    reasons = []
    if namespace.status_reason:
        reasons.append(f"namespace: {namespace.status_reason}")
    if quota.status_reason:
        reasons.append(f"quota: {quota.status_reason}")
    reason_text = "; ".join(reasons)

    # Priority 1: Any component failed -> Project failed
    if namespace.status == NamespaceStatus.FAILED or quota.status == QuotaStatus.FAILED:
        failed_components = [
            component
            for component, status in component_states
            if status in (NamespaceStatus.FAILED, QuotaStatus.FAILED)
        ]
        return ProjectStatus.FAILED, f"Failed components: {', '.join(failed_components)}. {reason_text}"

    # Priority 2: All components ready -> Project ready
    if namespace.status == NamespaceStatus.ACTIVE and quota.status == QuotaStatus.READY:
        return ProjectStatus.READY, f"All components ready. {reason_text}"

    # Priority 3: All components pending -> Project pending
    if namespace.status == NamespaceStatus.PENDING and quota.status == QuotaStatus.PENDING:
        return ProjectStatus.PENDING, f"All components pending. {reason_text}"

    # Priority 4: Mixed states (some ready, some pending) -> Partially ready
    ready_components = [
        name for name, status in component_states if status in (NamespaceStatus.ACTIVE, QuotaStatus.READY)
    ]
    pending_components = [
        name for name, status in component_states if status in (NamespaceStatus.PENDING, QuotaStatus.PENDING)
    ]

    if ready_components and pending_components:
        return (
            ProjectStatus.PARTIALLY_READY,
            f"Ready: {', '.join(ready_components)}; Pending: {', '.join(pending_components)}. {reason_text}",
        )

    # Default: Unknown/unexpected state -> Failed
    return ProjectStatus.FAILED, f"Unknown component states detected. {reason_text}"
