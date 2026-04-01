# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ConflictException, DeletionConflictException, NotFoundException
from app.models.models import OnboardingStatus
from app.models.repository import (
    can_delete_model,
    delete_model_by_id,
    insert_model,
    select_model,
    select_models,
    update_onboarding_statuses,
    workload_status_to_model_status,
)
from app.workloads.enums import WorkloadStatus
from tests import factory


@pytest.mark.asyncio
async def test_insert_model(db_session: AsyncSession, test_namespace: str) -> None:
    """Test inserting a model."""
    name = "Test Model"
    canonical_name = "test/model"
    model_weights_path = "test-model.bin"
    submitter = "test@example.com"

    model = await insert_model(
        db_session,
        name=name,
        submitter=submitter,
        namespace=test_namespace,
        onboarding_status=OnboardingStatus.ready,
        canonical_name=canonical_name,
        model_weights_path=model_weights_path,
    )

    assert model.name == name
    assert model.canonical_name == canonical_name
    assert model.model_weights_path == model_weights_path
    assert model.onboarding_status == OnboardingStatus.ready
    assert model.namespace == test_namespace
    assert model.created_by == submitter
    assert model.updated_by == submitter


@pytest.mark.asyncio
async def test_select_model(db_session: AsyncSession, test_namespace: str) -> None:
    """Test selecting a model by ID."""
    # Create a model
    model = await factory.create_inference_model(db_session, namespace=test_namespace)

    # Select model by ID
    found_model = await select_model(db_session, model.id, test_namespace)

    assert found_model is not None
    assert found_model.id == model.id
    assert found_model.name == model.name
    assert found_model.namespace == test_namespace

    # Non-existent model returns None
    non_existent_model = await select_model(db_session, uuid4(), test_namespace)
    assert non_existent_model is None

    # Wrong namespace returns None
    wrong_namespace_model = await select_model(db_session, model.id, "other-namespace")
    assert wrong_namespace_model is None


@pytest.mark.asyncio
async def test_select_models(db_session: AsyncSession, test_namespace: str) -> None:
    """Test listing models in a namespace."""
    namespace1 = test_namespace
    namespace2 = "other-namespace"

    # Create models in both namespaces
    await factory.create_inference_model(db_session, name="Model 1", namespace=namespace1)
    await factory.create_inference_model(db_session, name="Model 2", namespace=namespace1)
    await factory.create_inference_model(db_session, name="Model 3", namespace=namespace2)

    # List models for namespace1
    namespace1_models = await select_models(db_session, namespace=namespace1)
    assert len(namespace1_models) == 2

    model_names = {model.name for model in namespace1_models}
    assert "Model 1" in model_names
    assert "Model 2" in model_names

    # List models for namespace2
    namespace2_models = await select_models(db_session, namespace=namespace2)
    assert len(namespace2_models) == 1
    assert namespace2_models[0].name == "Model 3"


@pytest.mark.asyncio
async def test_delete_model_by_id_not_found(db_session: AsyncSession, test_namespace: str) -> None:
    """Test deleting a model by ID that does not exist."""
    non_existent_id = UUID("12345678-1234-5678-1234-567812345678")
    with pytest.raises(NotFoundException):
        await delete_model_by_id(db_session, non_existent_id, test_namespace)


@pytest.mark.asyncio
async def test_insert_model_with_different_statuses(db_session: AsyncSession, test_namespace: str) -> None:
    """Test inserting models with different onboarding statuses."""
    submitter = "test@example.com"

    # Test different statuses
    statuses = [OnboardingStatus.pending, OnboardingStatus.ready, OnboardingStatus.failed]

    for i, status in enumerate(statuses):
        model = await insert_model(
            db_session,
            name=f"Test Model {i}",
            submitter=submitter,
            namespace=test_namespace,
            onboarding_status=status,
            canonical_name=f"test/model-{i}",
            model_weights_path=f"test-model-{i}.bin",
        )

        assert model.onboarding_status == status

    # Verify all models exist in namespace
    namespace_models = await select_models(db_session, namespace=test_namespace)
    assert len(namespace_models) == 3

    model_statuses = {model.onboarding_status for model in namespace_models}
    assert OnboardingStatus.pending in model_statuses
    assert OnboardingStatus.ready in model_statuses
    assert OnboardingStatus.failed in model_statuses


@pytest.mark.asyncio
async def test_update_onboarding_statuses(db_session: AsyncSession, test_namespace: str) -> None:
    """Test updating model onboarding statuses based on workload statuses."""
    model1 = await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Model 1", onboarding_status=OnboardingStatus.pending
    )
    model2 = await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Model 2", onboarding_status=OnboardingStatus.pending
    )

    # Create workloads linked to models
    await factory.create_workload(
        db_session, namespace=test_namespace, status=WorkloadStatus.COMPLETE, model_id=model1.id
    )
    await factory.create_workload(
        db_session, namespace=test_namespace, status=WorkloadStatus.FAILED, model_id=model2.id
    )

    await update_onboarding_statuses(db_session, test_namespace)

    await db_session.refresh(model1)
    await db_session.refresh(model2)

    assert model1.onboarding_status == OnboardingStatus.ready
    assert model2.onboarding_status == OnboardingStatus.failed


@pytest.mark.asyncio
async def test_update_onboarding_statuses_no_workloads_marks_failed(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Test that pending models with no associated workloads are marked as failed."""
    model1 = await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Model 1", onboarding_status=OnboardingStatus.pending
    )
    model2 = await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Model 2", onboarding_status=OnboardingStatus.pending
    )

    await update_onboarding_statuses(db_session, test_namespace)

    await db_session.refresh(model1)
    await db_session.refresh(model2)

    assert model1.onboarding_status == OnboardingStatus.failed
    assert model2.onboarding_status == OnboardingStatus.failed


@pytest.mark.asyncio
async def test_insert_model_without_weights_path(db_session: AsyncSession, test_namespace: str) -> None:
    """Test inserting a model without model weights path."""
    model = await insert_model(
        db_session,
        name="Model Without Weights",
        submitter="test@example.com",
        namespace=test_namespace,
        onboarding_status=OnboardingStatus.pending,
        canonical_name="test/no-weights-model",
        model_weights_path=None,
    )

    assert model.name == "Model Without Weights"
    assert model.model_weights_path is None
    assert model.onboarding_status == OnboardingStatus.pending


@pytest.mark.asyncio
async def test_select_models_filtering(db_session: AsyncSession, test_namespace: str) -> None:
    """Test filtering models by various criteria."""
    submitter = "test@example.com"

    # Create models with different onboarding statuses
    base_model = await insert_model(
        db_session,
        name="Ready Model",
        namespace=test_namespace,
        submitter=submitter,
        onboarding_status=OnboardingStatus.ready,
        model_weights_path="s3://bucket/ready",
        canonical_name="test/base-model",
    )
    await insert_model(
        db_session,
        name="Pending Model",
        submitter=submitter,
        namespace=test_namespace,
        onboarding_status=OnboardingStatus.pending,
        canonical_name="test/pending-model",
        model_weights_path="test-pending-weights",
    )

    # List all models
    all_models = await select_models(db_session, namespace=test_namespace)
    assert len(all_models) == 2

    # List models with onboarding_status=ready
    ready_models = await select_models(db_session, namespace=test_namespace, onboarding_status=OnboardingStatus.ready)
    assert len(ready_models) == 1
    assert all(m.onboarding_status == OnboardingStatus.ready for m in ready_models)

    # List models by name
    named_models = await select_models(db_session, namespace=test_namespace, name="Ready Model")
    assert len(named_models) == 1
    assert named_models[0].name == "Ready Model"

    # List models by selected IDs
    selected_ids = [base_model.id]
    selected_models = await select_models(db_session, namespace=test_namespace, selected_model_ids=selected_ids)
    assert len(selected_models) == 1
    returned_ids = {m.id for m in selected_models}
    assert set(selected_ids) == returned_ids


@pytest.mark.asyncio
async def test_model_name_unique_constraint(db_session: AsyncSession, test_namespace: str) -> None:
    """Test that model names are unique within a namespace."""
    # Create first model
    await insert_model(
        db_session,
        name="Unique Model",
        submitter="test@example.com",
        namespace=test_namespace,
        onboarding_status=OnboardingStatus.ready,
        canonical_name="test/unique-model",
        model_weights_path="test-unique.bin",
    )

    # Try to create model with same name in same namespace - should fail
    with pytest.raises(ConflictException, match="already exists in this namespace"):
        await insert_model(
            db_session,
            name="Unique Model",  # Same name
            submitter="test@example.com",
            namespace=test_namespace,  # Same namespace
            onboarding_status=OnboardingStatus.ready,
            canonical_name="test/another-model",  # Different canonical name
            model_weights_path="test-another.bin",
        )


@pytest.mark.asyncio
async def test_delete_model_success(db_session: AsyncSession, test_namespace: str) -> None:
    """Test successfully deleting a model."""
    # Create a model
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Model to Delete",
        onboarding_status=OnboardingStatus.ready,
    )
    model_id = model.id

    # Delete the model
    await delete_model_by_id(db_session, model_id, test_namespace)

    # Verify model is deleted
    deleted_model = await select_model(db_session, model_id, test_namespace)
    assert deleted_model is None


@pytest.mark.asyncio
async def test_workload_status_to_model_status_complete(db_session: AsyncSession) -> None:
    """Test workload status COMPLETE maps to model status ready."""

    result = workload_status_to_model_status(WorkloadStatus.COMPLETE)
    assert result == OnboardingStatus.ready


@pytest.mark.asyncio
async def test_workload_status_to_model_status_failed(db_session: AsyncSession) -> None:
    """Test workload status FAILED maps to model status failed."""

    result = workload_status_to_model_status(WorkloadStatus.FAILED)
    assert result == OnboardingStatus.failed


@pytest.mark.asyncio
async def test_workload_status_to_model_status_pending(db_session: AsyncSession) -> None:
    """Test workload status PENDING maps to model status pending."""

    result = workload_status_to_model_status(WorkloadStatus.PENDING)
    assert result == OnboardingStatus.pending


@pytest.mark.asyncio
async def test_workload_status_to_model_status_running(db_session: AsyncSession) -> None:
    """Test workload status RUNNING maps to model status pending."""

    result = workload_status_to_model_status(WorkloadStatus.RUNNING)
    assert result == OnboardingStatus.pending


@pytest.mark.asyncio
async def test_can_delete_model_not_found(db_session: AsyncSession) -> None:
    """Test can_delete_model raises NotFoundException when model is None."""

    non_existent_id = uuid4()

    with pytest.raises(NotFoundException, match="not found in this namespace"):
        await can_delete_model(db_session, None, non_existent_id)


@pytest.mark.asyncio
async def test_can_delete_model_with_running_workload_ready_status(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Test can_delete_model raises DeletionConflictException for ready model with running workload."""

    # Create a ready model
    model = await factory.create_inference_model(
        db_session, namespace=test_namespace, onboarding_status=OnboardingStatus.ready
    )

    # Create a running workload associated with the model (linking via model_id)
    workload = await factory.create_workload(
        db_session,
        namespace=test_namespace,
        status=WorkloadStatus.RUNNING,
    )
    # Link workload to model
    workload.model_id = model.id
    await db_session.flush()

    # This should raise DeletionConflictException since model is ready with running workload
    with pytest.raises(DeletionConflictException, match="currently being used by a workload"):
        await can_delete_model(db_session, model, model.id)


@pytest.mark.asyncio
async def test_can_delete_model_with_pending_workload_pending_status(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Test can_delete_model raises DeletionConflictException for pending model with pending workload."""

    # Create a pending model
    model = await factory.create_inference_model(
        db_session, namespace=test_namespace, onboarding_status=OnboardingStatus.pending
    )

    # Create a pending workload associated with the model (linking via model_id)
    workload = await factory.create_workload(
        db_session,
        namespace=test_namespace,
        status=WorkloadStatus.PENDING,
    )
    # Link workload to model
    workload.model_id = model.id
    await db_session.flush()

    # This should raise DeletionConflictException since model is pending with pending workload
    with pytest.raises(DeletionConflictException, match="currently being onboarded"):
        await can_delete_model(db_session, model, model.id)


@pytest.mark.asyncio
async def test_can_delete_model_with_failed_status(db_session: AsyncSession, test_namespace: str) -> None:
    """Test can_delete_model succeeds for failed model even with workloads."""

    # Create a failed model
    model = await factory.create_inference_model(
        db_session, namespace=test_namespace, onboarding_status=OnboardingStatus.failed
    )

    # Create a workload associated with the model
    await factory.create_workload(
        db_session,
        namespace=test_namespace,
        status=WorkloadStatus.RUNNING,
    )

    # This should not raise an exception since model has failed status
    await can_delete_model(db_session, model, model.id)


@pytest.mark.asyncio
async def test_can_delete_model_with_completed_workload(db_session: AsyncSession, test_namespace: str) -> None:
    """Test can_delete_model succeeds for ready model with completed workload."""

    # Create a ready model
    model = await factory.create_inference_model(
        db_session, namespace=test_namespace, onboarding_status=OnboardingStatus.ready
    )

    # Create a completed workload associated with the model
    await factory.create_workload(
        db_session,
        namespace=test_namespace,
        status=WorkloadStatus.COMPLETE,
    )

    # This should not raise an exception since workload is complete
    await can_delete_model(db_session, model, model.id)


@pytest.mark.asyncio
async def test_update_onboarding_statuses_with_completed_workload(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Test update_onboarding_statuses updates model to ready when workload completes."""
    model = await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Model 1", onboarding_status=OnboardingStatus.pending
    )

    await factory.create_workload(
        db_session,
        namespace=test_namespace,
        status=WorkloadStatus.COMPLETE,
        model_id=model.id,
    )

    await update_onboarding_statuses(db_session, test_namespace)

    await db_session.refresh(model)
    assert model.onboarding_status == OnboardingStatus.ready


@pytest.mark.asyncio
async def test_update_onboarding_statuses_with_failed_workload(db_session: AsyncSession, test_namespace: str) -> None:
    """Test update_onboarding_statuses updates model to failed when workload fails."""
    model = await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Model 1", onboarding_status=OnboardingStatus.pending
    )

    await factory.create_workload(
        db_session,
        namespace=test_namespace,
        status=WorkloadStatus.FAILED,
        model_id=model.id,
    )

    await update_onboarding_statuses(db_session, test_namespace)

    await db_session.refresh(model)
    assert model.onboarding_status == OnboardingStatus.failed


@pytest.mark.asyncio
async def test_update_onboarding_statuses_no_pending_models(db_session: AsyncSession, test_namespace: str) -> None:
    """Test update_onboarding_statuses does nothing when no pending models exist."""
    # Create a ready model
    await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Ready Model", onboarding_status=OnboardingStatus.ready
    )

    # This should complete without errors
    await update_onboarding_statuses(db_session, test_namespace)
