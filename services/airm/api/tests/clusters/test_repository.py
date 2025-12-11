# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ClusterNode, GPUInformation, GPUVendor
from app.clusters.repository import create_cluster as create_cluster_repo
from app.clusters.repository import (
    create_cluster_nodes,
    delete_cluster,
    delete_cluster_nodes,
    get_all_cluster_nodes,
    get_cluster_by_id,
    get_cluster_in_organization,
    get_cluster_nodes,
    get_cluster_nodes_by_cluster_ids,
    get_clusters_in_organization,
    update_cluster,
    update_cluster_node,
    update_last_heartbeat,
)
from app.clusters.schemas import ClusterIn, ClusterNameEdit
from tests import factory


@pytest.mark.asyncio
async def test_create_cluster(db_session: AsyncSession):
    """Test creating a cluster with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    cluster = await create_cluster_repo(
        db_session,
        env.organization.id,
        env.creator,
        ClusterIn(workloads_base_url="https://example.com", kube_api_url="https://k8s.example.com:6443"),
    )

    assert cluster.organization_id == env.organization.id
    assert cluster.created_by == env.creator
    assert cluster.name is None  # Repository function doesn't set name
    assert cluster.updated_by == env.creator
    assert cluster.workloads_base_url == "https://example.com"
    assert cluster.kube_api_url == "https://k8s.example.com:6443"


@pytest.mark.asyncio
async def test_create_cluster_duplicate_name_raises_error(db_session: AsyncSession):
    """Test that creating duplicate cluster names raises integrity error."""
    env = await factory.create_basic_test_environment(db_session)

    cluster_name = "Duplicate Cluster"

    await factory.create_cluster(
        db_session, env.organization, name=cluster_name, creator=env.creator, workloads_base_url="https://example.com"
    )

    with pytest.raises(IntegrityError):
        await factory.create_cluster(
            db_session,
            env.organization,
            name=cluster_name,
            creator=env.creator,
            workloads_base_url="https://example.com",
        )


@pytest.mark.asyncio
async def test_get_cluster_by_id(db_session: AsyncSession):
    """Test getting cluster by ID."""
    env = await factory.create_basic_test_environment(db_session)

    found_cluster = await get_cluster_by_id(db_session, env.cluster.id)

    assert found_cluster is not None
    assert found_cluster.id == env.cluster.id
    assert found_cluster.name == "test-cluster"

    non_existent_cluster = await get_cluster_by_id(db_session, uuid4())
    assert non_existent_cluster is None


@pytest.mark.asyncio
async def test_get_cluster_in_organization(db_session: AsyncSession):
    """Test getting cluster within organization scope."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, _ = environments[0]
    org2, cluster2, _ = environments[1]

    # Test: Cluster should be found in correct organization
    found_cluster = await get_cluster_in_organization(db_session, org1.id, cluster1.id)
    assert found_cluster is not None
    assert found_cluster.id == cluster1.id

    # Test: Cluster should NOT be found in different organization
    not_found = await get_cluster_in_organization(db_session, org2.id, cluster1.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_get_clusters_in_organization(db_session: AsyncSession):
    """Test getting all clusters in an organization."""
    env = await factory.create_basic_test_environment(db_session)

    # Create additional cluster in same organization
    cluster2 = await factory.create_cluster(db_session, env.organization, name="Cluster 2")

    org_clusters = await get_clusters_in_organization(db_session, env.organization.id)

    assert len(org_clusters) == 2
    cluster_names = {c.name for c in org_clusters}
    assert "test-cluster" in cluster_names  # From basic environment
    assert "Cluster 2" in cluster_names


@pytest.mark.asyncio
async def test_create_cluster_nodes(db_session: AsyncSession):
    """Test creating cluster nodes."""
    env = await factory.create_basic_test_environment(db_session)

    # Create cluster nodes
    cluster_nodes = [
        ClusterNode(
            name="node-1",
            cpu_milli_cores=4000,
            memory_bytes=8 * 1024**3,
            ephemeral_storage_bytes=100 * 1024**3,
            gpu_information=GPUInformation(
                count=1,
                type="gfx908",
                vendor=GPUVendor.AMD,
                vram_bytes_per_device=16 * 1024**3,
                product_name="MI100",
            ),
            status="Ready",
            is_ready=True,
        ),
        ClusterNode(
            name="node-2",
            cpu_milli_cores=2000,
            memory_bytes=4 * 1024**3,
            ephemeral_storage_bytes=50 * 1024**3,
            gpu_information=None,
            status="Ready",
            is_ready=True,
        ),
    ]

    created_at = datetime.now(UTC)

    # Create nodes
    created_nodes = await create_cluster_nodes(db_session, env.cluster, cluster_nodes, env.creator, created_at)

    assert len(created_nodes) == 2
    assert created_nodes[0].name == "node-1"
    assert created_nodes[0].cluster_id == env.cluster.id
    assert created_nodes[0].gpu_count == 1
    assert created_nodes[0].gpu_type == "gfx908"
    assert created_nodes[0].gpu_vendor == GPUVendor.AMD
    assert created_nodes[0].gpu_vram_bytes_per_device == 16 * 1024**3
    assert created_nodes[0].gpu_product_name == "MI100"

    assert created_nodes[1].name == "node-2"
    assert created_nodes[1].gpu_count == 0
    assert created_nodes[1].gpu_vendor is None
    assert created_nodes[1].gpu_vram_bytes_per_device is None
    assert created_nodes[1].gpu_product_name is None


@pytest.mark.asyncio
async def test_get_cluster_nodes(db_session: AsyncSession):
    """Test getting cluster nodes."""
    env = await factory.create_basic_test_environment(db_session)

    node1 = await factory.create_cluster_node(db_session, env.cluster, name="node-1", gpu_count=1)
    node2 = await factory.create_cluster_node(db_session, env.cluster, name="node-2", gpu_count=0)

    nodes = await get_cluster_nodes(db_session, env.cluster)

    assert len(nodes) == 2
    node_names = {n.name for n in nodes}
    assert "node-1" in node_names
    assert "node-2" in node_names


@pytest.mark.asyncio
async def test_delete_cluster(db_session: AsyncSession):
    """Test deleting a cluster."""
    env = await factory.create_basic_test_environment(db_session)
    cluster_id = env.cluster.id

    found_cluster = await get_cluster_by_id(db_session, cluster_id)
    assert found_cluster is not None

    # Delete cluster
    await delete_cluster(db_session, env.cluster)

    deleted_cluster = await get_cluster_by_id(db_session, cluster_id)
    assert deleted_cluster is None


@pytest.mark.asyncio
async def test_update_cluster_nodes(db_session: AsyncSession):
    """Test updating cluster nodes."""
    env = await factory.create_basic_test_environment(db_session)
    node = await factory.create_cluster_node(db_session, env.cluster, name="test-node", status="NotReady")

    updated_nodes = [
        ClusterNode(
            name="test-node",
            cpu_milli_cores=8000,  # Updated
            memory_bytes=16 * 1024**3,  # Updated
            ephemeral_storage_bytes=200 * 1024**3,
            gpu_information=GPUInformation(  # Updated
                count=2,
                type="tsla",
                vendor=GPUVendor.NVIDIA,
                vram_bytes_per_device=16 * 1024**3,
                product_name="Tesla V100",
            ),
            status="Ready",  # Updated
            is_ready=True,  # Updated
        )
    ]

    updater = "admin@example.com"
    updated_at = datetime.now(UTC)

    # Update node
    result = await update_cluster_node(db_session, node, updated_nodes[0], updater, updated_at)

    await db_session.refresh(node)
    assert node.cpu_milli_cores == 8000
    assert node.memory_bytes == 16 * 1024**3
    assert node.gpu_count == 2
    assert node.gpu_type == "tsla"
    assert node.gpu_vendor == GPUVendor.NVIDIA
    assert node.gpu_vram_bytes_per_device == 16 * 1024**3
    assert node.gpu_product_name == "Tesla V100"
    assert node.status == "Ready"
    assert node.is_ready is True
    assert node.updated_by == updater


@pytest.mark.asyncio
async def test_get_cluster_by_invalid_id_raises_exception(db_session: AsyncSession):
    """Test that invalid UUID raises database error."""
    with pytest.raises(Exception):  # Database will raise exception for invalid UUID
        await get_cluster_by_id(db_session, "invalid-uuid")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "edit_obj, expected",
    [
        (
            ClusterIn(
                workloads_base_url="https://updated.example.com", kube_api_url="https://k8s.updated.example.com:6443"
            ),
            {
                "name": "original-name",
                "workloads_base_url": "https://updated.example.com",
                "kube_api_url": "https://k8s.updated.example.com:6443",
            },
        ),
        (
            ClusterNameEdit(name="updated-name"),
            {
                "name": "updated-name",
                "workloads_base_url": "https://example.com",
                "kube_api_url": "https://k8s.example.com:6443",
            },
        ),
    ],
)
async def test_update_cluster(db_session: AsyncSession, edit_obj, expected):
    """Test updating cluster attributes with parametrize."""
    env = await factory.create_basic_test_environment(db_session)
    cluster = await factory.create_cluster(
        db_session, env.organization, name="original-name", workloads_base_url="https://example.com"
    )
    updated_by = "updater@example.com"

    updated_cluster = await update_cluster(db_session, cluster, edit_obj, updated_by)

    assert updated_cluster.name == expected["name"]
    assert updated_cluster.workloads_base_url == expected["workloads_base_url"]
    assert updated_cluster.kube_api_url == expected["kube_api_url"]
    assert updated_cluster.updated_by == updated_by


@pytest.mark.asyncio
async def test_update_last_heartbeat(db_session: AsyncSession):
    """Test updating cluster last heartbeat timestamp."""
    env = await factory.create_basic_test_environment(db_session)

    timestamp = datetime.now(UTC)
    await update_last_heartbeat(db_session, env.cluster, timestamp)

    await db_session.refresh(env.cluster)
    assert env.cluster.last_heartbeat_at == timestamp


@pytest.mark.asyncio
async def test_delete_cluster_nodes(db_session: AsyncSession):
    """Test bulk deletion of cluster nodes."""
    env = await factory.create_basic_test_environment(db_session)

    # Create multiple nodes
    node1 = await factory.create_cluster_node(db_session, env.cluster, name="node-1")
    node2 = await factory.create_cluster_node(db_session, env.cluster, name="node-2")
    node3 = await factory.create_cluster_node(db_session, env.cluster, name="node-3")

    nodes_to_delete = [node1, node3]
    await delete_cluster_nodes(db_session, nodes_to_delete)

    remaining_nodes = await get_cluster_nodes(db_session, env.cluster)
    assert len(remaining_nodes) == 1
    assert remaining_nodes[0].name == "node-2"


@pytest.mark.asyncio
async def test_delete_cluster_deletes_nodes(db_session: AsyncSession):
    """Test that deleting cluster also deletes associated nodes."""
    env = await factory.create_basic_test_environment(db_session)

    # Create nodes
    await factory.create_cluster_node(db_session, env.cluster, name="node-1")
    await factory.create_cluster_node(db_session, env.cluster, name="node-2")

    nodes_before = await get_cluster_nodes(db_session, env.cluster)
    assert len(nodes_before) == 2

    # Delete cluster
    await delete_cluster(db_session, env.cluster)

    all_nodes = await get_all_cluster_nodes(db_session)
    cluster_node_ids = [n.id for n in all_nodes if n.cluster_id == env.cluster.id]
    assert len(cluster_node_ids) == 0


@pytest.mark.asyncio
async def test_get_cluster_nodes_by_cluster_ids(db_session: AsyncSession):
    """Test getting nodes for multiple clusters."""
    env = await factory.create_basic_test_environment(db_session)
    cluster2 = await factory.create_cluster(db_session, env.organization, name="Cluster 2")

    # Create nodes in both clusters
    await factory.create_cluster_node(db_session, env.cluster, name="cluster1-node1")
    await factory.create_cluster_node(db_session, env.cluster, name="cluster1-node2")
    await factory.create_cluster_node(db_session, cluster2, name="cluster2-node1")

    cluster_ids = [env.cluster.id, cluster2.id]
    nodes = await get_cluster_nodes_by_cluster_ids(db_session, cluster_ids)

    assert len(nodes) == 3
    cluster_node_names = {n.name for n in nodes}
    assert "cluster1-node1" in cluster_node_names
    assert "cluster1-node2" in cluster_node_names
    assert "cluster2-node1" in cluster_node_names


@pytest.mark.asyncio
async def test_get_all_cluster_nodes(db_session: AsyncSession):
    """Test getting all cluster nodes across all clusters."""
    env = await factory.create_basic_test_environment(db_session)
    cluster2 = await factory.create_cluster(db_session, env.organization, name="Cluster 2")

    # Create nodes in both clusters
    await factory.create_cluster_node(db_session, env.cluster, name="global-node1")
    await factory.create_cluster_node(db_session, cluster2, name="global-node2")

    all_nodes = await get_all_cluster_nodes(db_session)

    # Should include at least our test nodes (there might be others from other tests)
    node_names = {n.name for n in all_nodes}
    assert "global-node1" in node_names
    assert "global-node2" in node_names
