# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Gateway layer for namespace access and validation."""

from kubernetes_asyncio.client import ApiException
from loguru import logger

from ..dispatch.kube_client import KubernetesClient
from .crds import Namespace


async def get_namespace(kube_client: KubernetesClient, name: str) -> Namespace | None:
    """Get a specific namespace by name.

    Returns:
        Namespace instance if found, None if namespace doesn't exist
    """
    try:
        ns = await kube_client.core_v1.read_namespace(name)
        return Namespace(
            name=ns.metadata.name,
            labels=ns.metadata.labels or {},
            annotations=ns.metadata.annotations or {},
            created_at=ns.metadata.creation_timestamp,
        )
    except ApiException as e:
        if e.status == 404:
            return None
        logger.error(f"Failed to get namespace {name}: {e}")
        raise


async def get_namespaces(kube_client: KubernetesClient) -> list[Namespace]:
    """Get namespaces where user has access based on JWT groups."""
    try:
        namespaces = await kube_client.core_v1.list_namespace()
        return [
            Namespace(
                name=ns.metadata.name,
                labels=ns.metadata.labels or {},
                annotations=ns.metadata.annotations or {},
                created_at=ns.metadata.creation_timestamp,
            )
            for ns in namespaces.items
        ]
    except ApiException as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise
