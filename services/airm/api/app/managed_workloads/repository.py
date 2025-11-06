# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..charts.models import Chart
from ..projects.models import Project
from ..workloads.enums import WorkloadType
from .enums import WorkloadStatus
from .models import ManagedWorkload
from .schemas import AIMWorkloadCreate, ChartWorkloadCreate
from .utils import generate_display_name, generate_workload_name


async def insert_workload(
    session: AsyncSession, creator: str, project: Project, workload_data: ChartWorkloadCreate | AIMWorkloadCreate
) -> ManagedWorkload:
    """
    Create a new managed workload in the database.

    Raises:
        ConflictException: If database constraint violation occurs during creation
    """

    workload = ManagedWorkload(
        created_by=creator,
        updated_by=creator,
        cluster_id=project.cluster.id,
        project_id=project.id,
        status=WorkloadStatus.PENDING.value,
        **workload_data.model_dump(),
    )
    session.add(workload)
    await session.flush()

    workload.name = generate_workload_name(workload)
    if not workload.display_name:
        workload.display_name = generate_display_name(workload)
    await session.flush()
    return workload


async def select_workload(
    session: AsyncSession, workload_id: UUID, accessible_projects: list[Project]
) -> ManagedWorkload | None:
    """
    Retrieve a workload that the user has access to through project membership.

    Note:
        Access is determined by project membership - user must have access to the project containing the workload.
    """
    if not accessible_projects:
        return None

    project_ids = [project.id for project in accessible_projects]
    result = await session.execute(
        select(ManagedWorkload).join(Project).where(ManagedWorkload.id == workload_id, Project.id.in_(project_ids))
    )
    workload = result.scalars().first()
    if workload:
        workload.status = WorkloadStatus(workload.status)
    return workload


async def select_workloads(
    session: AsyncSession,
    project_id: UUID,
    type: list[WorkloadType] | None = None,
    status: list[WorkloadStatus] | None = None,
    chart_name: str | None = None,
    aim_ids: list[UUID] | None = None,
) -> list[ManagedWorkload]:
    """
    Retrieve workloads from a specific project with optional filtering.

    Note:
        Status enum conversion is performed on each returned workload for consistency with the service layer.
    """
    query = select(ManagedWorkload).where(ManagedWorkload.project_id == project_id)
    if type:
        query = query.where(ManagedWorkload.type.in_(type))
    if status:
        # Convert list of WorkloadStatus enums to list of string values for DB query
        status_values = [s.value for s in status]
        query = query.where(ManagedWorkload.status.in_(status_values))
    if chart_name:
        # Join with Chart table to filter by chart name
        query = query.join(Chart).where(Chart.name == chart_name)
    if aim_ids:
        query = query.where(ManagedWorkload.aim_id.in_(aim_ids))
    results = await session.execute(query)
    workloads = list(results.scalars().unique())

    # Convert status strings back to enums
    for workload in workloads:
        workload.status = WorkloadStatus(workload.status)
    return workloads
