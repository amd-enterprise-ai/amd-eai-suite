# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from airm.messaging.schemas import AIMClusterModel, AIMClusterModelsMessage, AIMClusterModelStatus
from app.aims.discovery import reconcile_aims_from_cluster
from app.aims.models import AIM


@pytest.mark.asyncio
async def test_reconcile_aims_add_new(db_session):
    """Test adding new AIMs that don't exist in database."""
    # Create discovery message with 2 new models
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-test-model-1-1-0-0",
                image_reference="docker.io/test/aim-test-model-1:1.0.0",
                labels={
                    "com.amd.aim.model.canonicalName": "test/model1",
                    "com.amd.aim.hfToken.required": "False",
                    "com.amd.aim.model.title": "Test Model 1",
                    "org.opencontainers.image.description": "Test model 1",
                },
                status="Ready",
            ),
            AIMClusterModel(
                resource_name="aim-test-model-2-2-0-0",
                image_reference="docker.io/test/aim-test-model-2:2.0.0",
                labels={
                    "com.amd.aim.model.canonicalName": "test/model2",
                    "com.amd.aim.hfToken.required": "True",
                    "com.amd.aim.model.title": "Test Model 2",
                    "org.opencontainers.image.description": "Test model 2",
                },
                status="Pending",
            ),
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify stats
    assert stats["added"] == 2
    assert stats["updated"] == 0
    assert stats["deleted"] == 0
    assert stats["skipped"] == 0

    # Verify AIMs were added to database
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 2

    # Verify first AIM
    aim1 = next(a for a in aims if a.resource_name == "aim-test-model-1-1-0-0")
    assert aim1.image_reference == "docker.io/test/aim-test-model-1:1.0.0"
    assert aim1.labels["com.amd.aim.model.canonicalName"] == "test/model1"
    assert aim1.status == AIMClusterModelStatus.READY
    assert aim1.created_by == "system"

    # Verify second AIM
    aim2 = next(a for a in aims if a.resource_name == "aim-test-model-2-2-0-0")
    assert aim2.image_reference == "docker.io/test/aim-test-model-2:2.0.0"
    assert aim2.labels["com.amd.aim.hfToken.required"] == "True"
    assert aim2.status == AIMClusterModelStatus.PENDING


@pytest.mark.asyncio
async def test_reconcile_aims_update_existing(db_session):
    """Test updating existing AIMs when metadata or status changes."""
    # Add existing AIM to database
    existing_aim = AIM(
        resource_name="aim-test-model-1-0-0",
        image_reference="docker.io/test/aim-test-model:1.0.0",
        labels={
            "com.amd.aim.model.canonicalName": "test/model",
            "org.opencontainers.image.description": "Old description",
        },
        status="Pending",
        created_by="system",
        updated_by="system",
    )
    db_session.add(existing_aim)
    await db_session.commit()

    # Create discovery message with updated metadata and status
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-test-model-1-0-0",
                image_reference="docker.io/test/aim-test-model:1.0.0",
                labels={
                    "com.amd.aim.model.canonicalName": "test/model",
                    "com.amd.aim.hfToken.required": "True",
                    "org.opencontainers.image.description": "New description",
                },
                status="Ready",
            )
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify stats
    assert stats["added"] == 0
    assert stats["updated"] == 1
    assert stats["deleted"] == 0
    assert stats["skipped"] == 0

    # Verify AIM was updated
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 1

    updated_aim = aims[0]
    assert updated_aim.labels["org.opencontainers.image.description"] == "New description"
    assert updated_aim.labels["com.amd.aim.hfToken.required"] == "True"
    assert updated_aim.status == AIMClusterModelStatus.READY
    assert updated_aim.updated_by == "system"


@pytest.mark.asyncio
async def test_reconcile_aims_skip_unchanged(db_session):
    """Test skipping AIMs that haven't changed."""
    # Add existing AIM to database
    existing_aim = AIM(
        resource_name="aim-test-model-1-0-0",
        image_reference="docker.io/test/aim-test-model:1.0.0",
        labels={
            "com.amd.aim.model.canonicalName": "test/model",
            "org.opencontainers.image.description": "Test description",
        },
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    db_session.add(existing_aim)
    await db_session.commit()

    # Create discovery message with same data
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-test-model-1-0-0",
                image_reference="docker.io/test/aim-test-model:1.0.0",
                labels={
                    "com.amd.aim.model.canonicalName": "test/model",
                    "org.opencontainers.image.description": "Test description",
                },
                status="Ready",
            )
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify stats
    assert stats["added"] == 0
    assert stats["updated"] == 0
    assert stats["deleted"] == 0
    assert stats["skipped"] == 1

    # Verify AIM unchanged
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 1


@pytest.mark.asyncio
async def test_reconcile_aims_soft_delete_missing(db_session):
    """Test soft-deleting AIMs that are no longer in cluster (marked as Deleted)."""
    # Add 3 existing AIMs to database
    aim1 = AIM(
        resource_name="aim-model-1-1-0-0",
        image_reference="docker.io/test/aim-model-1:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model1"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    aim2 = AIM(
        resource_name="aim-model-2-2-0-0",
        image_reference="docker.io/test/aim-model-2:2.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model2"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    aim3 = AIM(
        resource_name="aim-model-3-3-0-0",
        image_reference="docker.io/test/aim-model-3:3.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model3"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    db_session.add_all([aim1, aim2, aim3])
    await db_session.commit()

    # Create discovery message with only 2 models (model-3 removed from cluster)
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-model-1-1-0-0",
                image_reference="docker.io/test/aim-model-1:1.0.0",
                labels={"com.amd.aim.model.canonicalName": "test/model1"},
                status="Ready",
            ),
            AIMClusterModel(
                resource_name="aim-model-2-2-0-0",
                image_reference="docker.io/test/aim-model-2:2.0.0",
                labels={"com.amd.aim.model.canonicalName": "test/model2"},
                status="Ready",
            ),
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify stats
    assert stats["added"] == 0
    assert stats["updated"] == 0
    assert stats["deleted"] == 1
    assert stats["skipped"] == 2

    # Verify all 3 AIMs still exist (soft delete preserves records)
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 3

    # Verify model-3 is marked as Deleted, others are Ready
    aims_by_name = {aim.resource_name: aim for aim in aims}
    assert aims_by_name["aim-model-1-1-0-0"].status == AIMClusterModelStatus.READY
    assert aims_by_name["aim-model-2-2-0-0"].status == AIMClusterModelStatus.READY
    assert aims_by_name["aim-model-3-3-0-0"].status == AIMClusterModelStatus.DELETED


@pytest.mark.asyncio
async def test_reconcile_aims_mixed_operations(db_session):
    """Test reconciliation with add, update, delete, and skip operations."""
    # Add 3 existing AIMs
    aim1 = AIM(
        resource_name="aim-existing-1-1-0-0",
        image_reference="docker.io/test/aim-existing-1:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/existing1"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    aim2 = AIM(
        resource_name="aim-existing-2-2-0-0",
        image_reference="docker.io/test/aim-existing-2:2.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/existing2", "old": "data"},
        status="Pending",
        created_by="system",
        updated_by="system",
    )
    aim3 = AIM(
        resource_name="aim-to-delete-3-0-0",
        image_reference="docker.io/test/aim-to-delete:3.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/deleted"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    db_session.add_all([aim1, aim2, aim3])
    await db_session.commit()

    # Create discovery message with:
    # - aim-existing-1: unchanged (skip)
    # - aim-existing-2: metadata changed (update)
    # - aim-new: doesn't exist (add)
    # - aim-to-delete: not in message (delete)
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-existing-1-1-0-0",
                image_reference="docker.io/test/aim-existing-1:1.0.0",
                labels={"com.amd.aim.model.canonicalName": "test/existing1"},
                status="Ready",
            ),
            AIMClusterModel(
                resource_name="aim-existing-2-2-0-0",
                image_reference="docker.io/test/aim-existing-2:2.0.0",
                labels={"com.amd.aim.model.canonicalName": "test/existing2", "new": "data"},
                status="Ready",
            ),
            AIMClusterModel(
                resource_name="aim-new-4-0-0",
                image_reference="docker.io/test/aim-new:4.0.0",
                labels={"com.amd.aim.model.canonicalName": "test/new"},
                status="Pending",
            ),
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify stats
    assert stats["added"] == 1  # aim-new
    assert stats["updated"] == 1  # aim-existing-2
    assert stats["deleted"] == 1  # aim-to-delete
    assert stats["skipped"] == 1  # aim-existing-1

    # Verify final database state (soft delete preserves all records)
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 4  # All 4 AIMs exist (3 original + 1 new)

    aims_by_name = {aim.resource_name: aim for aim in aims}
    assert "aim-existing-1-1-0-0" in aims_by_name
    assert "aim-existing-2-2-0-0" in aims_by_name
    assert "aim-new-4-0-0" in aims_by_name
    assert "aim-to-delete-3-0-0" in aims_by_name

    # Verify statuses
    assert aims_by_name["aim-existing-1-1-0-0"].status == AIMClusterModelStatus.READY  # skipped
    assert aims_by_name["aim-existing-2-2-0-0"].status == AIMClusterModelStatus.READY  # updated
    assert aims_by_name["aim-new-4-0-0"].status == AIMClusterModelStatus.PENDING  # added
    assert aims_by_name["aim-to-delete-3-0-0"].status == AIMClusterModelStatus.DELETED  # soft-deleted

    # Verify updated metadata
    updated_aim = aims_by_name["aim-existing-2-2-0-0"]
    assert "new" in updated_aim.labels
    assert "old" not in updated_aim.labels


@pytest.mark.asyncio
async def test_reconcile_aims_empty_cluster(db_session):
    """Test reconciliation when cluster has no AIMs (delete all)."""
    # Add existing AIMs
    aim1 = AIM(
        resource_name="aim-model-1-1-0-0",
        image_reference="docker.io/test/aim-model-1:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model1"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    aim2 = AIM(
        resource_name="aim-model-2-2-0-0",
        image_reference="docker.io/test/aim-model-2:2.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model2"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    db_session.add_all([aim1, aim2])
    await db_session.commit()

    # Create discovery message with no models
    message = AIMClusterModelsMessage(message_type="aim_cluster_models", models=[], synced_at=datetime.now(UTC))

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify stats
    assert stats["added"] == 0
    assert stats["updated"] == 0
    assert stats["deleted"] == 2
    assert stats["skipped"] == 0

    # Verify all AIMs still exist but are marked as Deleted (soft delete)
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 2
    assert all(aim.status == AIMClusterModelStatus.DELETED for aim in aims)


@pytest.mark.asyncio
async def test_reconcile_aims_status_change(db_session):
    """Test that status changes trigger an update."""
    # Add existing AIM with Pending status
    existing_aim = AIM(
        resource_name="aim-test-model-1-0-0",
        image_reference="docker.io/test/aim-test-model:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
        status="Pending",
        created_by="system",
        updated_by="system",
    )
    db_session.add(existing_aim)
    await db_session.commit()

    # Create discovery message with status changed to Ready
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-test-model-1-0-0",
                image_reference="docker.io/test/aim-test-model:1.0.0",
                labels={"com.amd.aim.model.canonicalName": "test/model"},
                status="Ready",
            )
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify status change was detected
    assert stats["added"] == 0
    assert stats["updated"] == 1
    assert stats["deleted"] == 0
    assert stats["skipped"] == 0

    # Verify status was updated
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 1
    assert aims[0].status == AIMClusterModelStatus.READY


@pytest.mark.asyncio
async def test_reconcile_aims_already_deleted_skipped(db_session):
    """Test that already-deleted AIMs are skipped on subsequent reconciliations."""
    # Add an AIM that's already marked as Deleted
    deleted_aim = AIM(
        resource_name="aim-old-model-1-0-0",
        image_reference="docker.io/test/aim-old-model:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/old-model"},
        status=AIMClusterModelStatus.DELETED,
        created_by="system",
        updated_by="system",
    )
    db_session.add(deleted_aim)
    await db_session.commit()

    # Refresh to get the updated_at value from the database
    await db_session.refresh(deleted_aim)
    original_updated_at = deleted_aim.updated_at

    # Create discovery message with no models (AIM still missing)
    message = AIMClusterModelsMessage(message_type="aim_cluster_models", models=[], synced_at=datetime.now(UTC))

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify the already-deleted AIM was skipped (not counted as deleted again)
    assert stats["added"] == 0
    assert stats["updated"] == 0
    assert stats["deleted"] == 0
    assert stats["skipped"] == 1

    # Verify AIM still exists and updated_at wasn't changed
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 1
    assert aims[0].status == AIMClusterModelStatus.DELETED
    assert aims[0].updated_at == original_updated_at


@pytest.mark.asyncio
async def test_reconcile_aims_deleted_aim_returns_to_cluster(db_session):
    """Test that a previously deleted AIM is restored when it returns to the cluster."""
    # Add an AIM that was previously marked as Deleted
    deleted_aim = AIM(
        resource_name="aim-returning-model-1-0-0",
        image_reference="docker.io/test/aim-returning-model:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/returning-model"},
        status=AIMClusterModelStatus.DELETED,
        created_by="system",
        updated_by="system",
    )
    db_session.add(deleted_aim)
    await db_session.commit()

    # Create discovery message with the AIM back in the cluster
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-returning-model-1-0-0",
                image_reference="docker.io/test/aim-returning-model:1.0.0",
                labels={"com.amd.aim.model.canonicalName": "test/returning-model"},
                status="Ready",
            )
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Verify the AIM was updated (status changed from Deleted to Ready)
    assert stats["added"] == 0
    assert stats["updated"] == 1  # Status changed from Deleted -> Ready
    assert stats["deleted"] == 0
    assert stats["skipped"] == 0

    # Verify AIM is now Ready
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 1
    assert aims[0].status == AIMClusterModelStatus.READY


@pytest.mark.asyncio
async def test_reconcile_aims_resource_name_can_change(db_session):
    """Test that resource_name changes are updated (different clusters can name differently)."""
    # Add existing AIM
    existing_aim = AIM(
        resource_name="aim-test-model-1-0-0",
        image_reference="docker.io/test/aim-test-model:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    db_session.add(existing_aim)
    await db_session.commit()

    # Create discovery message with changed resource_name (can happen when moving to different cluster)
    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-test-model-new-name",  # Different resource_name!
                image_reference="docker.io/test/aim-test-model:1.0.0",  # Same image_reference
                labels={"com.amd.aim.model.canonicalName": "test/model"},
                status="Ready",
            )
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Should be updated since resource_name changed
    assert stats["added"] == 0
    assert stats["updated"] == 1
    assert stats["deleted"] == 0
    assert stats["skipped"] == 0

    # Verify resource_name was updated
    result = await db_session.execute(select(AIM))
    aim = result.scalars().first()
    assert aim.resource_name == "aim-test-model-new-name"  # Updated
    assert aim.image_reference == "docker.io/test/aim-test-model:1.0.0"  # Unchanged


@pytest.mark.asyncio
async def test_reconcile_aims_same_image_different_resource_names(db_session):
    """Test that discovery prevents duplicate AIMs with same image_reference but different resource_names.

    This is an edge case where two AIMClusterModels with different resource_names point to the same
    image_reference. Discovery should update the existing AIM's resource_name rather than creating
    a duplicate, since image_reference is the primary matching key.
    """
    existing_aim = AIM(
        resource_name="aim-old-name-1-0-0",
        image_reference="docker.io/test/same-image:1.0.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
        status="Ready",
        created_by="system",
        updated_by="system",
    )
    db_session.add(existing_aim)
    await db_session.commit()

    message = AIMClusterModelsMessage(
        message_type="aim_cluster_models",
        models=[
            AIMClusterModel(
                resource_name="aim-new-name-1-0-0",  # Different resource_name
                image_reference="docker.io/test/same-image:1.0.0",  # SAME image_reference
                labels={"com.amd.aim.model.canonicalName": "test/model"},
                status="Ready",
            )
        ],
        synced_at=datetime.now(UTC),
    )

    # Reconcile
    stats = await reconcile_aims_from_cluster(db_session, message)

    # Should update existing AIM, not create duplicate
    assert stats["added"] == 0
    assert stats["updated"] == 1
    assert stats["deleted"] == 0
    assert stats["skipped"] == 0

    # Verify only one AIM exists with updated resource_name
    result = await db_session.execute(select(AIM))
    aims = result.scalars().all()
    assert len(aims) == 1  # No duplicate created!

    aim = aims[0]
    assert aim.resource_name == "aim-new-name-1-0-0"  # Updated to new resource_name
    assert aim.image_reference == "docker.io/test/same-image:1.0.0"  # Same image_reference
    assert aim.status == AIMClusterModelStatus.READY
