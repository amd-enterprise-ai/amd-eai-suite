# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import QuotaStatus
from app.quotas.repository import (
    create_quota,
    get_quotas_by_cluster_ids,
    get_quotas_for_cluster,
    get_quotas_for_organization,
    update_quota,
    update_quota_status,
)
from app.quotas.schemas import QuotaCreate, QuotaUpdate
from tests import factory

__default_quota_quantities = {
    "gpu_count": 1,
    "cpu_milli_cores": 1000,
    "memory_bytes": 1000,
    "ephemeral_storage_bytes": 1000,
    "status": QuotaStatus.PENDING,
}


@pytest.mark.asyncio
async def test_get_quotas_for_cluster(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    org = env.organization
    cluster1 = env.cluster
    project1 = env.project

    # Create additional projects in the clusters
    project2 = await factory.create_project(db_session, org, cluster1, name="Test Project 2")

    # Create another cluster in the same organization
    cluster2 = await factory.create_cluster(db_session, org, name="Test Cluster2")
    project3 = await factory.create_project(db_session, org, cluster2, name="Test Project 3")

    quota1 = await factory.create_quota(db_session, org, cluster1, project1, gpu_count=1, status=QuotaStatus.PENDING)
    quota2 = await factory.create_quota(db_session, org, cluster1, project2, gpu_count=2, status=QuotaStatus.DELETING)
    quota3 = await factory.create_quota(db_session, org, cluster2, project3, gpu_count=0, status=QuotaStatus.READY)

    quotas = await get_quotas_for_cluster(db_session, cluster1.id)
    assert len(quotas) == 2
    assert quotas[0].cluster_id == cluster1.id
    assert quotas[0].project is not None
    assert quotas[0].project.id == project1.id


@pytest.mark.asyncio
async def test_get_quotas_for_organization(db_session: AsyncSession):
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create additional projects
    project3 = await factory.create_project(db_session, org1, cluster1, name="test-project-2")
    project4 = await factory.create_project(db_session, org2, cluster2, name="test-project-3")

    quota1 = await factory.create_quota(db_session, org1, cluster1, project1, gpu_count=1, status=QuotaStatus.PENDING)
    quota2 = await factory.create_quota(db_session, org1, cluster1, project3, gpu_count=2, status=QuotaStatus.DELETING)
    quota3 = await factory.create_quota(db_session, org2, cluster2, project4, gpu_count=0, status=QuotaStatus.READY)

    quotas = await get_quotas_for_organization(db_session, org1.id)
    assert len(quotas) == 2
    assert quotas[0].cluster_id == cluster1.id
    assert quotas[0].project is not None
    assert quotas[0].project.id in [project1.id, project3.id]


@pytest.mark.asyncio
async def test_get_quotas_by_cluster_ids(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    # Create additional clusters and projects
    cluster2 = await factory.create_cluster(db_session, env.organization, name="Test Cluster2")
    cluster3 = await factory.create_cluster(db_session, env.organization, name="Test Cluster3")

    project1 = await factory.create_project(db_session, env.organization, env.cluster, name="Test Project1")
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="Test Project2")
    project3 = await factory.create_project(db_session, env.organization, cluster2, name="Test Project3")
    project4 = await factory.create_project(db_session, env.organization, cluster3, name="Test Project4")

    quota1 = await factory.create_quota(
        db_session, env.organization, env.cluster, project1, **__default_quota_quantities
    )
    quota2 = await factory.create_quota(
        db_session, env.organization, env.cluster, project2, **__default_quota_quantities
    )
    quota3 = await factory.create_quota(db_session, env.organization, cluster2, project3, **__default_quota_quantities)
    quota4 = await factory.create_quota(db_session, env.organization, cluster3, project4, **__default_quota_quantities)

    assert len(await get_quotas_by_cluster_ids(db_session, [env.cluster.id, cluster2.id])) == 3
    assert len(await get_quotas_by_cluster_ids(db_session, [cluster3.id])) == 1


@pytest.mark.asyncio
async def test_create_quota(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    quota = QuotaCreate(
        cpu_milli_cores=2000,
        memory_bytes=2 * 1024**3,
        ephemeral_storage_bytes=20 * 1024**3,
        gpu_count=2,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
    )

    created_quota = await create_quota(
        db_session, env.project.id, env.cluster.id, quota, QuotaStatus.PENDING.value, "test-creator"
    )

    assert created_quota.id is not None

    assert created_quota.cpu_milli_cores == 2000
    assert created_quota.memory_bytes == 2 * 1024**3
    assert created_quota.ephemeral_storage_bytes == 20 * 1024**3
    assert created_quota.gpu_count == 2
    assert created_quota.cluster_id == env.cluster.id
    assert created_quota.project_id == env.project.id
    assert created_quota.status == QuotaStatus.PENDING.value
    assert created_quota.created_by == "test-creator"
    assert created_quota.updated_by == "test-creator"


@pytest.mark.asyncio
async def test_create_quota_minimum_values(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    quota_in = QuotaCreate(
        cpu_milli_cores=0,
        memory_bytes=0,
        ephemeral_storage_bytes=0,
        gpu_count=0,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
    )

    created_quota = await create_quota(
        db_session, env.project.id, env.cluster.id, quota_in, QuotaStatus.READY.value, "test-admin"
    )

    assert created_quota.cpu_milli_cores == 0
    assert created_quota.memory_bytes == 0
    assert created_quota.ephemeral_storage_bytes == 0
    assert created_quota.gpu_count == 0
    assert created_quota.status == QuotaStatus.READY.value


@pytest.mark.asyncio
async def test_update_quota_from_allocation(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    quota = await factory.create_quota(
        db_session, env.organization, env.cluster, env.project, **__default_quota_quantities
    )

    edits = QuotaUpdate(
        cpu_milli_cores=100,
        ephemeral_storage_bytes=100,
        memory_bytes=200,
        gpu_count=2,
    )

    await update_quota(db_session, quota, edits, QuotaStatus.FAILED, "reason", "system", datetime.now(tz=UTC))

    quotas = await get_quotas_for_organization(db_session, env.organization.id)
    assert len(quotas) == 1
    updated = quotas[0]

    assert updated is not None
    assert updated.cpu_milli_cores == 100
    assert updated.gpu_count == 2
    assert updated.ephemeral_storage_bytes == 100
    assert updated.memory_bytes == 200
    assert updated.status == QuotaStatus.FAILED
    assert updated.status_reason == "reason"
    assert updated.updated_by == "system"


@pytest.mark.asyncio
async def test_update_quota_status(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    quota = await factory.create_quota(
        db_session, env.organization, env.cluster, env.project, **__default_quota_quantities
    )

    await update_quota_status(db_session, quota, QuotaStatus.READY, "reason", "system", datetime.now(tz=UTC))
    quotas = await get_quotas_for_organization(db_session, env.organization.id)
    assert len(quotas) == 1
    updated = quotas[0]

    assert updated is not None
    assert updated.status == QuotaStatus.READY
    assert updated.status_reason == "reason"


@pytest.mark.asyncio
async def test_update_quota(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    quota = await factory.create_quota(
        db_session,
        env.organization,
        env.cluster,
        env.project,
        gpu_count=1,
        cpu_milli_cores=1000,
        memory_bytes=1000,
        ephemeral_storage_bytes=1000,
        status=QuotaStatus.PENDING,
    )

    edits = QuotaUpdate(
        cpu_milli_cores=2000,
        memory_bytes=2 * 1024**3,
        ephemeral_storage_bytes=20 * 1024**3,
        gpu_count=2,
    )

    updated_quota = await update_quota(db_session, quota, edits, QuotaStatus.PENDING, None, "test-updater")

    assert updated_quota.id is not None
    assert updated_quota.cpu_milli_cores == 2000
    assert updated_quota.memory_bytes == 2 * 1024**3
    assert updated_quota.ephemeral_storage_bytes == 20 * 1024**3
    assert updated_quota.gpu_count == 2
    assert updated_quota.cluster_id == env.cluster.id
    assert updated_quota.project_id == env.project.id
    assert updated_quota.status == QuotaStatus.PENDING.value
    assert updated_quota.updated_by == "test-updater"


@pytest.mark.asyncio
async def test_update_quota_minimum_values(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    quota = await factory.create_quota(
        db_session,
        env.organization,
        env.cluster,
        env.project,
        gpu_count=1,
        cpu_milli_cores=1000,
        memory_bytes=1000,
        ephemeral_storage_bytes=1000,
        status=QuotaStatus.PENDING,
    )

    edits = QuotaUpdate(
        cpu_milli_cores=0,
        memory_bytes=0,
        ephemeral_storage_bytes=0,
        gpu_count=0,
    )

    updated_quota = await update_quota(db_session, quota, edits, QuotaStatus.PENDING, None, "test-updater")

    assert updated_quota.id is not None
    assert updated_quota.cpu_milli_cores == 0
    assert updated_quota.memory_bytes == 0
    assert updated_quota.ephemeral_storage_bytes == 0
    assert updated_quota.gpu_count == 0
    assert updated_quota.cluster_id == env.cluster.id
    assert updated_quota.project_id == env.project.id
    assert updated_quota.status == QuotaStatus.PENDING.value
    assert updated_quota.updated_by == "test-updater"
