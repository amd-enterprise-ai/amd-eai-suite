# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import QuotaStatus
from app.quotas.constants import DEFAULT_CATCH_ALL_QUOTA_NAME
from app.quotas.utils import calculate_dynamic_catch_all_quota_allocation
from tests import factory


@pytest.mark.asyncio
async def test_calculate_dynamic_catch_all_quota_allocation(db_session: AsyncSession):
    """Test dynamic catch-all quota calculation based on cluster nodes and allocated quotas."""
    # Create a test environment
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    cluster = env.cluster

    # Create cluster nodes with specific resources
    node1 = await factory.create_cluster_node(
        db_session,
        cluster,
        name="node1",
        cpu_milli_cores=8000,  # 8 cores
        memory_bytes=16 * 1024**3,  # 16GB
        ephemeral_storage_bytes=100 * 1024**3,  # 100GB
        gpu_count=2,
        is_ready=True,
    )

    node2 = await factory.create_cluster_node(
        db_session,
        cluster,
        name="node2",
        cpu_milli_cores=4000,  # 4 cores
        memory_bytes=8 * 1024**3,  # 8GB
        ephemeral_storage_bytes=50 * 1024**3,  # 50GB
        gpu_count=1,
        is_ready=True,
    )

    # Create a non-ready node that should not be included
    await factory.create_cluster_node(
        db_session,
        cluster,
        name="node3",
        cpu_milli_cores=4000,
        memory_bytes=8 * 1024**3,
        ephemeral_storage_bytes=50 * 1024**3,
        gpu_count=1,
        is_ready=False,  # Not ready, should be excluded
    )

    # Total cluster resources from ready nodes only:
    # CPU: 8000 + 4000 = 12000 milli-cores
    # Memory: 16GB + 8GB = 24GB
    # Storage: 100GB + 50GB = 150GB
    # GPU: 2 + 1 = 3

    # Create projects with quotas that allocate some resources
    project1 = await factory.create_project(db_session, env.organization, cluster, name="project1")
    quota1 = await factory.create_quota(
        db_session,
        env.organization,
        cluster,
        project1,
        cpu_milli_cores=2000,  # 2 cores
        memory_bytes=4 * 1024**3,  # 4GB
        ephemeral_storage_bytes=20 * 1024**3,  # 20GB
        gpu_count=1,
    )

    project2 = await factory.create_project(db_session, env.organization, cluster, name="project2")
    quota2 = await factory.create_quota(
        db_session,
        env.organization,
        cluster,
        project2,
        cpu_milli_cores=3000,  # 3 cores
        memory_bytes=6 * 1024**3,  # 6GB
        ephemeral_storage_bytes=30 * 1024**3,  # 30GB
        gpu_count=1,
    )

    # Total allocated resources:
    # CPU: 2000 + 3000 = 5000 milli-cores
    # Memory: 4GB + 6GB = 10GB
    # Storage: 20GB + 30GB = 50GB
    # GPU: 1 + 1 = 2

    # Expected remaining resources for catch-all:
    # CPU: 12000 - 5000 = 7000 milli-cores
    # Memory: 24GB - 10GB = 14GB
    # Storage: 150GB - 50GB = 100GB
    # GPU: 3 - 2 = 1

    await db_session.commit()

    # Refresh cluster object to ensure it's properly loaded
    await db_session.refresh(cluster)

    # Calculate dynamic catch-all quota
    dynamic_quota = await calculate_dynamic_catch_all_quota_allocation(db_session, cluster)

    # Verify the calculations
    assert dynamic_quota.cpu_milli_cores == 7000
    assert dynamic_quota.memory_bytes == 14 * 1024**3
    assert dynamic_quota.ephemeral_storage_bytes == 100 * 1024**3
    assert dynamic_quota.gpu_count == 1
    assert dynamic_quota.quota_name == DEFAULT_CATCH_ALL_QUOTA_NAME
    assert dynamic_quota.namespaces == []


@pytest.mark.asyncio
async def test_calculate_dynamic_catch_all_quota_allocation_with_deleting_quota(db_session: AsyncSession):
    """Test that DELETING quotas are excluded from allocated resources calculation."""
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    cluster = env.cluster

    # Create cluster node
    await factory.create_cluster_node(
        db_session,
        cluster,
        name="node1",
        cpu_milli_cores=8000,
        memory_bytes=16 * 1024**3,
        ephemeral_storage_bytes=100 * 1024**3,
        gpu_count=2,
        is_ready=True,
    )

    # Create project with READY quota
    project1 = await factory.create_project(db_session, env.organization, cluster, name="project1")
    await factory.create_quota(
        db_session,
        env.organization,
        cluster,
        project1,
        cpu_milli_cores=2000,
        memory_bytes=4 * 1024**3,
        ephemeral_storage_bytes=20 * 1024**3,
        gpu_count=1,
        status=QuotaStatus.READY,
    )

    # Create project with DELETING quota (should be excluded)
    project2 = await factory.create_project(db_session, env.organization, cluster, name="project2")
    await factory.create_quota(
        db_session,
        env.organization,
        cluster,
        project2,
        cpu_milli_cores=3000,
        memory_bytes=6 * 1024**3,
        ephemeral_storage_bytes=30 * 1024**3,
        gpu_count=1,
        status=QuotaStatus.DELETING,
    )

    await db_session.commit()

    # Refresh cluster object to ensure it's properly loaded
    await db_session.refresh(cluster)

    # Calculate dynamic catch-all quota
    dynamic_quota = await calculate_dynamic_catch_all_quota_allocation(db_session, cluster)

    # Should only count the READY quota, not the DELETING one
    # Remaining: 8000 - 2000 = 6000 CPU, 16GB - 4GB = 12GB, etc.
    assert dynamic_quota.cpu_milli_cores == 6000
    assert dynamic_quota.memory_bytes == 12 * 1024**3
    assert dynamic_quota.ephemeral_storage_bytes == 80 * 1024**3
    assert dynamic_quota.gpu_count == 1


@pytest.mark.asyncio
async def test_calculate_dynamic_catch_all_quota_allocation_overallocated(db_session: AsyncSession):
    """Test that quota calculation handles overallocated clusters gracefully."""
    env = await factory.create_basic_test_environment(db_session, cluster_name="test_cluster")
    cluster = env.cluster

    # Create small cluster node
    await factory.create_cluster_node(
        db_session,
        cluster,
        name="node1",
        cpu_milli_cores=2000,  # 2 cores
        memory_bytes=4 * 1024**3,  # 4GB
        ephemeral_storage_bytes=20 * 1024**3,  # 20GB
        gpu_count=1,
        is_ready=True,
    )

    # Create projects that over-allocate cluster resources
    project1 = await factory.create_project(db_session, env.organization, cluster, name="project1")
    await factory.create_quota(
        db_session,
        env.organization,
        cluster,
        project1,
        cpu_milli_cores=3000,  # More than available
        memory_bytes=6 * 1024**3,  # More than available
        ephemeral_storage_bytes=30 * 1024**3,  # More than available
        gpu_count=2,  # More than available
    )

    await db_session.commit()

    # Refresh cluster object to ensure it's properly loaded
    await db_session.refresh(cluster)

    # Calculate dynamic catch-all quota
    dynamic_quota = await calculate_dynamic_catch_all_quota_allocation(db_session, cluster)

    # Should return 0 for all resources (not negative values)
    assert dynamic_quota.cpu_milli_cores == 0
    assert dynamic_quota.memory_bytes == 0
    assert dynamic_quota.ephemeral_storage_bytes == 0
    assert dynamic_quota.gpu_count == 0
