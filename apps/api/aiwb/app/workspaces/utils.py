# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from urllib.parse import urlparse

import yaml
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import WORKSPACES_HOST
from ..workloads.enums import WorkloadStatus, WorkloadType
from ..workloads.repository import get_workloads
from .enums import (
    WORKSPACE_USAGE_SCOPE_MAPPING,
    WorkspaceType,
    WorkspaceUsageScope,
    workspace_type_chart_name_mapping,
)

_HTTPROUTE_KIND = "HTTPRoute"


def get_workspaces_hostname(workspaces_host: str = WORKSPACES_HOST) -> str | None:
    """Host portion of ``WORKSPACES_HOST`` (e.g. ``workspaces.<domain>``), or None."""
    if not workspaces_host:
        return None
    return urlparse(workspaces_host).hostname or None


def pin_workspace_route_hostname(manifest: str) -> str:
    """Pin workspace HTTPRoutes in a rendered manifest to the workspaces host.

    Stamps ``spec.hostnames=[workspaces.<domain>]`` onto HTTPRoute documents that
    don't already declare hostnames, so the route lands in its own
    ``workspaces.<domain>`` virtual host. Without this the route stays in the
    shared wildcard vhost and is shadowed by the inference routes' exact-match
    vhost on ``workloads.<domain>`` → 404; the dedicated subdomain also keeps
    workspaces clear of the inference routes' cluster-auth gate.

    Returns the manifest unchanged when no host can be derived or there are no
    unpinned HTTPRoutes (so formatting is preserved in the common no-op case).
    """
    hostname = get_workspaces_hostname()
    if not hostname:
        logger.warning("WORKSPACES_HOST has no usable hostname; workspace routes left unpinned (may 404)")
        return manifest

    # Drop empty documents (Helm may emit `---` separators with only comments);
    # safe_load_all yields None for those and re-serializing them would inject
    # explicit `null` docs that break apply/create.
    docs = [doc for doc in yaml.safe_load_all(manifest) if doc is not None]
    changed = False
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == _HTTPROUTE_KIND and not doc.get("spec", {}).get("hostnames"):
            doc.setdefault("spec", {})["hostnames"] = [hostname]
            changed = True
            logger.debug(f"Pinned workspace HTTPRoute/{doc.get('metadata', {}).get('name', 'unknown')} to {hostname}")

    if not changed:
        return manifest
    return yaml.safe_dump_all(docs, sort_keys=False, default_flow_style=False, explicit_start=True)


async def check_workspace_availability_per_namespace(
    session: AsyncSession, namespace: str, workspace_type: WorkspaceType, creator_email: str
) -> bool:
    """
    Check if a workspace of the given type can be created in the namespace.

    For namespace-scoped workspace types (like MLFlow), only one instance is allowed per namespace.
    For user-scoped workspace types (like VSCode, Jupyter, ComfyUI), only one instance per user per namespace.

    Workspaces in PENDING, RUNNING, FAILED, or UNKNOWN status block creation.
    Users must explicitly delete failed workspaces before creating a new one of the same type.

    Args:
        session: Database session
        namespace: Kubernetes namespace
        workspace_type: Type of workspace (vscode, jupyter, etc.)
        creator_email: Email of the user creating the workspace

    Returns:
        True if workspace can be created, False if limit would be exceeded
    """
    target_chart_name = workspace_type_chart_name_mapping[workspace_type]
    existing_workspaces = await get_workloads(
        session=session,
        namespace=namespace,
        workload_types=[WorkloadType.WORKSPACE],
        status_filter=[WorkloadStatus.PENDING, WorkloadStatus.RUNNING, WorkloadStatus.FAILED, WorkloadStatus.UNKNOWN],
    )

    # Filter by workspace type - check if any existing workspace uses the same chart
    usage_scope = WORKSPACE_USAGE_SCOPE_MAPPING.get(workspace_type, WorkspaceUsageScope.USER)

    for workspace in existing_workspaces:
        if workspace.chart and workspace.chart.name == target_chart_name:
            if usage_scope == WorkspaceUsageScope.NAMESPACE:
                # Namespace-scoped (e.g., MLFlow): only 1 per namespace total
                return False
            elif workspace.created_by == creator_email:
                # User-scoped: only 1 per user per namespace (including failed ones)
                return False

    return True
