# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..charts.models import Chart
from .enums import WorkloadStatus, WorkloadType
from .models import Workload
from .utils import generate_display_name, generate_workload_name


async def create_workload(
    session: AsyncSession,
    display_name: str,
    workload_type: WorkloadType,
    chart_id: UUID,
    namespace: str,
    submitter: str,
    status: WorkloadStatus,
    model_id: UUID | None = None,
    dataset_id: UUID | None = None,
) -> Workload:
    """
    Create a new workload in the database.

    Args:
        session: Database session
        display_name: Human-readable display name (empty string to auto-generate)
        workload_type: Type of workload (WORKSPACE, INFERENCE, TRAINING, etc.)
        chart_id: ID of the chart used to create this workload
        namespace: Kubernetes namespace where workload is deployed
        submitter: Email of the user creating the workload
        status: Initial status of the workload
        model_id: Optional ID of the model associated with this workload
        dataset_id: Optional ID of the dataset associated with this workload

    Returns:
        Created Workload instance with auto-generated name
    """
    workload = Workload(
        name="",  # Will be generated after flush
        display_name=display_name,
        type=workload_type,
        status=status,
        chart_id=chart_id,
        namespace=namespace,
        created_by=submitter,
        updated_by=submitter,
        model_id=model_id,
        dataset_id=dataset_id,
    )
    session.add(workload)
    await session.flush()

    # Auto-generate name based on workload ID
    workload.name = generate_workload_name(workload)
    if not workload.display_name:
        workload.display_name = generate_display_name(workload)

    return workload


async def get_workload_by_id(session: AsyncSession, workload_id: UUID, namespace: str | None = None) -> Workload | None:
    """Get a workload by ID, optionally filtered by namespace."""
    query = select(Workload).where(Workload.id == workload_id)

    if namespace is not None:
        query = query.where(Workload.namespace == namespace)

    result = await session.execute(query)
    return result.scalars().first()


async def get_workloads(
    session: AsyncSession,
    namespace: str | None = None,
    workload_types: list[WorkloadType] | None = None,
    status_filter: list[WorkloadStatus] | None = None,
    chart_name: str | None = None,
) -> list[Workload]:
    """
    Get all workloads, optionally filtered by namespace, type, status, and chart.

    Args:
        session: Database session
        namespace: Filter by namespace
        workload_types: Filter by workload type(s)
        status_filter: Include only these statuses
        chart_name: Filter by chart name

    Returns:
        List of matching workloads
    """

    query = select(Workload)
    if namespace is not None:
        query = query.where(Workload.namespace == namespace)
    if workload_types:
        query = query.where(Workload.type.in_(workload_types))
    if status_filter:
        query = query.where(Workload.status.in_(status_filter))
    if chart_name:
        query = query.join(Chart).where(Chart.name == chart_name)

    result = await session.execute(query)
    return result.unique().scalars().all()


async def update_workload_status(
    session: AsyncSession, workload_id: UUID, status: WorkloadStatus, updated_by: str
) -> Workload | None:
    """
    Update the status of a workload.

    Args:
        session: Database session
        workload_id: ID of the workload to update
        status: New status
        updated_by: Email of user updating the status

    Returns:
        Updated workload or None if not found
    """
    workload = await get_workload_by_id(session, workload_id)
    if workload:
        workload.status = status
        workload.updated_by = updated_by
        await session.flush()
    return workload


async def delete_workload(session: AsyncSession, workload_id: UUID) -> bool:
    """
    Delete a workload from the database.

    Args:
        session: Database session
        workload_id: ID of the workload to delete

    Returns:
        True if deleted, False if not found
    """
    result = await session.execute(select(Workload).where(Workload.id == workload_id))
    workload = result.unique().scalar_one_or_none()
    if workload:
        await session.delete(workload)
        return True
    return False
