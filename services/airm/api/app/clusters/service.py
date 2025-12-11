# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from collections import defaultdict
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.connector import delete_connection_to_cluster_vhost
from airm.messaging.schemas import ClusterNodesMessage, HeartbeatMessage, QuotaStatus

from ..messaging.admin import create_vhost_and_user, delete_vhost_and_user
from ..messaging.queues import configure_queues_for_cluster
from ..messaging.sender import MessageSender
from ..organizations.models import Organization
from ..organizations.repository import get_organization_by_id
from ..projects.models import Project
from ..projects.repository import get_projects_in_cluster
from ..quotas.models import Quota
from ..quotas.repository import (
    get_quotas_for_cluster,
    get_quotas_for_organization,
)
from ..quotas.service import send_quotas_allocation_to_cluster_queue
from ..utilities.exceptions import (
    DeletionConflictException,
    ForbiddenException,
    NotFoundException,
    PreconditionNotMetException,
)
from ..utilities.keycloak_admin import KeycloakAdmin, get_client_secret, get_client_uuid, get_public_issuer_url
from .config import KUBE_API_KEYCLOAK_CLIENT_NAME
from .models import Cluster, ClusterNode
from .repository import create_cluster as create_cluster_in_db
from .repository import (
    create_cluster_nodes,
    delete_cluster_nodes,
    get_cluster_in_organization,
    get_cluster_nodes_in_organization,
    get_clusters_in_organization,
)
from .repository import delete_cluster as delete_cluster_in_db
from .repository import get_cluster_nodes as get_cluster_nodes_in_db
from .repository import update_cluster as update_cluster_in_db
from .repository import update_cluster_node as update_cluster_node_in_db
from .repository import update_last_heartbeat as update_last_heartbeat_in_db
from .schemas import (
    ClusterIn,
    ClusterKubeConfig,
    ClusterNameEdit,
    ClusterNodeResponse,
    ClusterNodes,
    ClusterResources,
    ClusterResponse,
    Clusters,
    ClustersStats,
    ClusterWithResources,
    ClusterWithUserSecret,
    GPUInfo,
)
from .utils import build_cluster_kube_config, has_node_changed


async def create_cluster(
    session: AsyncSession,
    organization_id: UUID,
    creator: str,
    cluster_create: ClusterIn,
) -> ClusterWithUserSecret:
    cluster = await create_cluster_in_db(session, organization_id, creator, cluster_create)
    user_secret = await create_vhost_and_user(cluster.id)
    await configure_queues_for_cluster(cluster.id)
    return ClusterWithUserSecret(
        **ClusterResponse.model_validate(cluster).model_dump(exclude={"status"}), user_secret=user_secret
    )


async def validate_cluster_accessible_to_user(
    accessible_projects: list[Project],
    cluster_id: UUID,
) -> None:
    if cluster_id not in {project.cluster_id for project in accessible_projects}:
        raise ForbiddenException(f"Cluster with ID {cluster_id} is not accessible")


async def update_cluster(session: AsyncSession, cluster: Cluster, edits: ClusterIn, updater: str) -> Cluster:
    return await update_cluster_in_db(session, cluster, edits, updater)


async def get_clusters_with_resources(session: AsyncSession, organization: Organization) -> Clusters:
    clusters, quotas, nodes = await asyncio.gather(
        get_clusters_in_organization(session, organization.id),
        get_quotas_for_organization(session, organization.id),
        get_cluster_nodes_in_organization(session, organization.id),
    )
    return __compute_clusters_resources(clusters, quotas, nodes)


async def get_clusters_stats(session: AsyncSession, organization_id: UUID) -> ClustersStats:
    clusters, quotas, nodes = await asyncio.gather(
        get_clusters_in_organization(session, organization_id),
        get_quotas_for_organization(session, organization_id),
        get_cluster_nodes_in_organization(session, organization_id),
    )
    # Filter out DELETING and DELETED quotas to keep consistent with dynamic quota calculation
    allocated_quotas = [q for q in quotas if q.status not in [QuotaStatus.DELETING, QuotaStatus.DELETED]]
    return ClustersStats(
        total_cluster_count=len(clusters),
        total_node_count=len(nodes),
        available_node_count=len([n for n in nodes if n.is_ready]),
        total_gpu_node_count=len([n for n in nodes if n.gpu_count > 0]),
        total_gpu_count=sum(n.gpu_count for n in nodes),
        available_gpu_count=sum(n.gpu_count for n in nodes if n.is_ready),
        allocated_gpu_count=sum(q.gpu_count for q in allocated_quotas),
    )


async def get_cluster_with_resources(session: AsyncSession, cluster: Cluster) -> ClusterWithResources:
    nodes, quotas = await asyncio.gather(
        get_cluster_nodes_in_db(session, cluster),
        get_quotas_for_cluster(session, cluster.id),
    )
    return __compute_cluster_resources(cluster, quotas, nodes)


def __compute_clusters_resources(clusters: list[Cluster], quotas: list[Quota], nodes: list[ClusterNode]) -> Clusters:
    nodes_by_cluster_id = defaultdict(list)
    quotas_by_cluster_id = defaultdict(list)
    for node in nodes:
        nodes_by_cluster_id[node.cluster_id].append(node)
    for quota in quotas:
        quotas_by_cluster_id[quota.cluster_id].append(quota)

    results = []
    for cluster in clusters:
        results.append(
            __compute_cluster_resources(cluster, quotas_by_cluster_id[cluster.id], nodes_by_cluster_id[cluster.id])
        )
    return Clusters(clusters=results)


def __compute_cluster_resources(
    cluster: Cluster, quotas: list[Quota], nodes: list[ClusterNode]
) -> ClusterWithResources:
    available_nodes = [n for n in nodes if n.is_ready]

    # Filter out DELETING and DELETED quotas
    allocated_quotas = [q for q in quotas if q.status not in [QuotaStatus.DELETING, QuotaStatus.DELETED]]

    available_resources = ClusterResources(
        cpu_milli_cores=sum(n.cpu_milli_cores for n in available_nodes),
        memory_bytes=sum(n.memory_bytes for n in available_nodes),
        ephemeral_storage_bytes=sum(n.ephemeral_storage_bytes for n in available_nodes),
        gpu_count=sum(n.gpu_count for n in available_nodes),
    )

    allocated_resources = ClusterResources(
        cpu_milli_cores=sum(q.cpu_milli_cores for q in allocated_quotas),
        memory_bytes=sum(q.memory_bytes for q in allocated_quotas),
        ephemeral_storage_bytes=sum(q.ephemeral_storage_bytes for q in allocated_quotas),
        gpu_count=sum(q.gpu_count for q in allocated_quotas),
    )

    gpu_node = next((n for n in nodes if n.gpu_count > 0), None)
    gpu_vendor = gpu_node.gpu_vendor if gpu_node else None
    gpu_type = gpu_node.gpu_type if gpu_node else None
    gpu_vram_bytes = gpu_node.gpu_vram_bytes_per_device if gpu_node else 0
    gpu_name = gpu_node.gpu_product_name if gpu_node else None

    return ClusterWithResources(
        **ClusterResponse.model_validate(cluster).model_dump(exclude={"status"}),
        available_resources=available_resources,
        allocated_resources=allocated_resources,
        gpu_info=(
            GPUInfo(vendor=gpu_vendor, type=gpu_type, memory_bytes_per_device=gpu_vram_bytes, name=gpu_name)
            if gpu_node
            else None
        ),
        total_node_count=len(nodes),
        available_node_count=len(available_nodes),
        assigned_quota_count=len(allocated_quotas),
    )


async def update_last_heartbeat(session: AsyncSession, cluster: Cluster, message: HeartbeatMessage) -> None:
    cluster_name = message.cluster_name
    organization_name = message.organization_name
    last_heartbeat_at = message.last_heartbeat_at

    if cluster.name is None or cluster.name.lower() != cluster_name.lower():
        organization = await get_organization_by_id(session, cluster.organization_id)

        if not organization or organization_name.lower() != organization.name.lower():
            logger.error(f"Organization {organization_name} mismatch with cluster's organization")
            return

        cluster_info = ClusterNameEdit(name=cluster_name)
        cluster = await update_cluster_in_db(session, cluster, cluster_info, "system")

    if cluster.last_heartbeat_at is None or last_heartbeat_at > cluster.last_heartbeat_at:
        await update_last_heartbeat_in_db(session, cluster, last_heartbeat_at)


async def delete_cluster(session: AsyncSession, cluster: Cluster) -> None:
    projects = await get_projects_in_cluster(session, cluster.id)
    if len(projects) > 0:
        raise DeletionConflictException(
            f"Cannot delete cluster {cluster.name} ({cluster.id}) because it has associated projects"
        )
    await delete_connection_to_cluster_vhost(cluster.id)
    await delete_cluster_in_db(session, cluster)
    await delete_vhost_and_user(cluster.id)


async def update_cluster_nodes(
    session: AsyncSession, cluster: Cluster, message: ClusterNodesMessage, message_sender: MessageSender
) -> None:
    existing_nodes = await get_cluster_nodes_in_db(session, cluster)
    existing_nodes_by_name = {node.name.lower(): node for node in existing_nodes}

    nodes_to_create = []
    nodes_changed = False

    for node in message.cluster_nodes:
        existing_node = existing_nodes_by_name.pop(node.name.lower(), None)
        if not existing_node:
            nodes_to_create.append(node)
            nodes_changed = True
            continue

        # Outdated message
        if existing_node.updated_at >= message.updated_at:
            continue

        if has_node_changed(node, existing_node):
            await update_cluster_node_in_db(session, existing_node, node, "system", message.updated_at)
            nodes_changed = True

    if nodes_to_create:
        await create_cluster_nodes(session, cluster, nodes_to_create, "system", message.updated_at)

    if existing_nodes_by_name:
        await delete_cluster_nodes(session, list(existing_nodes_by_name.values()))
        nodes_changed = True

    if nodes_changed:
        cluster_with_resources = await get_cluster_with_resources(session, cluster)
        gpu_vendor = cluster_with_resources.gpu_info.vendor if cluster_with_resources.gpu_info else None

        await send_quotas_allocation_to_cluster_queue(session, cluster, gpu_vendor, message_sender)

        logger.info(f"Updated quota allocations for cluster {cluster.name} ({cluster.id}) due to node changes")


async def get_cluster_nodes(session: AsyncSession, cluster: Cluster) -> ClusterNodes:
    cluster_nodes = await get_cluster_nodes_in_db(session, cluster)
    return ClusterNodes(
        cluster_nodes=[
            ClusterNodeResponse.model_validate(cluster_node).model_copy(
                update={
                    "gpu_info": (
                        GPUInfo(
                            vendor=cluster_node.gpu_vendor,
                            type=cluster_node.gpu_type,
                            memory_bytes_per_device=cluster_node.gpu_vram_bytes_per_device,
                            name=cluster_node.gpu_product_name,
                        )
                        if cluster_node.gpu_count > 0
                        else None
                    )
                }
            )
            for cluster_node in cluster_nodes
        ]
    )


async def get_cluster_by_id(session: AsyncSession, organization_id: UUID, cluster_id: UUID) -> Cluster:
    """Get a cluster by ID in organization, raising NotFoundException if not found."""
    cluster = await get_cluster_in_organization(session, organization_id, cluster_id)
    if not cluster:
        raise NotFoundException(f"Cluster with ID {cluster_id} not found in your organization")
    return cluster


async def get_cluster_kubeconfig_as_yaml(cluster: Cluster, kc_admin: KeycloakAdmin) -> ClusterKubeConfig:
    if not cluster.kube_api_url:
        raise ValueError(f"Cluster {cluster.name} does not have a kube_api_url configured")
    client_uuid = await get_client_uuid(kc_admin=kc_admin, client_id=KUBE_API_KEYCLOAK_CLIENT_NAME)
    credentials = await get_client_secret(kc_admin=kc_admin, client_uuid=client_uuid)
    if not credentials or "value" not in credentials:
        raise PreconditionNotMetException(f"Client {KUBE_API_KEYCLOAK_CLIENT_NAME} doesn't have secret configured")
    return build_cluster_kube_config(cluster, get_public_issuer_url(), credentials["value"])
