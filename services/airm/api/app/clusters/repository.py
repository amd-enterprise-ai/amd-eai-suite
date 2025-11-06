# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ClusterNode as ClusterNodeIn

from ..utilities.exceptions import ConflictException
from ..utilities.models import set_updated_fields
from .models import Cluster, ClusterNode
from .schemas import ClusterIn, ClusterNameEdit
from .utils import flatten_for_db_comparison


async def get_cluster_in_organization(session: AsyncSession, organization_id: UUID, cluster_id: UUID) -> Cluster | None:
    result = await session.execute(
        select(Cluster).where(Cluster.id == cluster_id, Cluster.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def get_clusters_in_organization(session: AsyncSession, organization_id: UUID) -> list[Cluster]:
    result = await session.execute(select(Cluster).where(Cluster.organization_id == organization_id))
    return result.scalars().all()


async def create_cluster(
    session: AsyncSession, organization_id: UUID, creator: str, cluster_create: ClusterIn
) -> Cluster:
    cluster = Cluster(
        organization_id=organization_id, created_by=creator, updated_by=creator, **cluster_create.model_dump()
    )
    session.add(cluster)
    await session.flush()
    return cluster


async def update_cluster(
    session: AsyncSession, cluster: Cluster, edits: ClusterIn | ClusterNameEdit, updater: str
) -> Cluster:
    for key, value in edits.model_dump(exclude_unset=True).items():
        setattr(cluster, key, value)
    set_updated_fields(cluster, updater)

    await session.flush()
    return cluster


async def delete_cluster(session: AsyncSession, cluster: Cluster) -> None:
    await session.delete(cluster)
    await session.flush()


async def get_cluster_by_id(session: AsyncSession, cluster_id: UUID) -> Cluster | None:
    result = await session.execute(select(Cluster).where(Cluster.id == cluster_id))
    return result.scalar()


async def update_last_heartbeat(session: AsyncSession, cluster: Cluster, last_heartbeat_at: datetime) -> None:
    cluster.last_heartbeat_at = last_heartbeat_at
    await session.flush()


async def get_cluster_nodes(session: AsyncSession, cluster: Cluster) -> list[ClusterNode]:
    result = await session.execute(select(ClusterNode).where(ClusterNode.cluster_id == cluster.id))
    return result.scalars().all()


async def get_all_cluster_nodes(session: AsyncSession) -> list[ClusterNode]:
    result = await session.execute(select(ClusterNode))
    return result.scalars().all()


async def get_cluster_nodes_in_organization(session: AsyncSession, organization_id: UUID) -> list[ClusterNode]:
    result = await session.execute(select(ClusterNode).join(Cluster).where(Cluster.organization_id == organization_id))
    return result.scalars().all()


async def get_cluster_nodes_by_cluster_ids(session: AsyncSession, cluster_ids: set[UUID]) -> list[ClusterNode]:
    result = await session.execute(select(ClusterNode).where(ClusterNode.cluster_id.in_(cluster_ids)))
    return result.scalars().all()


async def delete_cluster_nodes(session: AsyncSession, cluster_nodes: list[ClusterNode]) -> None:
    await session.execute(delete(ClusterNode).where(ClusterNode.id.in_([node.id for node in cluster_nodes])))
    await session.flush()


async def create_cluster_nodes(
    session: AsyncSession, cluster: Cluster, nodes: list[ClusterNodeIn], creator: str, created_at: datetime
) -> list[ClusterNode]:
    new_nodes = [
        ClusterNode(
            **flatten_for_db_comparison(node),
            cluster_id=cluster.id,
            updated_by=creator,
            created_by=creator,
            created_at=created_at,
            updated_at=created_at,
        )
        for node in nodes
    ]
    session.add_all(new_nodes)
    try:
        await session.flush()
        return new_nodes
    except IntegrityError as e:
        error_message = str(e)
        if "cluster_nodes_name_cluster_id_key" in error_message:
            raise ConflictException("One or more cluster nodes with the same name already exist in this cluster")
        raise e


async def update_cluster_node(
    session: AsyncSession, cluster_node: ClusterNode, edits: ClusterNodeIn, updater: str, updated_at: datetime
) -> ClusterNode:
    for key, value in flatten_for_db_comparison(edits).items():
        setattr(cluster_node, key, value)
    set_updated_fields(cluster_node, updater, updated_at)

    await session.flush()
    return cluster_node
