# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workloads service tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    AutoDiscoveredWorkloadComponentMessage,
    DeleteWorkloadMessage,
    JobStatus,
    WorkloadComponentKind,
    WorkloadComponentStatusMessage,
    WorkloadStatus,
    WorkloadStatusMessage,
)
from app.workloads.enums import WorkloadType
from app.workloads.repository import (
    get_workload_by_id_in_cluster,
    get_workload_component_by_id,
    get_workload_time_summary_by_workload_id_and_status,
)
from app.workloads.service import (
    create_and_submit_workload,
    extract_components_and_submit_workload,
    get_stats_for_workloads_in_cluster,
    get_stats_for_workloads_in_organization,
    get_stats_for_workloads_in_project,
    get_workload_with_components,
    get_workloads_accessible_to_user,
    get_workloads_by_project,
    increment_workload_time_summary,
    register_auto_discovered_workload_component,
    submit_delete_workload,
    update_workload_component_status,
    update_workload_status,
)
from tests import factory

# Mock YAML content for testing
MOCK_YAML_CONTENT = """
apiVersion: v1
kind: Deployment
metadata:
    name: test-pod
    namespace: some-namespace
spec:
    containers:
    - name: test-container
      image: test-image
"""


@pytest.mark.asyncio
async def test_create_and_submit_workload_success(db_session: AsyncSession):
    """Test successful workload creation and submission."""
    env = await factory.create_basic_test_environment(db_session)

    project, quota = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="test_project",
        quota_cpu=1000,
        quota_memory=1000000000,
        quota_storage=1000000000,
        quota_gpu=0,
    )

    creator = "test@example.com"
    workload_type = WorkloadType.INFERENCE

    manifest = [{"apiVersion": "v1", "kind": "Deployment", "metadata": {"name": "test-deployment"}}]
    token = "test-token"
    display_name = "Test Workload Display"

    with patch("app.workloads.service.extract_components_and_submit_workload") as mock_extract:
        result = await create_and_submit_workload(
            db_session,
            project,
            manifest,
            creator,
            token,
            workload_type,
            display_name,
        )
    mock_extract.assert_awaited_once()

    assert result is not None
    assert result.display_name == display_name
    assert result.type == workload_type
    assert result.project_id == project.id
    assert result.cluster_id == env.cluster.id

    assert await get_workload_by_id_in_cluster(db_session, result.id, result.cluster_id) is not None


@pytest.mark.asyncio
async def test_submit_delete_workload_success(db_session: AsyncSession):
    """Test successful workload deletion submission."""
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.RUNNING.value, display_name="Test Workload"
    )

    user = "test@example.com"

    with patch("app.workloads.service.submit_message_to_cluster_queue") as mock_submit:
        await submit_delete_workload(db_session, workload, user)

        mock_submit.assert_called_once()

        call_args = mock_submit.call_args
        cluster_id, message = call_args[0]
        assert cluster_id == env.cluster.id
        assert isinstance(message, DeleteWorkloadMessage)
        assert message.workload_id == workload.id

        await db_session.refresh(workload)
        assert workload.status == WorkloadStatus.DELETING.value


@pytest.mark.asyncio
async def test_submit_delete_workload_already_pending_deletion(db_session: AsyncSession):
    """Test deletion of workload already marked for deletion."""
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, status=WorkloadStatus.DELETING.value)

    user = "test@example.com"

    with patch("app.workloads.service.submit_message_to_cluster_queue") as mock_submit:
        with pytest.raises(Exception, match="Workload is already marked for deletion"):
            await submit_delete_workload(db_session, workload, user)

        mock_submit.assert_not_called()


@pytest.mark.asyncio
async def test_submit_delete_workload_already_deleted(db_session: AsyncSession):
    """Test deletion of workload already deleted."""
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, status=WorkloadStatus.DELETED.value)

    user = "test@example.com"

    with patch("app.workloads.service.submit_message_to_cluster_queue") as mock_submit:
        with pytest.raises(Exception, match="Workload has already been deleted"):
            await submit_delete_workload(db_session, workload, user)

        mock_submit.assert_not_called()


@pytest.mark.asyncio
async def test_update_workload_status_success(db_session: AsyncSession):
    """Test successful workload status update."""
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, status=WorkloadStatus.PENDING.value)

    message = WorkloadStatusMessage(
        message_type="workload_status_update",
        workload_id=workload.id,
        status=JobStatus.RUNNING,
        updated_at=datetime.now(UTC),
        status_reason="Test update",
    )

    await update_workload_status(db_session, env.cluster, message)

    # Verify the workload status was updated in the database
    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.RUNNING.value
    assert workload.updated_at == message.updated_at


@pytest.mark.asyncio
async def test_update_workload_status_no_workload(db_session: AsyncSession):
    """Test workload status update when workload doesn't exist."""
    # Create real test environment but don't create the workload
    env = await factory.create_basic_test_environment(db_session)

    # Create status message for non-existent workload
    non_existent_workload_id = uuid4()
    message = WorkloadStatusMessage(
        message_type="workload_status_update",
        workload_id=non_existent_workload_id,
        status=JobStatus.RUNNING,
        updated_at=datetime.now(UTC),
        status_reason="Test update for non-existent workload",
    )

    # Update workload status should handle gracefully when workload not found
    # This should not raise an exception, just log a warning
    await update_workload_status(db_session, env.cluster, message)


@pytest.mark.asyncio
async def test_update_workload_status_no_updates(db_session: AsyncSession):
    """Test workload status update when workload timestamp is newer than message."""
    env = await factory.create_basic_test_environment(db_session)

    # Create workload with a recent timestamp
    future_time = datetime.now(UTC) + timedelta(hours=1)
    workload = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.PENDING.value, last_status_transition_at=future_time
    )

    # Set workload updated_at to future time manually
    workload.updated_at = future_time
    await db_session.flush()

    # Create status message with older timestamp
    past_time = datetime.now(UTC) - timedelta(hours=1)
    message = WorkloadStatusMessage(
        message_type="workload_status_update",
        workload_id=workload.id,
        status=JobStatus.RUNNING,
        updated_at=past_time,
        status_reason="Outdated status update",
    )

    # Update workload status with older timestamp
    await update_workload_status(db_session, env.cluster, message)

    # Verify the workload status was NOT updated (timestamp was older)
    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.PENDING.value  # Should remain unchanged
    assert workload.updated_at == future_time  # Should remain unchanged


@pytest.mark.asyncio
async def test_get_workloads_by_project_success(db_session: AsyncSession):
    """Test retrieving workloads by project with real database operations."""
    # Create real test environment with multiple workloads
    env = await factory.create_basic_test_environment(db_session)

    # Create workloads in the project
    workload1 = await factory.create_workload(db_session, env.cluster, env.project, display_name="Workload 1")
    workload2 = await factory.create_workload(db_session, env.cluster, env.project, display_name="Workload 2")

    # Create workload in different project to verify isolation
    other_project = await factory.create_project(db_session, env.organization, env.cluster, name="Other Project")
    other_workload = await factory.create_workload(
        db_session, env.cluster, other_project, display_name="Other Workload"
    )

    # Test getting workloads by project
    result = await get_workloads_by_project(db_session, env.project.id)

    # Verify only project workloads are returned
    assert len(result.workloads) == 2
    workload_names = {w.display_name for w in result.workloads}
    assert "Workload 1" in workload_names
    assert "Workload 2" in workload_names
    assert "Other Workload" not in workload_names


@pytest.mark.asyncio
async def test_get_workloads_accessible_to_user_success(db_session: AsyncSession):
    """Test retrieving workloads accessible to user with real database operations."""
    # Create multi-organization environment for access control testing
    environments = await factory.create_multi_organization_environment(db_session)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create user and projects
    user = await factory.create_user(db_session, org1, email="test@example.com")
    accessible_project = await factory.create_project(db_session, org1, cluster1, name="Accessible Project")

    # Create accessible workload
    accessible_workload = await factory.create_workload(
        db_session, cluster1, accessible_project, display_name="Accessible Workload"
    )

    # Create inaccessible workload in different organization
    inaccessible_workload = await factory.create_workload(
        db_session, cluster2, project2, display_name="Inaccessible Workload"
    )

    # Test getting workloads accessible to user
    result = await get_workloads_accessible_to_user(db_session, [accessible_project])

    # Verify only accessible workloads are returned
    assert len(result.workloads) == 1
    assert result.workloads[0].display_name == "Accessible Workload"
    assert result.workloads[0].id == accessible_workload.id


@pytest.mark.asyncio
async def test_update_workload_component_status_success(db_session: AsyncSession):
    """Test successful workload component status update with real database operations."""
    # Create real test environment with workload and components
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="Test Workload")

    workload.last_status_transition_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.flush()

    # Create workload component
    component = await factory.create_workload_component(
        db_session,
        workload,
        name="test-component",
        kind=WorkloadComponentKind.DEPLOYMENT,
        api_version="apps/v1",
        status="Pending",
    )

    # Create component status message
    message = WorkloadComponentStatusMessage(
        message_type="workload_component_status_update",
        id=component.id,
        name="test-component",
        kind=WorkloadComponentKind.DEPLOYMENT,
        api_version="apps/v1",
        workload_id=workload.id,
        status=JobStatus.RUNNING,
        status_reason="Running successfully",
        updated_at=datetime.now(UTC),
    )

    await update_workload_component_status(db_session, env.cluster, message)

    # Verify the workload component status was updated in the database
    await db_session.refresh(component)
    assert component.status == JobStatus.RUNNING.value

    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.RUNNING.value

    pending_summary = await get_workload_time_summary_by_workload_id_and_status(
        db_session, workload.id, WorkloadStatus.PENDING
    )
    assert pending_summary.total_elapsed_seconds == 3600


@pytest.mark.asyncio
async def test_get_stats_for_workloads_in_project_success(db_session: AsyncSession):
    """Test getting workload statistics for project with real database operations."""
    # Create real test environment with workloads in different states
    env = await factory.create_basic_test_environment(db_session)

    # Create workloads with different statuses
    running_workload = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.RUNNING.value, display_name="Running Workload"
    )
    pending_workload = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.PENDING.value, display_name="Pending Workload"
    )
    failed_workload = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.FAILED.value, display_name="Failed Workload"
    )

    # Test getting workload stats using real database operations
    result = await get_stats_for_workloads_in_project(db_session, env.project)

    # Verify returned stats match the created workloads
    status_counts = {sc.status: sc.count for sc in result.statusCounts}
    assert status_counts.get(WorkloadStatus.RUNNING, 0) == 1
    assert status_counts.get(WorkloadStatus.PENDING, 0) == 1
    assert status_counts.get(WorkloadStatus.FAILED, 0) == 1
    assert status_counts.get(WorkloadStatus.COMPLETE, 0) == 0
    assert status_counts.get(WorkloadStatus.DELETED, 0) == 0
    assert status_counts.get(WorkloadStatus.DELETING, 0) == 0


@pytest.mark.asyncio
async def test_get_workload_with_components_success(db_session: AsyncSession):
    """Test retrieving workload with components with real database operations."""
    # Create real test environment with workload and components
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="Test Workload")

    # Create multiple components
    component1 = await factory.create_workload_component(
        db_session, workload, name="deployment", kind=WorkloadComponentKind.DEPLOYMENT
    )
    component2 = await factory.create_workload_component(
        db_session, workload, name="service", kind=WorkloadComponentKind.SERVICE
    )

    # Test retrieving workload with components using real database operations
    result = await get_workload_with_components(db_session, workload)

    # Verify workload and components are returned
    assert result.id == workload.id
    assert result.display_name == "Test Workload"
    assert len(result.components) == 2

    # Verify component details
    component_names = {comp.name for comp in result.components}
    assert "deployment" in component_names
    assert "service" in component_names


@pytest.mark.asyncio
async def test_get_stats_for_workloads_in_cluster(db_session: AsyncSession):
    """Test getting workload statistics for cluster."""
    # Create real test environment with multiple workloads
    env = await factory.create_basic_test_environment(db_session)

    # Create additional projects in the same cluster
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="Project 2")

    # Create workloads with different statuses across projects in the cluster
    running_workload1 = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.RUNNING.value
    )
    running_workload2 = await factory.create_workload(
        db_session, env.cluster, project2, status=WorkloadStatus.RUNNING.value
    )
    pending_workload = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.PENDING.value
    )
    completed_workload = await factory.create_workload(
        db_session, env.cluster, project2, status=WorkloadStatus.COMPLETE.value
    )

    # Create workload in different cluster to verify isolation
    other_environments = await factory.create_multi_organization_environment(db_session, org_count=1)
    other_org, other_cluster, other_project = other_environments[0]
    other_workload = await factory.create_workload(
        db_session, other_cluster, other_project, status=WorkloadStatus.RUNNING.value
    )

    # Test getting workload stats for the cluster
    result = await get_stats_for_workloads_in_cluster(db_session, env.cluster)

    # Verify stats only include workloads from the target cluster
    # Only RUNNING and PENDING are included in cluster stats
    assert result.running_workloads_count == 2  # Two running workloads in cluster
    assert result.pending_workloads_count == 1  # One pending workload in cluster


@pytest.mark.asyncio
async def test_get_stats_for_workloads_in_organization(db_session: AsyncSession):
    """Test getting workload statistics for organization."""
    # Create real test environment with multiple clusters
    env = await factory.create_basic_test_environment(db_session)

    # Create additional cluster in same organization
    cluster2 = await factory.create_cluster(db_session, env.organization, name="Cluster 2")
    project2 = await factory.create_project(db_session, env.organization, cluster2, name="Project 2")

    # Create workloads with different statuses across clusters in the organization
    running_workload1 = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.RUNNING.value
    )
    running_workload2 = await factory.create_workload(
        db_session, cluster2, project2, status=WorkloadStatus.RUNNING.value
    )
    pending_workload = await factory.create_workload(
        db_session, env.cluster, env.project, status=WorkloadStatus.PENDING.value
    )
    completed_workload = await factory.create_workload(
        db_session, cluster2, project2, status=WorkloadStatus.COMPLETE.value
    )

    # Create workload in different organization to verify isolation
    other_environments = await factory.create_multi_organization_environment(db_session, org_count=1)
    other_org, other_cluster, other_project = other_environments[0]
    other_workload = await factory.create_workload(
        db_session, other_cluster, other_project, status=WorkloadStatus.RUNNING.value
    )

    # Test getting workload stats for the organization
    result = await get_stats_for_workloads_in_organization(db_session, env.organization.id)

    # Verify stats only include workloads from the target organization
    # Only RUNNING and PENDING are included in organization stats
    assert result.running_workloads_count == 2  # Two running workloads across clusters
    assert result.pending_workloads_count == 1  # One pending workload across clusters


@pytest.mark.asyncio
async def test_increment_workload_time_summary_new(db_session: AsyncSession):
    """Test incrementing workload time summary for new entry with real database operations."""
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="Test Workload")

    status = WorkloadStatus.RUNNING
    increment_duration = timedelta(seconds=60)

    # Test incrementing workload time summary using real database operations
    await increment_workload_time_summary(db_session, workload.id, status, increment_duration)

    # Verify the time summary was created in the database
    time_summary = await get_workload_time_summary_by_workload_id_and_status(db_session, workload.id, status)
    assert time_summary is not None
    assert time_summary.workload_id == workload.id
    assert time_summary.status == status.value
    assert time_summary.total_elapsed_seconds == int(increment_duration.total_seconds())


@pytest.mark.asyncio
async def test_increment_workload_time_summary_existing(db_session: AsyncSession):
    """Test incrementing workload time summary for existing entry."""
    # Create real test environment with workload and existing time summary
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="Test Workload")

    # Create existing time summary
    status = WorkloadStatus.RUNNING.value
    initial_seconds = 3600  # 1 hour
    time_summary = await factory.create_workload_time_summary(
        db_session, workload, status=status, total_elapsed_seconds=initial_seconds
    )

    # Test incrementing existing workload time summary
    increment_duration = timedelta(seconds=1800)  # 30 minutes
    await increment_workload_time_summary(db_session, workload.id, status, increment_duration)

    # Verify the time summary was updated in the database
    updated_summary = await get_workload_time_summary_by_workload_id_and_status(db_session, workload.id, status)

    assert updated_summary is not None
    assert updated_summary.id == time_summary.id  # Same record
    assert updated_summary.total_elapsed_seconds == initial_seconds + 1800  # Original + increment
    assert updated_summary.workload_id == workload.id
    assert updated_summary.status == status


@pytest.mark.asyncio
async def test_extract_components_and_submit_workload(db_session: AsyncSession):
    """Test detailed component extraction and submission flow."""
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="Test Workload")

    # Create manifest with multiple components
    manifest = [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-deployment", "namespace": "default"},
            "spec": {"replicas": 1},
        },
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "test-service", "namespace": "default"},
            "spec": {"ports": [{"port": 80}]},
        },
    ]

    creator = "test@example.com"
    token = "test-token"

    with (
        patch("app.workloads.service.submit_message_to_cluster_queue") as mock_submit,
    ):
        await extract_components_and_submit_workload(db_session, workload, env.project, manifest, creator, token)

        # Verify message submission
        mock_submit.assert_called_once()
        call_args = mock_submit.call_args[0]
        cluster_id, message = call_args
        assert cluster_id == env.project.cluster_id
        assert message.message_type == "workload"
        assert message.workload_id == workload.id
        assert message.user_token == token

        workload_with_components = await get_workload_with_components(db_session, workload)
        components = workload_with_components.components
        service = next((c for c in components if c.kind == WorkloadComponentKind.SERVICE), None)
        deployment = next((c for c in components if c.kind == WorkloadComponentKind.DEPLOYMENT), None)

        assert service is not None
        assert deployment is not None

        assert (
            message.manifest
            == f"""apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    airm.silogen.ai/component-id: {deployment.id}
    airm.silogen.ai/project-id: {workload.project_id}
    airm.silogen.ai/workload-id: {workload.id}
    kueue.x-k8s.io/queue-name: test-project
  name: test-deployment
  namespace: test-project
spec:
  replicas: 1
  template:
    metadata:
      labels:
        airm.silogen.ai/component-id: {deployment.id}
        airm.silogen.ai/project-id: {workload.project_id}
        airm.silogen.ai/workload-id: {workload.id}
---
apiVersion: v1
kind: Service
metadata:
  labels:
    airm.silogen.ai/component-id: {service.id}
    airm.silogen.ai/project-id: {workload.project_id}
    airm.silogen.ai/workload-id: {workload.id}
  name: test-service
  namespace: test-project
spec:
  ports:
  - port: 80
"""
        )


@pytest.mark.asyncio
async def test_register_auto_discovered_workload_component_no_workload(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    workload_id = uuid4()
    component_id = uuid4()
    message = AutoDiscoveredWorkloadComponentMessage(
        message_type="auto_discovered_workload_component",
        workload_id=workload_id,
        component_id=component_id,
        project_id=env.project.id,
        name="test-component",
        submitter="test-submitter",
        kind=WorkloadComponentKind.DEPLOYMENT,
        api_version="apps/v1",
        updated_at=datetime.now(UTC),
    )

    await register_auto_discovered_workload_component(db_session, env.cluster, message)

    workload = await get_workload_by_id_in_cluster(db_session, workload_id, env.cluster.id)
    assert workload.id == workload_id
    assert workload.created_by == "test-submitter"

    component = await get_workload_component_by_id(db_session, component_id, workload.id)
    assert component.id == component_id
    assert component.created_by == "test-submitter"


@pytest.mark.asyncio
async def test_register_auto_discovered_workload_component_workload_exists(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    workload = await factory.create_workload(db_session, env.cluster, env.project, display_name="Test Workload")

    component_id = uuid4()
    message = AutoDiscoveredWorkloadComponentMessage(
        message_type="auto_discovered_workload_component",
        workload_id=workload.id,
        component_id=component_id,
        project_id=env.project.id,
        name="test-component",
        kind=WorkloadComponentKind.DEPLOYMENT,
        api_version="apps/v1",
        updated_at=datetime.now(UTC),
    )

    await register_auto_discovered_workload_component(db_session, env.cluster, message)

    workload = await get_workload_by_id_in_cluster(db_session, workload.id, env.cluster.id)
    assert workload.id == workload.id

    component = await get_workload_component_by_id(db_session, component_id, workload.id)
    assert component.id == component_id
