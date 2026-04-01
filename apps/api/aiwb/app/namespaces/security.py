# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Security and access control for namespace operations."""

from fastapi import Depends, HTTPException, status

from api_common.auth.security import get_user_groups

from ..config import STANDALONE_MODE
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from .config import DEFAULT_NAMESPACE
from .crds import Namespace
from .gateway import get_namespace


def is_valid_workbench_namespace(ns: Namespace, user_groups: list[str]) -> bool:
    """Check if a namespace is a valid, accessible workbench namespace.

    In standalone mode: only the default namespace is accessible
    In combined mode: user must have namespace in their JWT groups

    Criteria:
    - Namespace has project-id label (identifies it as a workbench namespace)
    - In standalone mode: namespace must be the default workbench namespace
    - In combined mode: user has namespace in their JWT groups
    """
    if ns.id is None:
        return False

    if STANDALONE_MODE:
        # In standalone mode, only allow access to the default namespace
        return ns.name == DEFAULT_NAMESPACE

    return ns.name in user_groups


async def _validate_namespace(namespace: str, user_groups: list[str], kube_client: KubernetesClient) -> Namespace:
    """Validate namespace access, raising HTTPException with specific error messages.

    In standalone mode: only the default namespace is accessible
    In combined mode: enforces group-based namespace access
    """
    if STANDALONE_MODE:
        # In standalone mode, only allow access to the default namespace
        if namespace != DEFAULT_NAMESPACE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"In standalone mode, only namespace '{DEFAULT_NAMESPACE}' is accessible",
            )
    else:
        # In combined mode, check if user has namespace in their groups
        if namespace not in user_groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have access to namespace '{namespace}'",
            )

    # Validate namespace exists and has required labels
    ns_data = await get_namespace(kube_client, namespace)
    if not ns_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Namespace '{namespace}' not found",
        )

    # Check for project-id label - this identifies it as a workbench namespace
    if not ns_data.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Namespace '{namespace}' is not a workbench namespace (missing project-id label)",
        )

    return ns_data


async def ensure_access_to_workbench_namespace(
    namespace: str,
    user_groups: list[str] = Depends(get_user_groups),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> str:
    ns_data = await _validate_namespace(namespace, user_groups, kube_client)
    return ns_data.name


async def get_workbench_namespace(
    namespace: str,
    user_groups: list[str] = Depends(get_user_groups),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> Namespace:
    ns_data = await _validate_namespace(namespace, user_groups, kube_client)
    return ns_data
