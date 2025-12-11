# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import AIMClusterModelStatus, WorkloadStatus

from ..managed_workloads.models import ManagedWorkload
from ..workloads.enums import WorkloadType
from .models import AIM


async def select_aim(session: AsyncSession, aim_id: UUID) -> AIM | None:
    """Get a specific AIM by ID."""
    result = await session.execute(select(AIM).where(AIM.id == aim_id))
    return result.scalar_one_or_none()


async def select_aims_with_workload(
    session: AsyncSession, project_id: UUID, statuses: list[AIMClusterModelStatus] | None = None
) -> list[tuple[AIM, ManagedWorkload | None]]:
    """Get all AIMs with their related workload in a specific project.

    Returns a list of tuples: (AIM, workload)
    - workload is None if the AIM is not deployed in the project

    Args:
        statuses: Optional list of AIMClusterModelStatus to filter by. If None, returns all AIMs.
    """
    query = (
        select(AIM, ManagedWorkload)
        .outerjoin(
            ManagedWorkload,
            (AIM.id == ManagedWorkload.aim_id)
            & (ManagedWorkload.project_id == project_id)
            & (ManagedWorkload.status.in_([WorkloadStatus.RUNNING.value, WorkloadStatus.PENDING.value])),
        )
        .order_by(AIM.image_reference)
    )

    if statuses:
        query = query.where(AIM.status.in_([s.value for s in statuses]))

    result = await session.execute(query)
    return list(result.unique().all())


async def select_aim_workload(
    session: AsyncSession,
    aim_id: UUID,
    project_id: UUID,
    type: list[WorkloadType] | None = None,
    status: list[WorkloadStatus] | None = None,
) -> ManagedWorkload | None:
    """Retrieve the active AIM workload for a specific AIM and project.

    Note:
        This function expects only one active workload per AIM per project (RUNNING or PENDING).
        Multiple terminated/deleted workloads may exist but only one should be active.
    """
    query = select(ManagedWorkload).where(ManagedWorkload.aim_id == aim_id, ManagedWorkload.project_id == project_id)
    if type:
        query = query.where(ManagedWorkload.type.in_(type))
    if status:
        # Convert list of WorkloadStatus enums to list of string values for DB query
        status_values = [s.value for s in status]
        query = query.where(ManagedWorkload.status.in_(status_values))

    result = await session.execute(query)
    workload = result.unique().scalar_one_or_none()

    # Convert status string back to enum if workload exists
    if workload:
        workload.status = WorkloadStatus(workload.status)
    return workload
