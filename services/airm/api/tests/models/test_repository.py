# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.managed_workloads.enums import WorkloadStatus
from app.models.models import OnboardingStatus
from app.models.repository import (
    delete_model_by_id,
    delete_models,
    insert_model,
    select_model,
    select_models,
    update_model,
    update_onboarding_statuses,
)
from app.models.schemas import ModelEdit
from app.utilities.exceptions import DeletionConflictException, NotFoundException
from tests import factory


@pytest.mark.asyncio
async def test_insert_model(db_session: AsyncSession):
    """Test inserting a model."""
    env = await factory.create_basic_test_environment(db_session)

    name = "Test Model"
    canonical_name = "test/model"
    model_weights_path = "test-model.bin"
    creator = "test@example.com"

    model = await insert_model(
        db_session,
        name=name,
        creator=creator,
        project_id=env.project.id,
        onboarding_status=OnboardingStatus.ready,
        canonical_name=canonical_name,
        model_weights_path=model_weights_path,
    )

    assert model.name == name
    assert model.canonical_name == canonical_name
    assert model.model_weights_path == model_weights_path
    assert model.onboarding_status == OnboardingStatus.ready
    assert model.project_id == env.project.id
    assert model.created_by == creator
    assert model.updated_by == creator


@pytest.mark.asyncio
async def test_select_model(db_session: AsyncSession):
    """Test selecting a model by ID."""
    env = await factory.create_full_test_environment(db_session, with_model=True)

    # Select model by ID
    found_model = await select_model(db_session, env.model.id, env.project.id)

    assert found_model is not None
    assert found_model.id == env.model.id
    assert found_model.name == env.model.name
    assert found_model.project_id == env.project.id

    non_existent_model = await select_model(db_session, uuid4(), env.project.id)
    assert non_existent_model is None

    wrong_project_model = await select_model(db_session, env.model.id, uuid4())
    assert wrong_project_model is None


@pytest.mark.asyncio
async def test_select_models(db_session: AsyncSession):
    """Test listing models in project."""
    # Create multiple organizations
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create models in both organizations
    model1 = await factory.create_inference_model(db_session, project1, name="Org1 Model 1")
    model2 = await factory.create_inference_model(db_session, project1, name="Org1 Model 2")
    model3 = await factory.create_inference_model(db_session, project2, name="Org2 Model")

    # List models for project1
    project1_models = await select_models(db_session, project_id=project1.id)
    assert len(project1_models) == 2

    model_names = {model.name for model in project1_models}
    assert "Org1 Model 1" in model_names
    assert "Org1 Model 2" in model_names
    assert "Org2 Model" not in model_names

    # List models for project2
    project2_models = await select_models(db_session, project_id=project2.id)
    assert len(project2_models) == 1
    assert project2_models[0].name == "Org2 Model"


@pytest.mark.asyncio
async def test_update_model(db_session: AsyncSession):
    """Test updating model details."""
    env = await factory.create_full_test_environment(db_session, with_model=True)

    original_name = env.model.name

    model_edit = ModelEdit(name="Updated Model Name")

    updated_model = await update_model(db_session, env.model, model_edit, "updater@example.com")

    assert updated_model.id == env.model.id
    assert updated_model.name == "Updated Model Name"
    assert updated_model.name != original_name
    assert updated_model.updated_by == "updater@example.com"


@pytest.mark.asyncio
async def test_delete_model_by_id_not_found(db_session: AsyncSession):
    """Test deleting a model by ID that does not exist."""
    env = await factory.create_basic_test_environment(db_session)

    non_existent_id = UUID("12345678-1234-5678-1234-567812345678")
    with pytest.raises(NotFoundException):
        await delete_model_by_id(db_session, non_existent_id, env.project.id)


@pytest.mark.asyncio
async def test_insert_model_with_different_statuses(db_session: AsyncSession):
    """Test inserting base models with different onboarding statuses."""
    env = await factory.create_basic_test_environment(db_session)

    creator = "test@example.com"

    # Test different statuses
    statuses = [OnboardingStatus.pending, OnboardingStatus.ready, OnboardingStatus.failed]

    for i, status in enumerate(statuses):
        model = await insert_model(
            db_session,
            name=f"Test Model {i}",
            creator=creator,
            project_id=env.project.id,
            onboarding_status=status,
            canonical_name=f"test/model-{i}",
            model_weights_path=f"test-model-{i}.bin",
        )

        assert model.onboarding_status == status

    # Verify all models exist in project
    project_models = await select_models(db_session, project_id=env.project.id)
    assert len(project_models) == 3

    model_statuses = {model.onboarding_status for model in project_models}
    assert OnboardingStatus.pending in model_statuses
    assert OnboardingStatus.ready in model_statuses
    assert OnboardingStatus.failed in model_statuses


@pytest.mark.asyncio
async def test_model_project_isolation(db_session: AsyncSession):
    """Test that models are properly isolated by project."""
    # Create multiple organizations
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    # Create model in project1
    model1 = await factory.create_inference_model(db_session, project1, name="Project1 Model")

    # Try to get model from project2 should not find it
    project2_models = await select_models(db_session, project_id=project2.id)
    assert len(project2_models) == 0

    # Create model in project2
    model2 = await factory.create_inference_model(db_session, project2, name="Project2 Model")

    # Verify isolation
    project1_models = await select_models(db_session, project_id=project1.id)
    project2_models = await select_models(db_session, project_id=project2.id)

    assert len(project1_models) == 1
    assert len(project2_models) == 1
    assert project1_models[0].name == "Project1 Model"
    assert project2_models[0].name == "Project2 Model"


@pytest.mark.asyncio
async def test_update_onboarding_statuses():
    # Create test data
    project_id = uuid4()

    # Create mock models with pending status
    model1 = MagicMock()
    model1.id = uuid4()
    model1.onboarding_status = OnboardingStatus.pending

    model2 = MagicMock()
    model2.id = uuid4()
    model2.onboarding_status = OnboardingStatus.pending

    pending_models = [model1, model2]

    # Create mock workloads with different statuses
    workload1 = MagicMock()
    workload1.id = uuid4()
    workload1.model_id = model1.id
    workload1.status = WorkloadStatus.COMPLETE

    workload2 = MagicMock()
    workload2.id = uuid4()
    workload2.model_id = model2.id
    workload2.status = WorkloadStatus.FAILED

    workloads = [workload1, workload2]

    # Create mock results
    models_result = MagicMock()
    models_result.scalars.return_value.all.return_value = pending_models

    workloads_result = MagicMock()
    workloads_result.unique.return_value.scalars.return_value.all.return_value = workloads

    # Create a mock session
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = [models_result, workloads_result]
    mock_session.flush = AsyncMock(spec=AsyncSession)

    # Call the function
    await update_onboarding_statuses(mock_session, project_id)

    # Verify model statuses were updated
    assert model1.onboarding_status == OnboardingStatus.ready  # succeeded workload -> ready model
    assert model2.onboarding_status == OnboardingStatus.failed  # failed workload -> failed model

    # Verify flush was called
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_insert_model_without_weights_path(db_session: AsyncSession):
    """Test inserting base model without model weights path."""
    env = await factory.create_basic_test_environment(db_session)

    # Insert base model without weights path
    model = await insert_model(
        db_session,
        name="Model Without Weights",
        creator="test@example.com",
        project_id=env.project.id,
        onboarding_status=OnboardingStatus.pending,
        canonical_name="test/no-weights-model",
        model_weights_path="test-weights-path",
    )
    # Verify model was created with placeholder weights path
    assert model.name == "Model Without Weights"
    assert model.model_weights_path == "test-weights-path"
    assert model.onboarding_status == OnboardingStatus.pending


async def test_select_models_filtering(db_session):
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id
    creator = env.creator
    # Create models with different onboarding statuses
    base_model = await insert_model(
        db_session,
        name="Ready Model",
        project_id=project_id,
        creator=creator,
        onboarding_status=OnboardingStatus.ready,
        model_weights_path="s3://bucket/ready",
        canonical_name="test/base-model",
    )
    pending_model = await insert_model(
        db_session,
        name="Model Without Weights",
        creator="test@example.com",
        project_id=env.project.id,
        onboarding_status=OnboardingStatus.pending,
        canonical_name="test/no-weights-model",
        model_weights_path="test-pending-weights",
    )

    # List all models
    all_models = await select_models(db_session, project_id=project_id)
    assert len(all_models) == 2

    # List models with onboarding_status=ready
    ready_models = await select_models(db_session, project_id=project_id, onboarding_status=OnboardingStatus.ready)
    assert len(ready_models) == 1
    assert all(m.onboarding_status == OnboardingStatus.ready for m in ready_models)

    # List models with onboarding_status=ready
    ready_models = await select_models(
        db_session,
        project_id=project_id,
        onboarding_status=OnboardingStatus.ready,
    )
    assert len(ready_models) == 1
    assert all(m.onboarding_status == OnboardingStatus.ready for m in ready_models)

    # List models by name
    finetuned_models = await select_models(db_session, project_id=project_id, name="Ready Model")
    assert len(finetuned_models) == 1
    assert finetuned_models[0].name == "Ready Model"

    # List models by selected IDs
    selected_ids = [base_model.id]
    selected_models = await select_models(db_session, project_id=project_id, selected_model_ids=selected_ids)
    assert len(selected_models) == 1
    returned_ids = {m.id for m in selected_models}
    assert set(selected_ids) == returned_ids


@pytest.mark.asyncio
async def test_model_name_unique_constraint(db_session: AsyncSession):
    """Test that model names are unique within project and cluster scope."""
    env = await factory.create_basic_test_environment(db_session)

    # Create first model
    await insert_model(
        db_session,
        name="Unique Model",
        creator=env.creator,
        project_id=env.project.id,
        onboarding_status=OnboardingStatus.ready,
        canonical_name="test/unique-model",
        model_weights_path="test-unique.bin",
    )

    # Try to create model with same name in same project - should fail
    from app.utilities.exceptions import ConflictException

    with pytest.raises(ConflictException, match="already exists in this project"):
        await insert_model(
            db_session,
            name="Unique Model",  # Same name
            creator=env.creator,
            project_id=env.project.id,  # Same project
            onboarding_status=OnboardingStatus.ready,
            canonical_name="test/another-model",  # Different canonical name
            model_weights_path="test-another.bin",
        )


# === SINGLE MODEL DELETION PARAMETRIZED TEST ===
@pytest.mark.parametrize(
    "test_name,model_type,model_status,workload_status,multiple_workloads,should_succeed,expected_error_fragment",
    [
        # === BASIC SCENARIOS ===
        ("Basic deletion - ready model", "base", OnboardingStatus.ready, None, False, True, None),
        ("Basic deletion - failed model", "base", OnboardingStatus.failed, None, False, True, None),
        ("Basic deletion - pending model", "base", OnboardingStatus.pending, None, False, True, None),
        # === WORKLOAD SCENARIOS - READY MODEL ===
        ("Ready model + COMPLETE workload", "base", OnboardingStatus.ready, WorkloadStatus.COMPLETE, False, True, None),
        ("Ready model + FAILED workload", "base", OnboardingStatus.ready, WorkloadStatus.FAILED, False, True, None),
        ("Ready model + DELETED workload", "base", OnboardingStatus.ready, WorkloadStatus.DELETED, False, True, None),
        (
            "Ready model + TERMINATED workload",
            "base",
            OnboardingStatus.ready,
            WorkloadStatus.TERMINATED,
            False,
            True,
            None,
        ),
        (
            "Ready model + RUNNING workload",
            "base",
            OnboardingStatus.ready,
            WorkloadStatus.RUNNING,
            False,
            False,
            "currently being used by a workload",
        ),
        (
            "Ready model + PENDING workload",
            "base",
            OnboardingStatus.ready,
            WorkloadStatus.PENDING,
            False,
            False,
            "currently being used by a workload",
        ),
        (
            "Ready model + DELETING workload",
            "base",
            OnboardingStatus.ready,
            WorkloadStatus.DELETING,
            False,
            False,
            "currently being used by a workload",
        ),
        (
            "Ready model + DELETE_FAILED workload",
            "base",
            OnboardingStatus.ready,
            WorkloadStatus.DELETE_FAILED,
            False,
            False,
            "currently being used by a workload",
        ),
        (
            "Ready model + UNKNOWN workload",
            "base",
            OnboardingStatus.ready,
            WorkloadStatus.UNKNOWN,
            False,
            False,
            "currently being used by a workload",
        ),
        # === WORKLOAD SCENARIOS - FAILED MODEL (always succeeds) ===
        ("Failed model + RUNNING workload", "base", OnboardingStatus.failed, WorkloadStatus.RUNNING, False, True, None),
        ("Failed model + FAILED workload", "base", OnboardingStatus.failed, WorkloadStatus.FAILED, False, True, None),
        ("Failed model + PENDING workload", "base", OnboardingStatus.failed, WorkloadStatus.PENDING, False, True, None),
        # === MULTIPLE WORKLOADS ===
        (
            "Ready model + multiple workloads (one active)",
            "base",
            OnboardingStatus.ready,
            WorkloadStatus.RUNNING,
            True,
            False,
            "currently being used by a workload",
        ),
    ],
)
@pytest.mark.asyncio
async def test_single_model_deletion_scenarios(
    db_session: AsyncSession,
    test_name: str,
    model_type: str,
    model_status: OnboardingStatus,
    workload_status: WorkloadStatus | None,
    multiple_workloads: bool,
    should_succeed: bool,
    expected_error_fragment: str | None,
):
    """
    Parametrized test covering all single model deletion scenarios.
    This systematically tests every combination of model states, workload statuses,
    and relationships defined in the business rules matrix.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Create base model first (always needed)
    test_model = await factory.create_inference_model(
        db_session,
        env.project,
        name=f"Base Model for {test_name}",
        onboarding_status=model_status if model_type == "base" else OnboardingStatus.ready,
    )

    # Create workload if specified
    if workload_status:
        await factory.create_chart_workload(db_session, env.project, model_id=test_model.id, status=workload_status)

    # Create multiple workloads if specified
    if multiple_workloads:
        await factory.create_chart_workload(
            db_session, env.project, model_id=test_model.id, status=WorkloadStatus.TERMINATED
        )
        await factory.create_chart_workload(
            db_session, env.project, model_id=test_model.id, status=WorkloadStatus.FAILED
        )

    # Test deletion
    if should_succeed:
        # Should succeed without exception
        await delete_model_by_id(db_session, test_model.id, env.project.id)
        assert await select_model(db_session, test_model.id, env.project.id) is None
    else:
        # Should fail with expected error
        with pytest.raises(DeletionConflictException, match=expected_error_fragment):
            await delete_model_by_id(db_session, test_model.id, env.project.id)


# === BATCH MODEL DELETION PARAMETRIZED TEST ===
@pytest.mark.parametrize(
    "test_name,model_count,deletable_count,has_workload_conflicts,has_nonexistent,expected_deleted_count,expected_exception_count",
    [
        # === BASIC BATCH SCENARIOS ===
        ("All deletable models", 3, 3, False, False, 3, 0),
        ("Empty list", 0, 0, False, False, 0, 0),
        ("Single deletable model", 1, 1, False, False, 1, 0),
        # === MIXED SCENARIOS ===
        ("Some with workload conflicts", 3, 2, True, False, 2, 1),
        # === ERROR SCENARIOS ===
        ("All nonexistent IDs", 2, 0, False, True, 0, 2),
        ("Mixed with nonexistent", 3, 2, False, True, 2, 1),
        # === COMPLEX SCENARIOS ===
        ("Complex mixed scenario", 5, 2, True, False, 2, 1),
        # 2 deletable models = 2 deleted, 1 workload conflict
    ],
)
@pytest.mark.asyncio
async def test_batch_model_deletion_scenarios(
    db_session: AsyncSession,
    test_name: str,
    model_count: int,
    deletable_count: int,
    has_workload_conflicts: bool,
    has_nonexistent: bool,
    expected_deleted_count: int,
    expected_exception_count: int,
):
    """
    Parametrized test covering all batch deletion scenarios.
    This systematically tests different combinations of models with various conflicts.
    """
    env = await factory.create_basic_test_environment(db_session)
    model_ids = []
    created_model_count = 0

    # Handle empty list case
    if model_count == 0:
        result = await delete_models(db_session, [], env.project.id)
        assert result == []
        return

    # Handle nonexistent IDs case
    if has_nonexistent and model_count > 0:
        model_ids.extend([uuid4() for _ in range(model_count if model_count == 2 else 1)])
        if model_count > 2:  # Mixed scenario - add some real models
            deletable_count = model_count - 1

    # Create deletable models
    for i in range(deletable_count):
        model = await factory.create_inference_model(
            db_session,
            env.project,
            name=f"Deletable Model {i}",
            onboarding_status=OnboardingStatus.ready,
        )
        model_ids.append(model.id)
        created_model_count += 1

    # Create models with workload conflicts
    if has_workload_conflicts:
        model = await factory.create_inference_model(
            db_session,
            env.project,
            name="Model with Workload Conflict",
            onboarding_status=OnboardingStatus.ready,
        )
        await factory.create_chart_workload(db_session, env.project, model_id=model.id, status=WorkloadStatus.RUNNING)
        model_ids.append(model.id)
        created_model_count += 1

    # Execute batch deletion
    if expected_exception_count == 0:
        deleted_ids = await delete_models(db_session, model_ids, env.project.id)
        assert len(deleted_ids) == expected_deleted_count
    else:
        with pytest.raises(ExceptionGroup) as exc_info:
            await delete_models(db_session, model_ids, env.project.id)

        exception_group = exc_info.value
        assert len(exception_group.exceptions) == expected_exception_count

        # Verify some models were still deleted (partial success)
        if expected_deleted_count > 0:
            remaining_models = await select_models(db_session, env.project.id, selected_model_ids=model_ids)
            # Count models that were actually created (exclude nonexistent IDs)
            actual_remaining = len([m for m in remaining_models if m.id in model_ids])
            expected_remaining = created_model_count - expected_deleted_count
            assert actual_remaining == expected_remaining


# === SPECIALIZED TESTS (Keep these for specific functionality) ===


# Batch deletion tests
@pytest.mark.parametrize(
    "test_name,scenario_setup,expected_deleted_count,expected_exception_count,expected_error_fragments",
    [
        ("All deletable models", lambda env: {"all_deletable": True, "count": 3}, 3, 0, []),
        (
            "Mixed scenarios",
            lambda env: {"deletable": 1, "with_workload": 1, "pending": 1},
            2,
            1,
            ["currently being used by a workload"],
        ),
        ("Empty list", lambda env: {"empty": True}, 0, 0, []),
        ("Nonexistent IDs", lambda env: {"nonexistent": 2}, 0, 2, ["not found in this project"]),
    ],
)
@pytest.mark.asyncio
async def test_batch_model_deletion(
    db_session: AsyncSession,
    test_name: str,
    scenario_setup: Callable,
    expected_deleted_count: int,
    expected_exception_count: int,
    expected_error_fragments: list[str],
):
    """Test batch deletion scenarios systematically."""
    env = await factory.create_basic_test_environment(db_session)
    setup = scenario_setup(env)
    model_ids: list[UUID] = []

    if setup.get("empty"):
        model_ids = []
    elif setup.get("nonexistent"):
        model_ids = [uuid4() for _ in range(setup["nonexistent"])]
    elif setup.get("all_deletable"):
        for i in range(setup["count"]):
            model = await factory.create_inference_model(
                db_session,
                env.project,
                name=f"Deletable Model {i}",
                onboarding_status=OnboardingStatus.ready,
            )
            model_ids.append(model.id)
    elif "deletable" in setup:
        # Mixed scenario
        for i in range(setup["deletable"]):
            model = await factory.create_inference_model(
                db_session,
                env.project,
                name=f"Deletable {i}",
                onboarding_status=OnboardingStatus.ready,
            )
            model_ids.append(model.id)

        if setup.get("with_workload"):
            model = await factory.create_inference_model(
                db_session,
                env.project,
                name="With Workload",
                onboarding_status=OnboardingStatus.ready,
            )
            await factory.create_chart_workload(
                db_session, env.project, model_id=model.id, status=WorkloadStatus.RUNNING
            )
            model_ids.append(model.id)

        if setup.get("pending"):
            model = await factory.create_inference_model(
                db_session,
                env.project,
                name="Pending",
                onboarding_status=OnboardingStatus.pending,
            )
            model_ids.append(model.id)

    # Execute deletion
    if expected_exception_count == 0:
        deleted_ids = await delete_models(db_session, model_ids, env.project.id)
        assert len(deleted_ids) == expected_deleted_count
    else:
        with pytest.raises(ExceptionGroup) as exc_info:
            await delete_models(db_session, model_ids, env.project.id)

        exception_group = exc_info.value
        assert len(exception_group.exceptions) == expected_exception_count

        error_messages = [str(e) for e in exception_group.exceptions]
        for expected_fragment in expected_error_fragments:
            assert any(expected_fragment in msg for msg in error_messages)
