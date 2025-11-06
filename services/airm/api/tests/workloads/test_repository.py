# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import CommonComponentStatus, WorkloadComponentKind, WorkloadStatus
from app.utilities.collections.schemas import FilterCondition, PaginationConditions, SortCondition
from app.workloads.enums import WorkloadType
from app.workloads.repository import (
    create_workload,
    create_workload_component,
    create_workload_components,
    get_active_workload_count_by_project,
    get_average_pending_time_for_workloads_in_project_created_between,
    get_last_updated_workload_time_summary_by_workload_id,
    get_workload_by_id_and_user_membership,
    get_workload_by_id_in_cluster,
    get_workload_by_id_in_organization,
    get_workload_component_by_id,
    get_workload_components_by_workload_id,
    get_workload_counts_with_status_by_project_id,
    get_workload_time_summary_by_workload_id_and_status,
    get_workloads_accessible_to_user,
    get_workloads_by_project,
    get_workloads_with_running_time_in_project,
    get_workloads_with_status_in_cluster_count,
    get_workloads_with_status_in_organization_count,
    insert_workload_time_summary,
    update_workload_component_status,
    update_workload_status,
)
from app.workloads.schemas import WorkloadComponentIn
from tests import factory


@pytest.mark.asyncio
async def test_create_workload(db_session: AsyncSession):
    """Test creating a workload"""
    env = await factory.create_basic_test_environment(db_session)

    workload_name = "test-workload"
    workload_type = WorkloadType.INFERENCE
    creator = "test@example.com"

    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=creator,
        workload_type=workload_type,
        display_name=workload_name,
    )

    assert workload.display_name == workload_name
    assert workload.type == workload_type.value
    assert workload.project_id == env.project.id
    assert workload.cluster_id == env.cluster.id
    assert workload.created_by == creator
    assert workload.status == WorkloadStatus.PENDING.value


@pytest.mark.asyncio
async def test_get_workload_by_id_and_user_membership(db_session: AsyncSession):
    """Test getting workload with user membership validation."""
    env = await factory.create_full_test_environment(db_session)

    # Create workload using real database
    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Running",
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="test-workload",
    )

    # Test: User with membership should find workload
    found_workload = await get_workload_by_id_and_user_membership(db_session, workload.id, [env.project])
    assert found_workload is not None
    assert found_workload.id == workload.id

    # Test: User without membership should not find workload
    not_found_workload = await get_workload_by_id_and_user_membership(db_session, workload.id, [])
    assert not_found_workload is None


@pytest.mark.asyncio
async def test_get_workloads_by_project(db_session: AsyncSession):
    """Test getting workloads by project ID."""
    env = await factory.create_basic_test_environment(db_session)

    # Create multiple workloads in the project
    workload1 = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Running",
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="workload-1",
    )

    workload2 = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Running",
        creator=env.creator,
        workload_type=WorkloadType.FINE_TUNING,
        display_name="workload-2",
    )

    # Get workloads by project
    project_workloads = await get_workloads_by_project(db_session, env.project.id)

    assert len(project_workloads) == 2
    workload_names = {w.display_name for w in project_workloads}
    assert "workload-1" in workload_names
    assert "workload-2" in workload_names


@pytest.mark.asyncio
async def test_get_workloads_in_organization(db_session: AsyncSession):
    """Test getting workloads in organization with proper isolation."""
    # Create multiple organizations
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create workloads in both organizations
    workload1 = await create_workload(
        db_session,
        cluster_id=cluster1.id,
        project_id=project1.id,
        status="Running",
        creator="test@example.com",
        workload_type=WorkloadType.INFERENCE,
        display_name="org1-workload",
    )

    workload2 = await create_workload(
        db_session,
        cluster_id=cluster2.id,
        project_id=project2.id,
        status="Running",
        creator="test@example.com",
        workload_type=WorkloadType.FINE_TUNING,
        display_name="org2-workload",
    )

    workload1_retrieved = await get_workload_by_id_in_cluster(db_session, workload1.id, cluster1.id)
    workload2_retrieved = await get_workload_by_id_in_cluster(db_session, workload2.id, cluster2.id)

    assert workload1_retrieved is not None
    assert workload1_retrieved.display_name == "org1-workload"
    assert workload2_retrieved is not None
    assert workload2_retrieved.display_name == "org2-workload"


@pytest.mark.asyncio
async def test_update_workload_status(db_session: AsyncSession):
    """Test updating workload status."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload
    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="test-workload",
    )

    assert workload.status == WorkloadStatus.PENDING

    updated_at = datetime.now(UTC)
    await update_workload_status(
        db_session,
        workload,
        WorkloadStatus.RUNNING,
        updated_at,
        "test@example.com",
    )

    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.RUNNING


@pytest.mark.asyncio
async def test_get_active_workload_count_by_project(db_session: AsyncSession):
    """Test counting active workloads by project."""
    env = await factory.create_basic_test_environment(db_session)

    running_workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="running-workload",
    )

    pending_workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.FINE_TUNING,
        display_name="pending-workload",
    )

    await update_workload_status(
        db_session,
        running_workload,
        WorkloadStatus.RUNNING,
        datetime.now(UTC),
        "test@example.com",
    )

    count = await get_active_workload_count_by_project(db_session, env.project.id)
    assert count == 2


@pytest.mark.asyncio
async def test_get_workload_by_id_in_cluster_wrong_cluster(db_session: AsyncSession):
    """Test retrieving workload by ID in wrong cluster returns None."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create workload in cluster1
    workload = await create_workload(
        db_session,
        cluster_id=cluster1.id,
        project_id=project1.id,
        status=WorkloadStatus.RUNNING.value,
        creator="test@example.com",
        workload_type=WorkloadType.INFERENCE,
        display_name="test-workload",
    )

    result = await get_workload_by_id_in_cluster(db_session, workload.id, cluster2.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_workloads_by_project_wrong_project(db_session: AsyncSession):
    """Test retrieving workloads for wrong project returns empty list."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create workload in project1
    await create_workload(
        db_session,
        cluster_id=cluster1.id,
        project_id=project1.id,
        status=WorkloadStatus.RUNNING.value,
        creator="test@example.com",
        workload_type=WorkloadType.INFERENCE,
        display_name="project1-workload",
    )

    workloads = await get_workloads_by_project(db_session, project2.id)
    assert len(workloads) == 0


@pytest.mark.asyncio
async def test_get_workloads_accessible_to_user(db_session: AsyncSession):
    """Test retrieving workloads accessible to specific user."""
    # Create extended environment with user
    env = await factory.create_full_test_environment(db_session)

    user_with_access = env.user  # Use the user created by the environment
    user_without_access = await factory.create_user(db_session, env.organization, email="user2@example.com")

    # Create workloads
    workload1 = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.RUNNING.value,
        creator=user_with_access.email,
        workload_type=WorkloadType.INFERENCE,
        display_name="user1-workload",
    )

    # User with membership should access workload
    accessible_workloads = await get_workloads_accessible_to_user(db_session, [env.project])
    assert len(accessible_workloads) == 1
    assert accessible_workloads[0].id == workload1.id

    # User without membership should not access workload
    inaccessible_workloads = await get_workloads_accessible_to_user(db_session, [])
    assert len(inaccessible_workloads) == 0


@pytest.mark.asyncio
async def test_get_workload_by_id_in_organization(db_session: AsyncSession):
    """Test retrieving workload by ID within organization scope."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create workload in org1
    workload = await create_workload(
        db_session,
        cluster_id=cluster1.id,
        project_id=project1.id,
        status=WorkloadStatus.RUNNING.value,
        creator="test@example.com",
        workload_type=WorkloadType.INFERENCE,
        display_name="org1-workload",
    )

    # Should find workload in correct organization
    found_workload = await get_workload_by_id_in_organization(db_session, workload.id, org1.id)
    assert found_workload is not None
    assert found_workload.id == workload.id

    # Should not find workload in different organization
    not_found = await get_workload_by_id_in_organization(db_session, workload.id, org2.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_create_workload_component(db_session: AsyncSession):
    """Test creating workload components."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload
    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="test-workload",
    )

    workload_component_in = WorkloadComponentIn(
        name="inference-job", kind=WorkloadComponentKind.JOB, api_version="batch/v1", workload_id=workload.id
    )

    component = await create_workload_component(db_session, workload_component_in, env.creator)
    assert component.name == "inference-job"
    assert component.id is not None
    assert component.workload_id == workload.id

    new_component_id = uuid4()
    workload_component_in.id = new_component_id

    component = await create_workload_component(db_session, workload_component_in, env.creator)
    assert component.name == "inference-job"
    assert component.id == new_component_id


@pytest.mark.asyncio
async def test_create_workload_components(db_session: AsyncSession):
    """Test creating workload components."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload
    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="test-workload",
    )

    components = [
        WorkloadComponentIn(
            name="inference-job", kind=WorkloadComponentKind.JOB, api_version="batch/v1", workload_id=workload.id
        ),
        WorkloadComponentIn(
            name="inference-service", kind=WorkloadComponentKind.SERVICE, api_version="v1", workload_id=workload.id
        ),
    ]

    components_result = await create_workload_components(db_session, components, env.creator)

    assert len(components_result) == 2

    assert components_result[0].name == "inference-job"
    assert components_result[0].workload_id == workload.id
    assert components_result[1].name == "inference-service"
    assert components_result[1].workload_id == workload.id


@pytest.mark.asyncio
async def test_get_workload_components_by_workload_id(db_session: AsyncSession):
    """Test retrieving workload components by workload ID."""
    env = await factory.create_basic_test_environment(db_session)

    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="test-workload")
    component1 = await factory.create_workload_component(db_session, workload, name="pod-1")
    component2 = await factory.create_workload_component(db_session, workload, name="service-1")

    components = await get_workload_components_by_workload_id(db_session, workload.id)

    assert len(components) == 2
    component_names = {c.name for c in components}
    assert "pod-1" in component_names
    assert "service-1" in component_names


@pytest.mark.asyncio
async def test_get_workload_component_by_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="test-workload")
    component = await factory.create_workload_component(db_session, workload, name="test-pod", status="Registered")

    assert await get_workload_component_by_id(db_session, component.id, workload.id) is not None
    assert await get_workload_component_by_id(db_session, uuid4(), workload.id) is None


@pytest.mark.asyncio
async def test_update_workload_component_status(db_session: AsyncSession):
    """Test updating workload component status."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload with component
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="test-workload")
    component = await factory.create_workload_component(db_session, workload, name="test-pod", status="Registered")

    updated_at = datetime.now(UTC)
    await update_workload_component_status(
        db_session, component, CommonComponentStatus.DELETED.value, None, updated_at, "updater@example.com"
    )

    await db_session.refresh(component)
    assert component.status == CommonComponentStatus.DELETED.value
    assert component.updated_by == "updater@example.com"


@pytest.mark.asyncio
async def test_get_workloads_with_status_in_cluster_count(db_session: AsyncSession):
    """Test counting workloads with specific status in cluster."""
    env = await factory.create_basic_test_environment(db_session)

    await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.RUNNING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="running-1",
    )

    await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.RUNNING.value,
        creator=env.creator,
        workload_type=WorkloadType.FINE_TUNING,
        display_name="running-2",
    )

    await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="pending-1",
    )

    running_counts = await get_workloads_with_status_in_cluster_count(
        db_session, env.cluster.id, [WorkloadStatus.RUNNING]
    )
    assert running_counts[WorkloadStatus.RUNNING] == 2

    pending_counts = await get_workloads_with_status_in_cluster_count(
        db_session, env.cluster.id, [WorkloadStatus.PENDING]
    )
    assert pending_counts[WorkloadStatus.PENDING] == 1


@pytest.mark.asyncio
async def test_get_workloads_with_status_in_organization_count(db_session: AsyncSession):
    """Test counting workloads with specific status in organization."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create workloads in org1
    await create_workload(
        db_session,
        cluster_id=cluster1.id,
        project_id=project1.id,
        status=WorkloadStatus.RUNNING.value,
        creator="test@example.com",
        workload_type=WorkloadType.INFERENCE,
        display_name="org1-running-1",
    )

    await create_workload(
        db_session,
        cluster_id=cluster1.id,
        project_id=project1.id,
        status=WorkloadStatus.RUNNING.value,
        creator="test@example.com",
        workload_type=WorkloadType.FINE_TUNING,
        display_name="org1-running-2",
    )

    # Create workload in org2
    await create_workload(
        db_session,
        cluster_id=cluster2.id,
        project_id=project2.id,
        status=WorkloadStatus.RUNNING.value,
        creator="test@example.com",
        workload_type=WorkloadType.INFERENCE,
        display_name="org2-running-1",
    )

    org1_counts = await get_workloads_with_status_in_organization_count(db_session, org1.id, [WorkloadStatus.RUNNING])
    assert org1_counts[WorkloadStatus.RUNNING] == 2

    org2_counts = await get_workloads_with_status_in_organization_count(db_session, org2.id, [WorkloadStatus.RUNNING])
    assert org2_counts[WorkloadStatus.RUNNING] == 1


@pytest.mark.asyncio
async def test_get_workload_counts_with_status_by_project_id(db_session: AsyncSession):
    """Test getting workload counts by status for a project."""
    env = await factory.create_basic_test_environment(db_session)

    await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.RUNNING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="running-1",
    )

    await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.RUNNING.value,
        creator=env.creator,
        workload_type=WorkloadType.FINE_TUNING,
        display_name="running-2",
    )

    await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="pending-1",
    )

    counts = await get_workload_counts_with_status_by_project_id(
        db_session, env.organization.id, [WorkloadStatus.RUNNING, WorkloadStatus.PENDING]
    )

    # Should return counts grouped by project and status
    # Find counts for our specific project
    project_running_count = counts.get((env.project.id, WorkloadStatus.RUNNING), 0)
    project_pending_count = counts.get((env.project.id, WorkloadStatus.PENDING), 0)
    assert project_running_count == 2
    assert project_pending_count == 1


@pytest.mark.asyncio
async def test_get_active_workload_count_by_project_no_workloads(db_session: AsyncSession):
    """Test counting active workloads when project has no workloads."""
    env = await factory.create_basic_test_environment(db_session)

    count = await get_active_workload_count_by_project(db_session, env.project.id)
    assert count == 0


@pytest.mark.asyncio
async def test_get_workload_time_summary_by_workload_id_and_status(db_session: AsyncSession):
    """Test retrieving workload time summary by workload ID and status."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="test-workload")

    await insert_workload_time_summary(
        db_session,
        workload.id,
        WorkloadStatus.RUNNING.value,
        total_elapsed_seconds=3600,
    )

    summary = await get_workload_time_summary_by_workload_id_and_status(db_session, workload.id, WorkloadStatus.RUNNING)

    assert summary is not None
    assert summary.workload_id == workload.id
    assert summary.status == WorkloadStatus.RUNNING
    assert summary.total_elapsed_seconds == 3600


@pytest.mark.asyncio
async def test_get_workloads_with_running_time_in_project(db_session: AsyncSession):
    """Test retrieving workloads with running time in project."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workloads
    workload1 = await factory.create_workload(db_session, env.cluster, env.project, display_name="workload-1")
    workload2 = await factory.create_workload(db_session, env.cluster, env.project, display_name="workload-2")

    await insert_workload_time_summary(
        db_session,
        workload1.id,
        WorkloadStatus.RUNNING.value,
        total_elapsed_seconds=1800,
    )

    await insert_workload_time_summary(
        db_session,
        workload2.id,
        WorkloadStatus.RUNNING.value,
        total_elapsed_seconds=3600,
    )

    # Retrieve workloads with running time

    pagination_params = PaginationConditions(page=1, page_size=10)
    sort_params: list[SortCondition] = []
    filter_conditions: list[FilterCondition] = []

    workloads_with_time, count = await get_workloads_with_running_time_in_project(
        db_session, env.project.id, pagination_params, sort_params, filter_conditions
    )

    assert len(workloads_with_time) == 2
    assert count == 2
    # Function returns list of tuples (Workload, int)
    workload_ids = {workload.id for workload, _ in workloads_with_time}
    assert workload1.id in workload_ids
    assert workload2.id in workload_ids


@pytest.mark.asyncio
async def test_get_last_updated_workload_time_summary_by_workload_id(db_session: AsyncSession):
    """Test retrieving latest workload time summary."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="test-workload")

    older_time = datetime.now(UTC) - timedelta(hours=2)
    newer_time = datetime.now(UTC) - timedelta(hours=1)

    await insert_workload_time_summary(
        db_session,
        workload.id,
        WorkloadStatus.PENDING.value,
        total_elapsed_seconds=1800,
    )

    older_summary = await get_workload_time_summary_by_workload_id_and_status(
        db_session, workload.id, WorkloadStatus.PENDING
    )
    older_summary.updated_at = older_time
    await db_session.flush()

    await insert_workload_time_summary(
        db_session,
        workload.id,
        WorkloadStatus.RUNNING.value,
        total_elapsed_seconds=3600,
    )

    newer_summary = await get_workload_time_summary_by_workload_id_and_status(
        db_session, workload.id, WorkloadStatus.RUNNING
    )
    newer_summary.updated_at = newer_time
    await db_session.flush()

    latest_summary = await get_last_updated_workload_time_summary_by_workload_id(db_session, workload.id)

    # Should return the newer summary
    assert latest_summary is not None
    assert latest_summary.status == WorkloadStatus.RUNNING
    assert latest_summary.total_elapsed_seconds == 3600


@pytest.mark.asyncio
async def test_get_last_updated_workload_time_summary_by_workload_id_no_summaries(db_session: AsyncSession):
    """Test retrieving latest workload time summary when none exist."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload without any time summaries
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="test-workload")

    latest_summary = await get_last_updated_workload_time_summary_by_workload_id(db_session, workload.id)

    # Should return None when no summaries exist
    assert latest_summary is None


@pytest.mark.asyncio
async def test_get_average_pending_time_for_workloads_in_project_created_between(db_session: AsyncSession):
    """Test getting average pending time for workloads in project."""
    env = await factory.create_basic_test_environment(db_session)

    # Define time range
    start_date = datetime.now(UTC) - timedelta(days=7)
    end_date = datetime.now(UTC)

    # Create workloads within the date range
    workload1 = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="pending-workload-1",
    )

    workload2 = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.COMPLETE.value,
        creator=env.creator,
        workload_type=WorkloadType.FINE_TUNING,
        display_name="completed-workload-1",
    )

    # Set creation times to be within the range
    workload1.created_at = start_date + timedelta(days=1)
    workload2.created_at = start_date + timedelta(days=2)
    await db_session.flush()

    # Insert time summaries for pending status
    await insert_workload_time_summary(
        db_session,
        workload1.id,
        WorkloadStatus.PENDING.value,
        total_elapsed_seconds=1800,  # 30 minutes
    )

    await insert_workload_time_summary(
        db_session,
        workload2.id,
        WorkloadStatus.PENDING.value,
        total_elapsed_seconds=3600,  # 60 minutes
    )

    # Get average pending time
    avg_time = await get_average_pending_time_for_workloads_in_project_created_between(
        db_session, env.project.id, start_date, end_date
    )

    # Should return average of 1800 and 3600 = 2700 seconds (approximately)
    assert avg_time is not None
    assert abs(float(avg_time) - 2700.0) < 1.0  # Allow small floating point variance


@pytest.mark.asyncio
async def test_get_average_pending_time_for_workloads_no_workloads(db_session: AsyncSession):
    """Test getting average pending time when no workloads exist in date range."""
    env = await factory.create_basic_test_environment(db_session)

    # Define time range with no workloads
    start_date = datetime.now(UTC) + timedelta(days=10)
    end_date = datetime.now(UTC) + timedelta(days=20)

    # Get average pending time (should be None/empty)
    avg_time = await get_average_pending_time_for_workloads_in_project_created_between(
        db_session, env.project.id, start_date, end_date
    )

    # Should return None when no workloads exist in the date range
    assert avg_time is None


@pytest.mark.asyncio
async def test_get_total_elapsed_seconds_for_deleted_workload_that_was_running(db_session: AsyncSession):
    """Test retrieving total elapsed seconds for a deleted workload that was previously running."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload
    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="test-workload",
    )

    # Simulate workload lifecycle: PENDING -> RUNNING -> DELETED
    start_time = datetime.now(UTC) - timedelta(hours=2)

    # Transition to RUNNING
    await update_workload_status(db_session, workload, WorkloadStatus.RUNNING.value, start_time, "system")

    # Add running time summary (simulate 1 hour of running)
    running_seconds = 3600  # 1 hour
    await insert_workload_time_summary(
        db_session,
        workload.id,
        WorkloadStatus.RUNNING.value,
        total_elapsed_seconds=running_seconds,
    )

    # Transition to DELETED
    deletion_time = start_time + timedelta(hours=1)
    await update_workload_status(db_session, workload, WorkloadStatus.DELETED.value, deletion_time, "user@example.com")

    # Retrieve the running time summary for the deleted workload
    running_summary = await get_workload_time_summary_by_workload_id_and_status(
        db_session, workload.id, WorkloadStatus.RUNNING
    )

    assert running_summary is not None
    assert running_summary.workload_id == workload.id
    assert running_summary.status == WorkloadStatus.RUNNING.value
    assert running_summary.total_elapsed_seconds == running_seconds

    # Verify workload is now deleted
    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.DELETED.value


@pytest.mark.asyncio
async def test_get_total_elapsed_seconds_for_deleted_workload_never_ran(db_session: AsyncSession):
    """Test retrieving total elapsed seconds for a deleted workload that never entered running state."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload that goes directly from PENDING to DELETED
    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="never-ran-workload",
    )

    # Transition directly to DELETED without running
    deletion_time = datetime.now(UTC)
    await update_workload_status(db_session, workload, WorkloadStatus.DELETED.value, deletion_time, "user@example.com")

    # Try to retrieve running time summary (should not exist)
    running_summary = await get_workload_time_summary_by_workload_id_and_status(
        db_session, workload.id, WorkloadStatus.RUNNING
    )

    assert running_summary is None

    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.DELETED.value


@pytest.mark.asyncio
async def test_get_total_elapsed_seconds_for_failed_workload_that_was_running(db_session: AsyncSession):
    """Test retrieving total elapsed seconds for a failed workload that was previously running."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload
    workload = await create_workload(
        db_session,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status=WorkloadStatus.PENDING.value,
        creator=env.creator,
        workload_type=WorkloadType.INFERENCE,
        display_name="failed-workload",
    )

    # Simulate workload lifecycle: PENDING -> RUNNING -> FAILED
    start_time = datetime.now(UTC) - timedelta(minutes=45)

    # Transition to RUNNING
    await update_workload_status(db_session, workload, WorkloadStatus.RUNNING.value, start_time, "system")

    # Add running time summary (simulate 30 minutes of running before failure)
    running_seconds = 1800  # 30 minutes
    await insert_workload_time_summary(
        db_session,
        workload.id,
        WorkloadStatus.RUNNING.value,
        total_elapsed_seconds=running_seconds,
    )

    # Transition to FAILED
    failure_time = start_time + timedelta(minutes=30)
    await update_workload_status(db_session, workload, WorkloadStatus.FAILED.value, failure_time, "system")

    # Retrieve the running time summary for the failed workload
    running_summary = await get_workload_time_summary_by_workload_id_and_status(
        db_session, workload.id, WorkloadStatus.RUNNING
    )

    assert running_summary is not None
    assert running_summary.workload_id == workload.id
    assert running_summary.status == WorkloadStatus.RUNNING.value
    assert running_summary.total_elapsed_seconds == running_seconds

    # Verify workload is now failed
    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.FAILED.value
