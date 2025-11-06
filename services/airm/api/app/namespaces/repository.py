# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import NamespaceStatus

from ..projects.models import Project
from ..utilities.models import set_updated_fields
from .models import Namespace


async def create_namespace(session: AsyncSession, namespace: Namespace) -> Namespace:
    session.add(namespace)
    await session.flush()
    return namespace


async def update_namespace_status(
    session: AsyncSession,
    namespace: Namespace,
    status: NamespaceStatus,
    status_reason: str,
    updater: str,
    updated_at: datetime | None = None,
) -> Namespace:
    namespace.status = status
    namespace.status_reason = status_reason
    set_updated_fields(namespace, updater, updated_at)
    await session.flush()
    return namespace


async def get_namespace_by_project_and_cluster(
    session: AsyncSession, project_id: UUID, cluster_id: UUID
) -> Namespace | None:
    result = await session.execute(
        select(Namespace).where(Namespace.project_id == project_id, Namespace.cluster_id == cluster_id)
    )
    return result.scalars().first()


async def get_namespaces_by_organisation(session: AsyncSession, organization_id: UUID) -> list[Namespace]:
    result = await session.execute(
        select(Namespace)
        .join(Project, Namespace.project_id == Project.id)
        .where(Project.organization_id == organization_id)
        .order_by(Namespace.cluster_id)
    )
    return result.scalars().all()


async def delete_namespace(session: AsyncSession, namespace: Namespace) -> None:
    await session.delete(namespace)
    await session.flush()
