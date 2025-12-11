# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Clusters service tests."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ClusterNode as ClusterNodeIn
from airm.messaging.schemas import ClusterNodesMessage, GPUInformation, GPUVendor, HeartbeatMessage
from app.clusters.repository import get_cluster_in_organization
from app.clusters.repository import get_cluster_nodes as get_cluster_nodes_from_db
from app.clusters.schemas import ClusterIn, ClusterKubeConfig, Clusters, ClustersStats
from app.clusters.service import (
    create_cluster,
    delete_cluster,
    get_cluster_kubeconfig_as_yaml,
    get_cluster_nodes,
    get_cluster_with_resources,
    get_clusters_stats,
    get_clusters_with_resources,
    update_cluster,
    update_cluster_nodes,
    update_last_heartbeat,
    validate_cluster_accessible_to_user,
)
from app.projects.models import Project
from app.quotas.models import QuotaStatus
from app.utilities.exceptions import DeletionConflictException, ForbiddenException, PreconditionNotMetException
from tests import factory


@pytest.mark.asyncio
async def test_create_cluster_success(db_session: AsyncSession):
    """Test successful cluster creation with real database operations."""
    env = await factory.create_basic_test_environment(db_session, creator="test_creator")
    organization = env.organization
    creator = env.creator

    with (
        patch("app.clusters.service.create_vhost_and_user", return_value="12345") as mock_create_vhost,
        patch("app.clusters.service.configure_queues_for_cluster") as mock_configure_queues,
    ):
        result = await create_cluster(
            db_session, organization.id, creator, cluster_create=ClusterIn(workloads_base_url="http://example.com")
        )

    mock_create_vhost.assert_called_once()
    mock_configure_queues.assert_called_once()

    assert result is not None
    assert result.created_by == creator
    assert result.user_secret == "12345"
    assert result.workloads_base_url == "http://example.com"


@pytest.mark.asyncio
async def test_create_cluster_success_no_base_url(db_session: AsyncSession):
    """Test successful cluster creation without a base URL with real database operations."""
    env = await factory.create_basic_test_environment(db_session, creator="test_creator")
    organization = env.organization
    creator = env.creator

    with (
        patch("app.clusters.service.create_vhost_and_user", return_value="12345") as mock_create_vhost,
        patch("app.clusters.service.configure_queues_for_cluster") as mock_configure_queues,
    ):
        result = await create_cluster(db_session, organization.id, creator, cluster_create=ClusterIn())

    mock_create_vhost.assert_called_once()
    mock_configure_queues.assert_called_once()

    assert result is not None
    assert result.created_by == creator
    assert result.user_secret == "12345"
    assert result.workloads_base_url is None


@pytest.mark.asyncio
async def test_create_cluster_vhost_failure(db_session: AsyncSession):
    """Test cluster creation failure when vhost creation fails."""
    env = await factory.create_basic_test_environment(db_session, creator="test_creator")
    organization = env.organization
    creator = env.creator

    with patch("app.clusters.service.create_vhost_and_user", side_effect=Exception("Mock exception")):
        with pytest.raises(Exception, match="Mock exception"):
            await create_cluster(
                db_session, organization.id, creator, cluster_create=ClusterIn(workloads_base_url="http://example.com")
            )


@pytest.mark.asyncio
async def test_update_cluster_success(db_session: AsyncSession):
    """Test successful cluster update with real database operations."""
    env = await factory.create_basic_test_environment(db_session, cluster_name="original_name")
    cluster = env.cluster
    original_name = cluster.name

    cluster_data = ClusterIn(workloads_base_url="https://updated.example.com")
    updater = "test_updater"

    result = await update_cluster(db_session, cluster, cluster_data, updater)

    await db_session.refresh(cluster)
    assert cluster.name == original_name
    assert cluster.updated_by == updater
    assert cluster.workloads_base_url == "https://updated.example.com"
    assert result.name == original_name
    assert result.workloads_base_url == "https://updated.example.com"


@pytest.mark.asyncio
async def test_delete_cluster_success(db_session: AsyncSession):
    """Test successful cluster deletion with real database operations."""
    env = await factory.create_basic_test_environment(db_session, cluster_name="Test Cluster")
    organization = env.organization
    await db_session.delete(env.project)
    await db_session.flush()
    cluster = env.cluster

    with patch("app.clusters.service.delete_vhost_and_user") as mock_delete_vhost:
        await delete_cluster(db_session, cluster)

    # Verify external service call was made
    mock_delete_vhost.assert_called_once_with(cluster.id)

    # Verify cluster was deleted from real database
    deleted_cluster = await get_cluster_in_organization(db_session, organization.id, cluster.id)
    assert deleted_cluster is None


@pytest.mark.asyncio
async def test_delete_cluster_vhost_failure(db_session: AsyncSession):
    """Test cluster deletion failure when vhost deletion fails."""
    env = await factory.create_basic_test_environment(db_session, cluster_name="Test Cluster")
    await db_session.delete(env.project)
    await db_session.flush()
    cluster = env.cluster

    # Mock vhost deletion failure and verify exception is raised
    with patch("app.clusters.service.delete_vhost_and_user", side_effect=Exception("Mock vhost exception")):
        with pytest.raises(Exception, match="Mock vhost exception"):
            await delete_cluster(db_session, cluster)


@pytest.mark.asyncio
async def test_delete_cluster_db_failure(db_session: AsyncSession):
    """Test cluster deletion failure when database operation fails."""
    env = await factory.create_basic_test_environment(db_session, cluster_name="Test Cluster")
    await db_session.delete(env.project)
    await db_session.flush()
    cluster = env.cluster

    # Mock database deletion failure and verify exception is raised
    with patch("app.clusters.service.delete_cluster_in_db", side_effect=Exception("Mock DB exception")):
        with pytest.raises(Exception, match="Mock DB exception"):
            await delete_cluster(db_session, cluster)


@pytest.mark.asyncio
async def test_delete_cluster_active_project(db_session: AsyncSession):
    """Test cluster deletion failure when cluster has active projects.."""
    env = await factory.create_basic_test_environment(db_session, cluster_name="Test Cluster")
    cluster = env.cluster

    with (
        patch("app.clusters.service.delete_vhost_and_user"),
        pytest.raises(DeletionConflictException, match="Cannot delete cluster Test Cluster"),
    ):
        await delete_cluster(db_session, cluster)


@pytest.mark.asyncio
async def test_get_clusters_with_resources(db_session: AsyncSession):
    """Test retrieving clusters with resources using real database data."""
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session, cluster_name="cluster1")
    organization = env.organization
    cluster1 = env.cluster

    # Create second cluster
    cluster2 = await factory.create_cluster(
        db_session, organization, name="cluster2", workloads_base_url="http://example.com"
    )

    # Create cluster nodes
    await factory.create_cluster_node(db_session, cluster1, name="node1", gpu_count=1, status="Ready")
    await factory.create_cluster_node(db_session, cluster1, name="node2", gpu_count=0, status="Unavailable")
    await factory.create_cluster_node(db_session, cluster2, name="node1", gpu_count=1, status="Ready")

    # Create quotas for clusters
    project1, quota1 = await factory.create_project_with_quota(
        db_session,
        organization,
        cluster1,
        project_name="project1",
        quota_cpu=1000,
        quota_gpu=1,
        quota_status=QuotaStatus.PENDING,
    )
    project2, quota2 = await factory.create_project_with_quota(
        db_session,
        organization,
        cluster1,
        project_name="project2",
        quota_cpu=500,
        quota_gpu=1,
        quota_status=QuotaStatus.DELETING,
    )
    project3, quota3 = await factory.create_project_with_quota(
        db_session,
        organization,
        cluster2,
        project_name="project3",
        quota_cpu=1000,
        quota_gpu=1,
        quota_status=QuotaStatus.READY,
    )

    result = await get_clusters_with_resources(db_session, organization)

    # Verify results with real database data
    assert isinstance(result, Clusters)
    assert len(result.clusters) == 2

    # Verify cluster data is correctly aggregated
    cluster_names = [cluster.name for cluster in result.clusters]
    assert "cluster1" in cluster_names
    assert "cluster2" in cluster_names


@pytest.mark.asyncio
async def test_validate_cluster_accessible_to_user(db_session: AsyncSession):
    """Test validating that a cluster is accessible to a user"""
    # Create real test environment using factories - disable auto project membership
    env = await factory.create_full_test_environment(
        db_session, user_email="test@example.com", cluster_name="accessible_cluster"
    )
    organization = env.organization
    user = env.user
    cluster1 = env.cluster

    project1, quota1 = await factory.create_project_with_quota(
        db_session, organization, cluster1, project_name="user_project"
    )
    user2 = await factory.create_user(db_session, organization, email="test2@example.com")

    # Test with projects accessible to user (user has access to project1)
    accessible_projects = [project1]
    await validate_cluster_accessible_to_user(accessible_projects, cluster1.id)

    # Test with no projects accessible to user2 (should raise exception)
    empty_accessible_projects: list[Project] = []
    with pytest.raises(ForbiddenException):
        await validate_cluster_accessible_to_user(empty_accessible_projects, cluster1.id)


@pytest.mark.asyncio
async def test_update_cluster_nodes(db_session: AsyncSession):
    """Test cluster nodes update with real database operations."""
    mock_message_sender = AsyncMock()
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    cluster = env.cluster

    # Create existing cluster nodes
    existing_node1 = await factory.create_cluster_node(db_session, cluster, name="node1", status="Ready")
    existing_node2 = await factory.create_cluster_node(db_session, cluster, name="node2", status="Unavailable")

    # Prepare updated node information
    updated_time = datetime.datetime.now(datetime.UTC)
    new_nodes = [
        ClusterNodeIn(
            name="node1",
            cpu_milli_cores=8000,  # Changed from 4000
            memory_bytes=16 * 1024**3,  # Changed from 8GB
            ephemeral_storage_bytes=20 * 1024**3,  # Changed from 10GB
            gpu_information=GPUInformation(
                count=2,  # Changed from 1
                type="75a0",  # Changed,
                vendor=GPUVendor.AMD,
                vram_bytes_per_device=8 * 1024**3,
                product_name="Instinct MI300A",
            ),
            status="Ready",
            is_ready=True,
        ),
        ClusterNodeIn(
            name="node3",  # New node
            cpu_milli_cores=4000,
            memory_bytes=8 * 1024**3,
            ephemeral_storage_bytes=10 * 1024**3,
            gpu_information=GPUInformation(
                count=2,
                type="74a0",
                vendor=GPUVendor.AMD,
                vram_bytes_per_device=8 * 1024**3,
                product_name="Instinct MI300A",
            ),
            status="Ready",
            is_ready=True,
        ),
    ]

    message = ClusterNodesMessage(
        message_type="cluster_nodes",
        cluster_nodes=new_nodes,
        updated_at=updated_time,
    )
    await update_cluster_nodes(db_session, cluster, message, message_sender=mock_message_sender)

    # Verify nodes were updated in real database
    updated_nodes = await get_cluster_nodes_from_db(db_session, cluster)

    # Should have 2 nodes: updated node1 and new node3 (node2 was removed)
    assert len(updated_nodes) == 2

    node_names = [node.name for node in updated_nodes]
    assert "node1" in node_names
    assert "node3" in node_names
    assert "node2" not in node_names  # Should be deleted

    # Verify node1 was updated
    node1 = next(node for node in updated_nodes if node.name == "node1")
    assert node1.cpu_milli_cores == 8000
    assert node1.memory_bytes == 16 * 1024**3
    assert node1.gpu_count == 2


@pytest.mark.asyncio
async def test_update_last_heartbeat_with_cluster_name_update(db_session: AsyncSession):
    """Test heartbeat update that also sets cluster name."""
    env = await factory.create_basic_test_environment(db_session, org_name="AMD")
    organization = env.organization
    # Create cluster without name to test name setting during heartbeat
    cluster = await factory.create_cluster(db_session, organization, name=None, workloads_base_url="http://example.com")

    message = HeartbeatMessage(
        message_type="heartbeat",
        cluster_name="test_cluster",
        organization_name="AMD",
        last_heartbeat_at=datetime.datetime.fromisoformat("2025-01-01T00:01:00+00:00"),
    )

    await update_last_heartbeat(db_session, cluster, message)

    await db_session.refresh(cluster)
    assert cluster.name == "test_cluster"
    assert cluster.last_heartbeat_at == message.last_heartbeat_at


@pytest.mark.asyncio
async def test_get_cluster_nodes(db_session: AsyncSession):
    """Test retrieving cluster nodes with real database data."""
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session)
    cluster = env.cluster

    # Create multiple cluster nodes
    node1 = await factory.create_cluster_node(db_session, cluster, name="node1", gpu_count=1, status="Ready")
    node2 = await factory.create_cluster_node(db_session, cluster, name="node2", gpu_count=0, status="Unavailable")

    result = await get_cluster_nodes(db_session, cluster)

    # Verify correct cluster nodes are returned
    assert len(result.cluster_nodes) == 2
    node_names = [node.name for node in result.cluster_nodes]
    assert "node1" in node_names
    assert "node2" in node_names


@pytest.mark.asyncio
async def test_get_cluster_with_resources(db_session: AsyncSession):
    """Test retrieving single cluster with resources using real database data."""
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    organization = env.organization
    cluster = env.cluster

    # Create cluster nodes and quotas
    await factory.create_cluster_node(db_session, cluster, name="node1", gpu_count=2, status="Ready")
    project, quota = await factory.create_project_with_quota(
        db_session, organization, cluster, project_name="Test Project With Quota", quota_cpu=1000, quota_gpu=1
    )

    result = await get_cluster_with_resources(db_session, cluster)

    # Verify cluster data is correctly populated from real database
    assert result is not None
    assert result.name == "test_cluster"
    assert result.total_node_count == 1
    assert result.available_node_count == 1  # Node is Ready, so available
    assert result.available_resources.gpu_count == 2


@pytest.mark.asyncio
async def test_create_cluster_failure(db_session: AsyncSession):
    """Test cluster creation failure when database operation fails."""
    env = await factory.create_basic_test_environment(db_session, creator="test_creator")
    organization = env.organization
    creator = env.creator

    # Mock database failure and verify exception is raised
    with patch("app.clusters.service.create_cluster_in_db", side_effect=Exception("Mock DB exception")):
        with pytest.raises(Exception, match="Mock DB exception"):
            await create_cluster(
                db_session, organization.id, creator, ClusterIn(workloads_base_url="http://example.com")
            )


@pytest.mark.asyncio
async def test_update_last_heartbeat(db_session: AsyncSession):
    """Test basic heartbeat update with real database operations."""
    env = await factory.create_basic_test_environment(db_session, org_name="AMD", cluster_name="test_cluster")
    cluster = env.cluster

    # Set up heartbeat message
    message = HeartbeatMessage(
        message_type="heartbeat",
        cluster_name="test_cluster",
        organization_name="AMD",
        last_heartbeat_at=datetime.datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
    )

    await update_last_heartbeat(db_session, cluster, message)

    # Verify cluster heartbeat was updated in real database
    await db_session.refresh(cluster)
    assert cluster.last_heartbeat_at == message.last_heartbeat_at


@pytest.mark.asyncio
async def test_update_last_heartbeat_stale(db_session: AsyncSession):
    """Test that stale heartbeat messages are ignored."""
    env = await factory.create_basic_test_environment(db_session, org_name="AMD", cluster_name="test_cluster")
    cluster = env.cluster

    # Set cluster with future heartbeat timestamp
    future_time = datetime.datetime.fromisoformat("2026-01-01T00:00:00+00:00")
    cluster.last_heartbeat_at = future_time
    await db_session.flush()

    # Set up stale heartbeat message (earlier than current)
    stale_message = HeartbeatMessage(
        message_type="heartbeat",
        cluster_name="test_cluster",
        organization_name="AMD",
        last_heartbeat_at=datetime.datetime.fromisoformat("2025-01-01T00:01:00+00:00"),
    )

    await update_last_heartbeat(db_session, cluster, stale_message)

    # Verify cluster heartbeat was NOT updated (still has future time)
    await db_session.refresh(cluster)
    assert cluster.last_heartbeat_at == future_time


@pytest.mark.asyncio
async def test_update_last_heartbeat_mismatch_organization(db_session: AsyncSession):
    """Test that heartbeat update is rejected when organization names don't match."""
    # Create real test data using factories with different organization name
    # Use None for cluster name to trigger organization name validation
    env = await factory.create_basic_test_environment(db_session, org_name="SILO")
    organization = env.organization
    # Create cluster without name to test organization name validation
    cluster = await factory.create_cluster(db_session, organization, name=None, workloads_base_url="http://example.com")
    original_heartbeat = cluster.last_heartbeat_at

    # Set up heartbeat message with mismatched organization name
    message = HeartbeatMessage(
        message_type="heartbeat",
        cluster_name="test_cluster",
        organization_name="AMD",  # Different from organization name "SILO"
        last_heartbeat_at=datetime.datetime.fromisoformat("2025-01-01T00:01:00+00:00"),
    )

    await update_last_heartbeat(db_session, cluster, message)

    # Verify cluster heartbeat was NOT updated due to organization mismatch
    await db_session.refresh(cluster)
    assert cluster.last_heartbeat_at == original_heartbeat
    # Verify cluster name was also NOT updated
    assert cluster.name is None


@pytest.mark.asyncio
async def test_updates_existing_nodes_with_new_information(db_session: AsyncSession):
    """Test that existing cluster nodes are updated with new information."""
    mock_message_sender = AsyncMock()
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    cluster = env.cluster

    # Create existing cluster nodes
    existing_node1 = await factory.create_cluster_node(
        db_session, cluster, name="node1", cpu_milli_cores=2000, memory_bytes=4 * 1024**3, gpu_count=1
    )

    # Prepare updated node information with changed specs
    updated_time = datetime.datetime.now(datetime.UTC)
    updated_nodes = [
        ClusterNodeIn(
            name="node1",
            cpu_milli_cores=4000,  # Changed from 2000
            memory_bytes=8 * 1024**3,  # Changed from 4GB
            ephemeral_storage_bytes=10 * 1024**3,
            gpu_count=1,
            gpu_type="74a0",
            gpu_vendor=GPUVendor.AMD,
            status="ready",
            is_ready=True,
        ),
    ]

    message = ClusterNodesMessage(
        message_type="cluster_nodes",
        cluster_nodes=updated_nodes,
        updated_at=updated_time,
    )
    await update_cluster_nodes(db_session, cluster, message, message_sender=mock_message_sender)

    # Verify node was updated in real database
    nodes = await get_cluster_nodes_from_db(db_session, cluster)
    assert len(nodes) == 1

    updated_node = nodes[0]
    assert updated_node.name == "node1"
    assert updated_node.cpu_milli_cores == 4000  # Verify it was updated
    assert updated_node.memory_bytes == 8 * 1024**3  # Verify it was updated


@pytest.mark.asyncio
async def test_creates_new_nodes(db_session: AsyncSession):
    """Test that new cluster nodes are created from cluster nodes message."""
    mock_message_sender = AsyncMock()
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    cluster = env.cluster

    # Prepare new node information (no existing nodes)
    updated_time = datetime.datetime.now(datetime.UTC)
    new_nodes = [
        ClusterNodeIn(
            name="node1",
            cpu_milli_cores=4000,
            memory_bytes=8 * 1024**3,
            ephemeral_storage_bytes=10 * 1024**3,
            gpu_information=GPUInformation(
                count=1,
                type="74a0",
                vendor=GPUVendor.AMD,
                vram_bytes_per_device=8 * 1024**3,
                product_name="Instinct MI300A",
            ),
            status="ready",
            is_ready=True,
        ),
    ]

    message = ClusterNodesMessage(
        message_type="cluster_nodes",
        cluster_nodes=new_nodes,
        updated_at=updated_time,
    )
    await update_cluster_nodes(db_session, cluster, message, message_sender=mock_message_sender)

    # Verify new node was created in real database
    nodes = await get_cluster_nodes_from_db(db_session, cluster)
    assert len(nodes) == 1

    new_node = nodes[0]
    assert new_node.name == "node1"
    assert new_node.cpu_milli_cores == 4000
    assert new_node.gpu_count == 1
    assert new_node.gpu_type == "74a0"
    assert new_node.gpu_vendor == GPUVendor.AMD
    assert new_node.gpu_vram_bytes_per_device == 8 * 1024**3
    assert new_node.gpu_product_name == "Instinct MI300A"


@pytest.mark.asyncio
async def test_deletes_nodes_not_in_message(db_session: AsyncSession):
    """Test that cluster nodes not present in the message are deleted."""
    mock_message_sender = AsyncMock()
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    cluster = env.cluster

    # Create existing cluster nodes
    existing_node1 = await factory.create_cluster_node(db_session, cluster, name="node1")
    existing_node2 = await factory.create_cluster_node(db_session, cluster, name="node2")

    # Prepare message with empty cluster nodes (should delete all existing nodes)
    updated_time = datetime.datetime.now(datetime.UTC)
    message = ClusterNodesMessage(
        message_type="cluster_nodes",
        cluster_nodes=[],  # Empty list - should delete all existing nodes
        updated_at=updated_time,
    )
    await update_cluster_nodes(db_session, cluster, message, message_sender=mock_message_sender)

    # Verify nodes were deleted from real database
    nodes = await get_cluster_nodes_from_db(db_session, cluster)
    assert len(nodes) == 0  # All nodes should be deleted


@pytest.mark.asyncio
async def test_get_clusters_stats(db_session: AsyncSession):
    """Test retrieving cluster statistics with real database data."""
    # Create real test environment using factories
    env = await factory.create_basic_test_environment(db_session, cluster_name="cluster1")
    organization = env.organization
    cluster1 = env.cluster

    # Create second cluster
    cluster2 = await factory.create_cluster(
        db_session, organization, name="cluster2", workloads_base_url="http://example.com"
    )

    # Create cluster nodes with different specs
    await factory.create_cluster_node(db_session, cluster1, name="node1", gpu_count=8, status="Ready", is_ready=True)
    await factory.create_cluster_node(
        db_session, cluster1, name="node2", gpu_count=8, status="Unavailable", is_ready=False
    )
    await factory.create_cluster_node(db_session, cluster2, name="node1", gpu_count=8, status="Ready", is_ready=True)
    await factory.create_cluster_node(
        db_session, cluster2, name="node2", gpu_count=0, status="Unavailable", is_ready=False
    )

    # Create quotas for clusters
    project1, quota1 = await factory.create_project_with_quota(
        db_session,
        organization,
        cluster1,
        project_name="project1",
        quota_cpu=1000,
        quota_gpu=1,
        quota_status=QuotaStatus.PENDING,
    )
    project2, quota2 = await factory.create_project_with_quota(
        db_session,
        organization,
        cluster1,
        project_name="project2",
        quota_cpu=500,
        quota_gpu=1,
        quota_status=QuotaStatus.DELETING,
    )
    project3, quota3 = await factory.create_project_with_quota(
        db_session,
        organization,
        cluster2,
        project_name="project3",
        quota_cpu=1000,
        quota_gpu=1,
        quota_status=QuotaStatus.PENDING,
    )
    project4, quota4 = await factory.create_project_with_quota(
        db_session,
        organization,
        cluster2,
        project_name="project4",
        quota_cpu=500,
        quota_gpu=1,
        quota_status=QuotaStatus.READY,
    )

    result = await get_clusters_stats(db_session, organization.id)

    # Verify statistics are correctly calculated from real database data
    assert isinstance(result, ClustersStats)
    assert result.total_cluster_count == 2
    assert result.total_node_count == 4
    assert result.total_gpu_count == 24  # 8+8+8+0 = 24 total GPUs
    assert result.total_gpu_node_count == 3  # 3 nodes with GPUs (excluding node2 in cluster2)
    assert result.available_gpu_count == 16  # 8+8 = 16 from Ready nodes
    assert result.allocated_gpu_count == 3  # 1+1+1 = 3 from non-deleting quotas (pending, pending, ready)
    assert result.available_node_count == 2  # 2 Ready nodes


@pytest.mark.asyncio
@patch("app.clusters.service.get_client_uuid", return_value=uuid4())
@patch("app.clusters.service.get_client_secret", return_value={"value": "secret"})
@patch("app.clusters.service.get_public_issuer_url", return_value="http://url.com")
@patch("app.clusters.service.build_cluster_kube_config", return_value=ClusterKubeConfig(kube_config="config"))
async def test_get_cluster_kubeconfig_as_yaml(mock_build_config, __, ___, mock_get_uuid, db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session, cluster_name="cluster1")

    result = await get_cluster_kubeconfig_as_yaml(env.cluster, MagicMock())
    assert result.kube_config == "config"
    mock_get_uuid.assert_called_once()

    call_args = mock_build_config.call_args[0]
    assert call_args[0] == env.cluster
    assert call_args[1] == "http://url.com"
    assert call_args[2] == "secret"


@pytest.mark.asyncio
async def test_get_cluster_kubeconfig_as_yaml_missing_kube_api_url(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session, cluster_name="cluster1")
    env.cluster.kube_api_url = None

    with pytest.raises(ValueError, match="does not have a kube_api_url configured"):
        await get_cluster_kubeconfig_as_yaml(env.cluster, AsyncMock())


@pytest.mark.asyncio
@patch("app.clusters.service.get_client_uuid", return_value=uuid4())
@patch("app.clusters.service.get_client_secret", return_value={})
async def test_get_cluster_kubeconfig_as_yaml_missing_client_secret(_, __, db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session, cluster_name="cluster1")
    with pytest.raises(PreconditionNotMetException, match="doesn't have secret configured"):
        await get_cluster_kubeconfig_as_yaml(env.cluster, AsyncMock())
