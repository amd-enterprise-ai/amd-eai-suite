# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    AutoDiscoveredWorkloadComponentMessage,
    DeleteWorkloadMessage,
    WorkloadComponentStatusMessage,
    WorkloadMessage,
    WorkloadStatus,
    WorkloadStatusMessage,
)

from ..clusters.models import Cluster
from ..messaging.sender import MessageSender
from ..projects.models import Project
from ..utilities.exceptions import ConflictException
from .enums import WorkloadType
from .models import Workload
from .repository import create_workload as create_workload_in_db
from .repository import create_workload_component as create_workload_component_in_db
from .repository import create_workload_components as create_workload_components_in_db
from .repository import (
    get_workload_by_id_in_cluster,
    get_workload_component_by_id,
    get_workload_components_by_workload_id,
    get_workload_time_summary_by_workload_id_and_status,
    get_workloads_with_status_in_cluster_count,
    get_workloads_with_status_in_organization_count,
    get_workloads_with_status_in_project_count,
    increment_total_elapsed_seconds,
    insert_workload_time_summary,
)
from .repository import get_workloads_accessible_to_user as get_workloads_accessible_to_user_from_db
from .repository import get_workloads_by_project as get_workloads_by_project_in_db
from .repository import update_workload_component_status as update_workload_component_status_in_db
from .repository import update_workload_status as update_workload_status_in_db
from .schemas import (
    ProjectWorkloadsStats,
    WorkloadComponent,
    WorkloadComponentIn,
    WorkloadResponse,
    Workloads,
    WorkloadsStats,
    WorkloadStatusCount,
    WorkloadWithComponents,
)
from .utils import (
    extract_workload_components_from_manifest,
    get_workload_component_for_status_update,
    inject_workload_metadata_to_manifest,
    resolve_workload_status,
)


async def extract_components_and_submit_workload(
    session: AsyncSession,
    workload: Workload,
    project: Project,
    manifest: list[dict],
    creator: str,
    token: str,
    message_sender: MessageSender,
) -> None:
    components_with_manifests = extract_workload_components_from_manifest(manifest, workload.id)
    # Separate the list into components and manifests lists
    components, manifests = zip(*components_with_manifests)

    # Save the components
    db_components = await create_workload_components_in_db(
        session=session,
        components=list(components),
        creator=creator,
    )

    # Match up the db components with the manifests based on the indexes in the lists
    db_components_with_manifests = list(zip(db_components, manifests))

    workload_manifest = inject_workload_metadata_to_manifest(workload.id, project, db_components_with_manifests)

    message = WorkloadMessage(
        message_type="workload", manifest=workload_manifest, user_token=token, workload_id=workload.id
    )
    await message_sender.enqueue(project.cluster_id, message)


async def create_and_submit_workload(
    session: AsyncSession,
    project: Project,
    manifest: list[dict],
    creator: str,
    token: str,
    workload_type: WorkloadType,
    display_name: str,
    message_sender: MessageSender,
) -> WorkloadResponse:
    workload = await create_workload_in_db(
        session=session,
        cluster_id=project.cluster_id,
        project_id=project.id,
        status=WorkloadStatus.PENDING.value,
        creator=creator,
        workload_type=workload_type,
        display_name=display_name,
    )
    await extract_components_and_submit_workload(session, workload, project, manifest, creator, token, message_sender)
    return WorkloadResponse.model_validate(workload)


async def submit_delete_workload(
    session: AsyncSession, workload: WorkloadResponse, user: str, message_sender: MessageSender
) -> None:
    if workload.status == WorkloadStatus.DELETING:
        raise ConflictException("Workload is already marked for deletion")
    elif workload.status == WorkloadStatus.DELETED:
        raise ConflictException("Workload has already been deleted")

    if workload.updated_at > workload.last_status_transition_at:
        duration_in_status = workload.updated_at - workload.last_status_transition_at
    else:
        duration_in_status = datetime.now(UTC) - workload.updated_at

    await increment_workload_time_summary(session, workload.id, workload.status, duration_in_status)
    await update_workload_status_in_db(session, workload, WorkloadStatus.DELETING.value, datetime.now(UTC), user)

    message = DeleteWorkloadMessage(message_type="delete_workload", workload_id=workload.id)
    await message_sender.enqueue(workload.cluster_id, message)


async def get_workload_with_components(session: AsyncSession, workload: WorkloadResponse) -> WorkloadWithComponents:
    components = await get_workload_components_by_workload_id(session, workload.id)
    return WorkloadWithComponents.model_validate(
        WorkloadResponse.model_validate(workload).model_copy(
            update={"components": [WorkloadComponent.model_validate(c) for c in components]}
        )
    )


async def get_stats_for_workloads_in_cluster(session: AsyncSession, cluster: Cluster) -> WorkloadsStats:
    workloads_counts = await get_workloads_with_status_in_cluster_count(
        session, cluster.id, [WorkloadStatus.RUNNING, WorkloadStatus.PENDING]
    )
    return WorkloadsStats(
        running_workloads_count=workloads_counts.get(WorkloadStatus.RUNNING, 0),
        pending_workloads_count=workloads_counts.get(WorkloadStatus.PENDING, 0),
    )


async def get_stats_for_workloads_in_organization(session: AsyncSession, organization_id: UUID) -> WorkloadsStats:
    workloads_counts = await get_workloads_with_status_in_organization_count(
        session, organization_id, [WorkloadStatus.RUNNING, WorkloadStatus.PENDING]
    )
    return WorkloadsStats(
        running_workloads_count=workloads_counts.get(WorkloadStatus.RUNNING, 0),
        pending_workloads_count=workloads_counts.get(WorkloadStatus.PENDING, 0),
    )


async def update_workload_status(
    session: AsyncSession, cluster: Cluster, workload_status: WorkloadStatusMessage
) -> None:
    workload = await get_workload_by_id_in_cluster(session, workload_status.workload_id, cluster.id)

    if workload is None:
        logger.warning(f"Workload {workload_status.workload_id} not found in cluster {cluster.id}")
        return

    if workload.updated_at < workload_status.updated_at:
        await increment_workload_time_summary(
            session, workload.id, workload.status, workload_status.updated_at - workload.updated_at
        )
        await update_workload_status_in_db(
            session, workload, workload_status.status, workload_status.updated_at, "system"
        )


async def get_workloads_by_project(session: AsyncSession, project_id: UUID) -> Workloads:
    db_workloads = await get_workloads_by_project_in_db(session, project_id)
    return Workloads(data=[WorkloadResponse.model_validate(workload) for workload in db_workloads])


async def get_workloads_accessible_to_user(session: AsyncSession, accessible_projects: list[Project]) -> Workloads:
    db_workloads = await get_workloads_accessible_to_user_from_db(session, accessible_projects)
    return Workloads(data=[WorkloadResponse.model_validate(workload) for workload in db_workloads])


async def update_workload_component_status(
    session: AsyncSession, cluster: Cluster, message: WorkloadComponentStatusMessage
) -> None:
    workload = await get_workload_by_id_in_cluster(session, message.workload_id, cluster.id)

    if workload is None:
        logger.error(f"Workload {message.workload_id} not found in cluster {cluster.id}")
        return

    components = await get_workload_components_by_workload_id(session, message.workload_id)

    if not components:
        logger.error(f"No components found for workload {message.workload_id}")
        return

    component = get_workload_component_for_status_update(components, message)

    if not component:
        logger.warning(
            f"Workload component {message.id} not found in workload {workload.id}. Maybe a child created from a component."
        )
        return

    if component.updated_at >= message.updated_at:
        logger.debug(f"Received outdated status for workload component {message.id}, ignoring.")
        return

    await update_workload_component_status_in_db(
        session, component, message.status, message.status_reason, message.updated_at, "system"
    )

    new_workload_status = resolve_workload_status(workload.status, components)

    if workload.status != new_workload_status.value:
        await increment_workload_time_summary(
            session, workload.id, workload.status, message.updated_at - workload.last_status_transition_at
        )
        await update_workload_status_in_db(session, workload, new_workload_status, message.updated_at, "system")


async def register_auto_discovered_workload_component(
    session: AsyncSession, cluster: Cluster, message: AutoDiscoveredWorkloadComponentMessage
) -> None:
    workload = await get_workload_by_id_in_cluster(session, message.workload_id, cluster.id)
    submitter = message.submitter or "system"
    if not workload:
        logger.info("Workload has been auto discovered, creating entry in database")

        workload = await create_workload_in_db(
            session=session,
            cluster_id=cluster.id,
            project_id=message.project_id,
            status=WorkloadStatus.PENDING.value,
            creator=submitter,
            workload_type=WorkloadType.CUSTOM,
            display_name=message.name,
            workload_id=message.workload_id,
        )

    component = await get_workload_component_by_id(session, message.component_id, workload.id)
    if not component:
        logger.info("Workload component has been auto discovered, creating entry in database")
        component = WorkloadComponentIn(
            name=message.name,
            kind=message.kind,
            api_version=message.api_version,
            workload_id=workload.id,
            id=message.component_id,
        )
        await create_workload_component_in_db(session=session, component=component, creator=submitter)


async def increment_workload_time_summary(
    session: AsyncSession, workload_id: UUID, status: str, duration_in_status: timedelta
) -> None:
    duration_in_status_seconds = duration_in_status.total_seconds()
    workload_time_summary = await get_workload_time_summary_by_workload_id_and_status(session, workload_id, status)
    if workload_time_summary:
        await increment_total_elapsed_seconds(
            session, workload_time_summary=workload_time_summary, increment_seconds=duration_in_status_seconds
        )
    else:
        await insert_workload_time_summary(
            session, workload_id=workload_id, status=status, total_elapsed_seconds=duration_in_status_seconds
        )


async def get_stats_for_workloads_in_project(session: AsyncSession, project: Project) -> ProjectWorkloadsStats:
    workloads_counts = await get_workloads_with_status_in_project_count(
        session,
        project.id,
        [
            WorkloadStatus.COMPLETE,
            WorkloadStatus.DOWNLOADING,
            WorkloadStatus.FAILED,
            WorkloadStatus.DELETING,
            WorkloadStatus.DELETE_FAILED,
            WorkloadStatus.RUNNING,
            WorkloadStatus.PENDING,
            WorkloadStatus.TERMINATED,
        ],
    )

    status_counts = [WorkloadStatusCount(status=status, count=count) for status, count in workloads_counts.items()]

    return ProjectWorkloadsStats(
        name=project.name, total_workloads=sum(workloads_counts.values()), statusCounts=status_counts
    )
