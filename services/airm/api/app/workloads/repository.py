# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import case

from airm.messaging.schemas import CommonComponentStatus, WorkloadStatus

from ..projects.models import Project
from ..utilities.collections.queries import (
    apply_filter_to_query,
    apply_pagination_to_query,
    apply_sorting_to_query,
    get_count_query,
)
from ..utilities.collections.schemas import FilterCondition, PaginationConditions, SortCondition
from ..utilities.exceptions import ConflictException
from ..utilities.models import set_updated_fields
from .enums import WorkloadType
from .models import Workload, WorkloadComponent, WorkloadTimeSummary
from .schemas import WorkloadComponentIn


async def create_workload(
    session: AsyncSession,
    cluster_id: UUID,
    project_id: UUID,
    status: str,
    creator: str,
    workload_type: WorkloadType,
    display_name: str | None = None,
    workload_id: UUID | None = None,
) -> Workload:
    workload = Workload(
        id=workload_id,
        cluster_id=cluster_id,
        project_id=project_id,
        status=status,
        created_by=creator,
        updated_by=creator,
        type=workload_type.value,
        display_name=display_name,
    )
    session.add(workload)
    await session.flush()
    return workload


async def get_workload_by_id_in_cluster(session: AsyncSession, workload_id: UUID, cluster_id: UUID) -> Workload | None:
    result = await session.execute(
        select(Workload).where(Workload.cluster_id == cluster_id, Workload.id == workload_id)
    )
    return result.scalar_one_or_none()


async def update_workload_status(
    session: AsyncSession, workload: Workload, status: str, updated_at: datetime, updated_by: str
):
    workload.status = status
    workload.updated_at = updated_at
    workload.updated_by = updated_by
    workload.last_status_transition_at = updated_at
    await session.flush()


async def get_workloads_by_project(session: AsyncSession, project_id: UUID) -> list[Workload]:
    result = await session.execute(select(Workload).where(Workload.project_id == project_id))
    return result.scalars().all()


async def get_workloads_accessible_to_user(session: AsyncSession, accessible_projects: list[Project]) -> list[Workload]:
    """
    Get workloads accessible to user based on project membership.

    Args:
        session: Database session
        accessible_projects: List of projects the user has access to (from Keycloak groups)

    Returns:
        List of workloads in the accessible projects
    """
    if not accessible_projects:
        return []

    project_ids = [project.id for project in accessible_projects]
    result = await session.execute(select(Workload).join(Project).where(Project.id.in_(project_ids)))
    return result.scalars().all()


async def get_workload_by_id_and_user_membership(
    session: AsyncSession, workload_id: UUID, accessible_projects: list[Project]
) -> Workload | None:
    """
    Get workload by ID if user has access to it through project membership.

    Args:
        session: Database session
        workload_id: ID of the workload to retrieve
        accessible_projects: List of projects the user has access to (from Keycloak groups)

    Returns:
        Workload if accessible, None otherwise
    """
    if not accessible_projects:
        return None

    project_ids = [project.id for project in accessible_projects]
    result = await session.execute(
        select(Workload).join(Project).where(Workload.id == workload_id, Project.id.in_(project_ids))
    )
    return result.scalar_one_or_none()


async def get_workload_by_id_in_organization(
    session: AsyncSession, workload_id: UUID, organization_id: UUID
) -> Workload | None:
    result = await session.execute(
        select(Workload).join(Project).where(Workload.id == workload_id, Project.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def get_active_workload_count_by_project(session: AsyncSession, project_id: UUID) -> int:
    """Return the number of active workloads for a project."""
    count_workload = select(func.count(Workload.id).label("workload_count")).where(
        Workload.project_id == project_id,
        ~Workload.status.in_(
            [WorkloadStatus.COMPLETE.value, WorkloadStatus.DELETED.value, WorkloadStatus.TERMINATED.value]
        ),
    )

    result = await session.execute(count_workload)
    return result.scalar_one()


async def create_workload_component(
    session: AsyncSession,
    component: WorkloadComponentIn,
    creator: str,
) -> WorkloadComponent:
    components = await create_workload_components(session, [component], creator)
    return components[0]


async def create_workload_components(
    session: AsyncSession,
    components: list[WorkloadComponentIn],
    creator: str,
) -> list[WorkloadComponent]:
    workload_components = []
    for component in components:
        workload_component = WorkloadComponent(
            status=CommonComponentStatus.REGISTERED.value,
            created_by=creator,
            updated_by=creator,
            **component.model_dump(),
        )
        workload_components.append(workload_component)

    session.add_all(workload_components)
    await session.flush()
    return workload_components


async def get_workload_components_by_workload_id(session: AsyncSession, workload_id: UUID) -> list[WorkloadComponent]:
    result = await session.execute(select(WorkloadComponent).where(WorkloadComponent.workload_id == workload_id))
    return result.scalars().all()


async def get_workload_component_by_id(
    session: AsyncSession, component_id: UUID, workload_id: UUID
) -> WorkloadComponent | None:
    result = await session.execute(
        select(WorkloadComponent).where(
            WorkloadComponent.id == component_id, WorkloadComponent.workload_id == workload_id
        )
    )
    return result.scalar_one_or_none()


async def update_workload_component_status(
    session: AsyncSession,
    component: WorkloadComponent,
    status: str,
    status_reason: str | None,
    updated_at: datetime,
    updated_by: str,
):
    component.status = status
    component.status_reason = status_reason
    component.updated_at = updated_at
    component.updated_by = updated_by
    await session.flush()
    return component


async def get_workloads_with_status_in_cluster_count(
    session: AsyncSession, cluster_id: UUID, statuses: list[WorkloadStatus]
) -> dict[WorkloadStatus, int]:
    stmt = (
        select(Workload.status, func.count())
        .select_from(Workload)
        .where(Workload.cluster_id == cluster_id, Workload.status.in_([w.value for w in statuses]))
        .group_by(Workload.status)
    )
    result = await session.execute(stmt)
    return {WorkloadStatus(status): count for status, count in result.all()}


async def get_workloads_with_status_in_project_count(
    session: AsyncSession, project_id: UUID, statuses: list[WorkloadStatus]
) -> dict[WorkloadStatus, int]:
    stmt = (
        select(Workload.status, func.count())
        .select_from(Workload)
        .where(Workload.project_id == project_id, Workload.status.in_([w.value for w in statuses]))
        .group_by(Workload.status)
    )
    result = await session.execute(stmt)
    return {WorkloadStatus(status): count for status, count in result.all()}


async def get_workloads_with_status_in_organization_count(
    session: AsyncSession, organization_id: UUID, statuses: list[WorkloadStatus]
) -> dict[WorkloadStatus, int]:
    stmt = (
        select(Workload.status, func.count())
        .select_from(Workload)
        .join(Project)
        .where(Project.organization_id == organization_id, Workload.status.in_([w.value for w in statuses]))
        .group_by(Workload.status)
    )
    result = await session.execute(stmt)
    return {WorkloadStatus(status): count for status, count in result.all()}


async def get_workload_counts_with_status_by_project_id(
    session: AsyncSession, organization_id: UUID, statuses: list[WorkloadStatus]
) -> dict[tuple[UUID, WorkloadStatus], int]:
    stmt = (
        select(Workload.project_id, Workload.status, func.count())
        .select_from(Workload)
        .join(Project)
        .where(Project.organization_id == organization_id, Workload.status.in_([w.value for w in statuses]))
    ).group_by(Workload.project_id, Workload.status)
    result = await session.execute(stmt)

    return {(project_id, WorkloadStatus(status)): count for project_id, status, count in result.all()}


async def get_workload_time_summary_by_workload_id_and_status(
    session: AsyncSession, workload_id: UUID, status: str
) -> WorkloadTimeSummary | None:
    result = await session.execute(
        select(WorkloadTimeSummary).where(
            WorkloadTimeSummary.workload_id == workload_id, WorkloadTimeSummary.status == status
        )
    )
    return result.scalar_one_or_none()


async def get_last_updated_workload_time_summary_by_workload_id(
    session: AsyncSession, workload_id: UUID
) -> WorkloadTimeSummary | None:
    result = await session.execute(
        select(WorkloadTimeSummary)
        .where(WorkloadTimeSummary.workload_id == workload_id)
        .order_by(WorkloadTimeSummary.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def increment_total_elapsed_seconds(
    session: AsyncSession, workload_time_summary: WorkloadTimeSummary, increment_seconds: float
):
    workload_time_summary.total_elapsed_seconds += increment_seconds
    set_updated_fields(workload_time_summary, "system")
    await session.flush()


async def insert_workload_time_summary(
    session: AsyncSession, workload_id: UUID, status: str, total_elapsed_seconds: float
) -> WorkloadTimeSummary:
    summary = WorkloadTimeSummary(
        workload_id=workload_id,
        status=status,
        total_elapsed_seconds=total_elapsed_seconds,
    )
    session.add(summary)
    try:
        await session.flush()
        return summary
    except IntegrityError as e:
        error_message = str(e)
        if "workload_time_summaries_workload_id_status_key" in error_message:
            raise ConflictException(f"A time summary already exists for workload status '{status}'")
        raise e


async def get_workloads_with_running_time_in_project(
    session: AsyncSession,
    project_id: UUID,
    pagination_params: PaginationConditions,
    sort_params: list[SortCondition],
    filter_conditions: list[FilterCondition],
) -> tuple[list[tuple[Workload, int]], int]:
    now = func.now()

    stmt = (
        select(
            Workload,
            case(
                (
                    Workload.status == WorkloadStatus.RUNNING.value,
                    func.extract("epoch", now - Workload.last_status_transition_at),
                ),
                else_=0,
            ).label("additional_running_time"),
            WorkloadTimeSummary.total_elapsed_seconds.label("running_time_summary"),
        )
        .outerjoin(
            WorkloadTimeSummary,
            (Workload.id == WorkloadTimeSummary.workload_id)
            & (WorkloadTimeSummary.status == WorkloadStatus.RUNNING.value),
        )
        .where(Workload.project_id == project_id)
    )

    filter_query = apply_filter_to_query(stmt, filter_conditions, [Workload, WorkloadTimeSummary])
    pagainated_query = apply_pagination_to_query(filter_query, pagination_params)
    sorted_query = apply_sorting_to_query(pagainated_query, sort_params, [Workload, WorkloadTimeSummary])

    count_query = get_count_query(filter_query)
    count_result = await session.execute(count_query)
    total_count = count_result.scalar_one()

    result = await session.execute(sorted_query)
    workloads_with_running_time = []
    for workload, additional_running_time, running_time_summary in result.all():
        total_running_time = (running_time_summary or 0) + (additional_running_time or 0)
        workloads_with_running_time.append((workload, total_running_time))

    return workloads_with_running_time, total_count


async def get_average_pending_time_for_workloads_in_project_created_between(
    session: AsyncSession,
    project_id: UUID,
    start_date: datetime,
    end_date: datetime,
) -> float | None:
    now = func.now()
    stmt = (
        select(
            func.avg(
                case(
                    (
                        Workload.status == WorkloadStatus.PENDING.value,
                        func.extract("epoch", now - Workload.last_status_transition_at)
                        + func.coalesce(WorkloadTimeSummary.total_elapsed_seconds, 0),
                    ),
                    else_=WorkloadTimeSummary.total_elapsed_seconds,
                )
            )
        )
        .select_from(Workload)
        .outerjoin(
            WorkloadTimeSummary,
            (Workload.id == WorkloadTimeSummary.workload_id)
            & (WorkloadTimeSummary.status == WorkloadStatus.PENDING.value),
        )
        .where(
            Workload.project_id == project_id,
            Workload.created_at >= start_date,
            Workload.created_at <= end_date,
        )
    )

    result = await session.execute(stmt)
    return result.scalar()
