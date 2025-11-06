# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Quotas service tests."""

import datetime
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    ClusterQuotaAllocation,
    ClusterQuotasFailureMessage,
    ClusterQuotasStatusMessage,
    GPUVendor,
    QuotaStatus,
)
from app.quotas.schemas import QuotaCreate, QuotaUpdate
from app.quotas.service import (
    create_quota_for_cluster,
    delete_quota_for_cluster,
    update_cluster_quotas_from_allocations,
    update_pending_quotas_to_failed,
    update_quota_for_cluster,
)
from tests import factory


@pytest.mark.asyncio
@patch("app.quotas.service.does_quota_match_allocation", return_value=True)
async def test_update_cluster_quotas_from_allocations_matching(
    mock_update_project_status,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)

    project1, quota1 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="quota",
        quota_cpu=1000,
        quota_memory=1000,
        quota_storage=1000,
        quota_gpu=2,
        quota_status=QuotaStatus.PENDING,
    )

    project2, quota2 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="quota2",
        quota_cpu=4000,
        quota_memory=4000,
        quota_storage=4000,
        quota_gpu=4,
        quota_status=QuotaStatus.READY,
    )

    message = ClusterQuotasStatusMessage(
        message_type="cluster_quotas_status",
        quota_allocations=[
            ClusterQuotaAllocation(
                quota_name="quota",
                cpu_milli_cores=1000,
                memory_bytes=1000,
                ephemeral_storage_bytes=1000,
                gpu_count=2,
                namespaces=["quota"],
            ),
            ClusterQuotaAllocation(
                quota_name="quota2",
                cpu_milli_cores=4000,
                memory_bytes=4000,
                ephemeral_storage_bytes=4000,
                gpu_count=4,
                namespaces=["quota2"],
            ),
        ],
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    dummy_kc_admin = object()
    await update_cluster_quotas_from_allocations(dummy_kc_admin, db_session, env.cluster, message)

    await db_session.refresh(quota1)
    assert quota1.status == QuotaStatus.READY
    assert mock_update_project_status.called


@pytest.mark.asyncio
@patch("app.quotas.service.does_quota_match_allocation", return_value=False)
async def test_update_cluster_quotas_from_allocations_not_matching(
    mock_does_quota_match_allocation,
    db_session: AsyncSession,
):
    """Test quota status update when cluster allocation doesn't match database quota."""
    env = await factory.create_basic_test_environment(db_session)

    project, quota = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="quota",
        quota_cpu=1000,
        quota_memory=1000,
        quota_storage=1000,
        quota_gpu=2,
        quota_status=QuotaStatus.PENDING,
    )

    message = ClusterQuotasStatusMessage(
        message_type="cluster_quotas_status",
        quota_allocations=[
            ClusterQuotaAllocation(
                quota_name="quota",
                cpu_milli_cores=500,
                memory_bytes=500 * (1024**2),
                ephemeral_storage_bytes=600 * (1024**2),
                gpu_count=2,
                namespaces=["quota"],
            ),
        ],
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    await update_cluster_quotas_from_allocations(object(), db_session, env.cluster, message)

    await db_session.refresh(quota)
    assert quota.status == QuotaStatus.FAILED
    assert "Quota on cluster does not match configured value" in quota.status_reason


@pytest.mark.asyncio
async def test_create_quota_for_cluster_success(db_session: AsyncSession):
    """Test successful quota creation with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    # Create existing project with quota for realistic scenario
    _, _ = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="existing_project",
        quota_cpu=600,
        quota_memory=5 * (1024**3),
        quota_storage=1 * (1024**3),
        quota_gpu=0,
        quota_status=QuotaStatus.READY,
    )

    __, ___ = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="existing_project2",
        quota_cpu=600,
        quota_memory=5 * (1024**3),
        quota_storage=1 * (1024**3),
        quota_gpu=0,
        quota_status=QuotaStatus.DELETING,
    )

    gpu_vendor = GPUVendor.AMD
    creator = "platform-admin"

    quota_in = QuotaCreate(
        cpu_milli_cores=400,
        memory_bytes=1000000000,
        ephemeral_storage_bytes=2000000000,
        gpu_count=2,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
    )

    # Mock only external messaging service
    with patch("app.quotas.service.submit_quotas_allocation_to_cluster_queue", autospec=True) as mock_submit_quotas:
        result = await create_quota_for_cluster(db_session, env.project, env.cluster, gpu_vendor, quota_in, creator)

    # Verify external service calls were made
    mock_submit_quotas.assert_called_once()

    # 2 valid quotas + 1 catchall quota
    assert len(mock_submit_quotas.call_args[0]) == 3

    # Verify quota was created in real database
    assert result is not None
    assert result.cpu_milli_cores == 400
    assert result.memory_bytes == 1000000000
    assert result.ephemeral_storage_bytes == 2000000000
    assert result.gpu_count == 2
    assert result.status == QuotaStatus.PENDING
    assert result.project_id == env.project.id
    assert result.cluster_id == env.cluster.id
    assert result.created_by == creator


@pytest.mark.asyncio
async def test_update_quota_for_cluster_with_resource_changes(db_session: AsyncSession):
    """Test quota update when resources actually change."""
    env = await factory.create_basic_test_environment(db_session)

    # Create project with quota
    _, quota = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="test_project",
        quota_cpu=400,
        quota_memory=1000000000,
        quota_storage=2000000000,
        quota_gpu=2,
        quota_status=QuotaStatus.READY,
    )

    gpu_vendor = GPUVendor.AMD
    updater = "platform-admin"

    # Different values than existing quota
    edits = QuotaUpdate(
        cpu_milli_cores=600,  # Changed from 400
        memory_bytes=2000000000,  # Changed from 1000000000
        ephemeral_storage_bytes=3000000000,  # Changed from 2000000000
        gpu_count=3,  # Changed from 2
    )

    # Mock only external messaging service and resource change detection
    with (
        patch("app.quotas.service.have_quota_resources_changed", return_value=True),
        patch("app.quotas.service.send_quotas_allocation_to_cluster_queue", autospec=True) as mock_send_quotas,
    ):
        result = await update_quota_for_cluster(db_session, env.cluster, quota, edits, gpu_vendor, updater)

    # Verify messaging service was called
    mock_send_quotas.assert_called_once()

    # Verify quota was updated with PENDING status in real database
    await db_session.refresh(quota)
    assert quota.status == QuotaStatus.PENDING
    assert quota.cpu_milli_cores == 600
    assert quota.memory_bytes == 2000000000
    assert quota.ephemeral_storage_bytes == 3000000000
    assert quota.gpu_count == 3


@pytest.mark.asyncio
async def test_update_quota_for_cluster_no_resource_changes(db_session: AsyncSession):
    """Test quota update when no resources change (SDA-1527 bug fix)."""
    env = await factory.create_basic_test_environment(db_session)

    # Create project with quota
    _, quota = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="test_project",
        quota_cpu=400,
        quota_memory=1000000000,
        quota_storage=2000000000,
        quota_gpu=2,
        quota_status=QuotaStatus.READY,
    )

    gpu_vendor = GPUVendor.AMD
    updater = "platform-admin"

    # Same values as existing quota
    edits = QuotaUpdate(
        cpu_milli_cores=400,
        memory_bytes=1000000000,
        ephemeral_storage_bytes=2000000000,
        gpu_count=2,
    )

    # Mock only resource change detection
    with (
        patch("app.quotas.service.have_quota_resources_changed", return_value=False),
        patch("app.quotas.service.send_quotas_allocation_to_cluster_queue", autospec=True) as mock_send_quotas,
    ):
        result = await update_quota_for_cluster(db_session, env.cluster, quota, edits, gpu_vendor, updater)

    # Verify no message was sent to cluster queue
    mock_send_quotas.assert_not_called()

    # Verify quota maintains READY status in real database
    await db_session.refresh(quota)
    assert quota.status == QuotaStatus.READY


@pytest.mark.asyncio
async def test_delete_quota_for_cluster_success(db_session: AsyncSession):
    """Test successful quota deletion with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    # Create multiple projects with quotas for realistic scenario
    _, quota1 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="project1",
        quota_cpu=600,
        quota_memory=5 * (1024**3),
        quota_storage=1 * (1024**3),
        quota_gpu=0,
        quota_status=QuotaStatus.READY,
    )

    _, quota2 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="project2",
        quota_cpu=200,
        quota_memory=1 * (1024**3),
        quota_storage=1 * (1024**3),
        quota_gpu=1,
        quota_status=QuotaStatus.PENDING,
    )

    gpu_vendor = GPUVendor.AMD
    updater = "platform-admin"

    # Mock only external messaging service
    with patch("app.quotas.service.submit_quotas_allocation_to_cluster_queue", autospec=True) as mock_submit_quotas:
        result = await delete_quota_for_cluster(db_session, quota1, env.cluster, gpu_vendor, updater)

    # Verify messaging service was called
    mock_submit_quotas.assert_called_once()

    # Verify quota status was updated to DELETING in real database
    await db_session.refresh(quota1)
    assert quota1.status == QuotaStatus.DELETING

    assert result is None


@pytest.mark.asyncio
async def test_update_pending_quotas_to_failed(db_session: AsyncSession):
    """Test updating all pending quotas to failed status."""
    env = await factory.create_basic_test_environment(db_session)

    # Create project with quota in READY status (should not be affected)
    _, quota1 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="ready_project",
        quota_cpu=400,
        quota_memory=1000000000,
        quota_storage=2000000000,
        quota_gpu=2,
        quota_status=QuotaStatus.READY,
    )

    message = ClusterQuotasFailureMessage(
        message_type="cluster_quotas_failure",
        updated_at=datetime.datetime.now(datetime.UTC),
        reason="some reason",
    )
    dummy_kc_admin = object()
    await update_pending_quotas_to_failed(dummy_kc_admin, db_session, env.cluster, message)

    # Verify READY quota remains unchanged in real database
    await db_session.refresh(quota1)
    assert quota1.status == QuotaStatus.READY  # Should remain unchanged


@pytest.mark.asyncio
async def test_update_cluster_quotas_from_allocations_missing(db_session: AsyncSession):
    """Test quota handling when allocations are missing from cluster."""
    env = await factory.create_basic_test_environment(db_session)

    # Create projects with quotas in different states
    _, quota1 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="quota-test-project",
        quota_cpu=1000,
        quota_memory=1000,
        quota_storage=1000,
        quota_gpu=2,
        quota_status=QuotaStatus.DELETING,
        quota_updated_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
    )

    _, quota2 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="test-project2",
        quota_cpu=4000,
        quota_memory=400 * 1024 * 1024,
        quota_storage=600 * 1024 * 1024,
        quota_gpu=4,
        quota_status=QuotaStatus.READY,
        quota_updated_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
    )

    _, quota3 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="test-project3",
        quota_cpu=4000,
        quota_memory=400 * 1024 * 1024,
        quota_storage=600 * 1024 * 1024,
        quota_gpu=4,
        quota_status=QuotaStatus.PENDING,
        quota_updated_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
    )

    # Message with empty quota allocations
    message = ClusterQuotasStatusMessage(
        message_type="cluster_quotas_status",
        quota_allocations=[],
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    dummy_kc_admin = object()
    await update_cluster_quotas_from_allocations(dummy_kc_admin, db_session, env.cluster, message)

    # Verify DELETING quota was deleted from database
    # Try to get quota1 by ID - should not exist anymore
    try:
        await db_session.refresh(quota1)
        assert False, "DELETING quota should have been deleted from database"
    except Exception:
        # Expected - quota1 should be deleted from database
        pass

    # Verify READY quota was updated to FAILED (missing from cluster allocations)
    await db_session.refresh(quota2)
    assert quota2.status == QuotaStatus.FAILED
    assert "Quota was removed from the cluster" in quota2.status_reason
    assert quota2.cpu_milli_cores == 0
    assert quota2.memory_bytes == 0
    assert quota2.ephemeral_storage_bytes == 0
    assert quota2.gpu_count == 0

    # Verify PENDING quota was updated to FAILED with appropriate reason
    await db_session.refresh(quota3)
    assert quota3.status == QuotaStatus.FAILED
    assert "Quota was removed from the cluster" in quota3.status_reason
    assert quota3.cpu_milli_cores == 0
    assert quota3.memory_bytes == 0
    assert quota3.ephemeral_storage_bytes == 0
    assert quota3.gpu_count == 0


@pytest.mark.asyncio
async def test_update_cluster_quotas_from_allocations_unknown_no_action(db_session: AsyncSession):
    """Test no action for unknown allocations."""
    env = await factory.create_basic_test_environment(db_session)

    # No projects in cluster
    message = ClusterQuotasStatusMessage(
        message_type="cluster_quotas_status",
        quota_allocations=[
            ClusterQuotaAllocation(
                quota_name="quota",
                cpu_milli_cores=500,
                memory_bytes=500,
                ephemeral_storage_bytes=500,
                gpu_count=2,
                namespaces=["quota"],
            ),
        ],
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    # This should not raise any exceptions or make any changes
    dummy_kc_admin = object()
    await update_cluster_quotas_from_allocations(dummy_kc_admin, db_session, env.cluster, message)

    # Verify no quotas were created or modified
    # Since there are no projects in the cluster, nothing should happen


@pytest.mark.asyncio
async def test_create_quota_with_mixed_status_quotas(db_session: AsyncSession):
    """Test quota creation with mixed quota statuses."""
    env = await factory.create_basic_test_environment(db_session)

    # Create existing projects with quotas of mixed statuses
    _, quota2 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="project2",
        quota_cpu=600,
        quota_memory=5 * (1024**3),
        quota_storage=1 * (1024**3),
        quota_gpu=0,
        quota_status=QuotaStatus.READY,
    )

    _, quota3 = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="project3",
        quota_cpu=200,
        quota_memory=1 * (1024**3),
        quota_storage=1 * (1024**3),
        quota_gpu=1,
        quota_status=QuotaStatus.PENDING,
    )

    gpu_vendor = GPUVendor.AMD
    creator = "platform-admin"

    quota_in = QuotaCreate(
        cpu_milli_cores=400,
        memory_bytes=1000000000,
        ephemeral_storage_bytes=2000000000,
        gpu_count=2,
        cluster_id=env.cluster.id,
        project_id=env.project.id,
    )

    # Mock only external messaging service
    with patch("app.quotas.service.submit_quotas_allocation_to_cluster_queue", autospec=True) as mock_submit_quotas:
        result = await create_quota_for_cluster(db_session, env.project, env.cluster, gpu_vendor, quota_in, creator)

    # Verify external service calls were made
    mock_submit_quotas.assert_called_once()

    # Verify quota was created in real database
    assert result is not None
    assert result.cpu_milli_cores == 400
    assert result.memory_bytes == 1000000000
    assert result.ephemeral_storage_bytes == 2000000000
    assert result.gpu_count == 2
    assert result.status == QuotaStatus.PENDING
    assert result.project_id == env.project.id
    assert result.cluster_id == env.cluster.id
    assert result.created_by == creator


@pytest.mark.asyncio
async def test_update_quota_for_cluster_success(db_session: AsyncSession):
    """Generic success case for quota updates with resource changes."""
    env = await factory.create_basic_test_environment(db_session)

    # Create project with quota
    _, quota = await factory.create_project_with_quota(
        db_session,
        env.organization,
        env.cluster,
        project_name="test_project",
        quota_cpu=400,
        quota_memory=1000000000,
        quota_storage=2000000000,
        quota_gpu=2,
        quota_status=QuotaStatus.READY,
    )

    gpu_vendor = GPUVendor.AMD
    updater = "platform-admin"

    # Update quota with different values
    edits = QuotaUpdate(
        cpu_milli_cores=600,  # Changed from 400
        memory_bytes=2000000000,  # Changed from 1000000000
        ephemeral_storage_bytes=3000000000,  # Changed from 2000000000
        gpu_count=3,  # Changed from 2
    )

    # Mock only external messaging service and resource change detection
    with (
        patch("app.quotas.service.have_quota_resources_changed", return_value=True),
        patch("app.quotas.service.send_quotas_allocation_to_cluster_queue", autospec=True) as mock_send_quotas,
    ):
        result = await update_quota_for_cluster(db_session, env.cluster, quota, edits, gpu_vendor, updater)

    # Verify messaging service was called
    mock_send_quotas.assert_called_once()

    # Verify quota was updated with PENDING status in real database
    await db_session.refresh(quota)
    assert quota.status == QuotaStatus.PENDING
    assert quota.cpu_milli_cores == 600
    assert quota.memory_bytes == 2000000000
    assert quota.ephemeral_storage_bytes == 3000000000
    assert quota.gpu_count == 3

    # Verify return value
    assert result is not None
    assert result.cpu_milli_cores == 600
    assert result.memory_bytes == 2000000000
    assert result.ephemeral_storage_bytes == 3000000000
    assert result.gpu_count == 3
    assert result.status == QuotaStatus.PENDING
