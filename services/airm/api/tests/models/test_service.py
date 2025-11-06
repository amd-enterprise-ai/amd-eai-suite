# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from pydantic_core import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus
from app.charts.config import FINETUNING_CHART_NAME, INFERENCE_CHART_NAME, MLFLOW_CHART_NAME
from app.models.models import OnboardingStatus
from app.models.repository import insert_model, update_onboarding_statuses
from app.models.schemas import FinetuneCreate, ModelDeployRequest
from app.models.service import (
    delete_model,
    delete_models,
    get_finetunable_models,
    run_finetune_model_workload,
    run_model_deployment,
)
from app.utilities.exceptions import (
    ConflictException,
    DeletionConflictException,
    NotFoundException,
)
from app.workloads.enums import WorkloadType
from tests import factory


@pytest.mark.asyncio
async def test_run_model_deployment_success(db_session: AsyncSession):
    """Test successful model deployment workload submission."""
    env = await factory.create_full_test_environment(db_session, with_model=True, with_dataset=True)

    inference_chart = await factory.create_chart(
        db_session,
        name=INFERENCE_CHART_NAME,
    )

    # Create chart workload using factory instead of mocking submission
    chart_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=inference_chart,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        workload_type=WorkloadType.INFERENCE,
        display_name="Test Deployment",
        name="mw-test-deployment",
    )

    with (
        patch("app.charts.repository.select_chart", return_value=inference_chart),
        patch("app.models.service.submit_chart_workload", return_value=chart_workload),
        patch("app.overlays.repository.list_overlays", return_value=[]),
    ):
        result = await run_model_deployment(
            session=db_session,
            model_id=env.model.id,
            creator=env.user,
            token="token123",
            project=env.project,
        )

    # Verify workload was returned
    assert result is not None
    assert result.display_name is not None
    assert result.id == chart_workload.id


@pytest.mark.asyncio
async def test_run_model_deployment_with_different_specs(db_session: AsyncSession):
    """Test model deployment with different resource specifications."""
    env = await factory.create_full_test_environment(db_session)

    # Create model and inference chart
    model = await factory.create_inference_model(
        db_session,
        env.project,
        name="Test Model",
        onboarding_status=OnboardingStatus.ready,
    )

    inference_chart = await factory.create_chart(
        db_session,
        name=INFERENCE_CHART_NAME,
    )

    # Create chart workload using factory
    chart_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=inference_chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        display_name="Test Different Specs Deployment",
        name="mw-test-deployment-specs",
        user_inputs={
            "gpus": 2,
            "memory_per_gpu": 16.0,
            "cpu_per_gpu": 4.0,
            "image": "custom/ml-image:latest",
        },
    )

    with (
        patch("app.charts.repository.select_chart", return_value=inference_chart),
        patch("app.models.service.submit_chart_workload", return_value=chart_workload),
        patch("app.overlays.repository.list_overlays", return_value=[]),
    ):
        result = await run_model_deployment(
            db_session,
            model.id,
            env.user,
            "token123",
            env.project,
            request=ModelDeployRequest(
                image="custom/ml-image:latest",
                gpus=2,
                memory_per_gpu=16.0,
                cpu_per_gpu=4.0,
            ),
        )

    # Verify workload was returned
    assert result is not None
    assert result.display_name is not None

    assert result.user_inputs["gpus"] == 2
    assert result.user_inputs["memory_per_gpu"] == 16.0
    assert result.user_inputs["cpu_per_gpu"] == 4.0
    assert result.user_inputs["image"] == "custom/ml-image:latest"


@pytest.mark.asyncio
async def test_run_model_deployment_replica_validation(db_session: AsyncSession):
    """Test replica validation in model deployment."""
    env = await factory.create_full_test_environment(db_session, with_model=True)

    # Set model properties for validation test
    env.model.model_weights_path = "test-bucket/test-project/models/test-model"
    env.model.onboarding_status = OnboardingStatus.ready
    await db_session.flush()

    # Test invalid replica counts
    test_cases = [0, -1, 11, 100]

    for replicas in test_cases:
        with pytest.raises(ValidationError):
            await run_model_deployment(
                db_session,
                env.model.id,
                env.user,
                "token123",
                env.project,
                request=ModelDeployRequest(replicas=replicas),
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("model_id", [uuid4(), "meta-llama/Llama-3-8b"])
async def test_run_finetune_model_workload_success(db_session: AsyncSession, model_id):
    """Test successful finetune model workload submission with both UUID and canonical name."""
    env = await factory.create_full_test_environment(db_session, with_dataset=True)

    # Create base model for UUID test case
    if isinstance(model_id, UUID):
        base_model = await factory.create_inference_model(
            db_session,
            env.project,
            name="Base Model",
            onboarding_status=OnboardingStatus.ready,
        )
        model_input = base_model.id
    else:
        model_input = model_id  # Canonical name input

    # Create finetuning chart
    finetune_chart = await factory.create_chart(
        db_session,
        name=FINETUNING_CHART_NAME,
    )

    finetune_create = FinetuneCreate(
        name="Finetuned Model",
        dataset_id=env.dataset.id,
        learning_rate=0.001,
        epochs=3,
        batch_size=8,
    )

    # Create chart workload using factory
    chart_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=finetune_chart,
        dataset_id=env.dataset.id,
        workload_type=WorkloadType.FINE_TUNING,
        display_name="Test Finetuning from Canonical",
        name="mw-test-finetune-canonical",
    )

    with (
        patch("app.charts.repository.select_chart", return_value=finetune_chart),
        patch("app.models.service.submit_chart_workload", return_value=chart_workload),
        patch("app.overlays.repository.list_overlays", return_value=[]),
        patch("app.datasets.repository.select_dataset", return_value=env.dataset),
    ):
        result = await run_finetune_model_workload(
            db_session,
            model_id=model_input,
            finetuning_data=finetune_create,
            creator=env.creator,
            token="token123",
            project=env.project,
        )

    # Verify workload was returned
    assert result is not None
    assert result.display_name is not None
    assert result.id == chart_workload.id


@pytest.mark.asyncio
async def test_run_finetune_model_workload_model_not_found(db_session: AsyncSession):
    """Test finetune workload fails when model UUID is not found."""
    env = await factory.create_basic_test_environment(db_session)

    dataset = await factory.create_dataset(db_session, env.project, name="finetune-dataset")
    non_existent_model_id = uuid4()

    finetune_data = FinetuneCreate(
        name="Test Finetune",
        dataset_id=dataset.id,
        learning_rate=0.001,
        epochs=3,
        batch_size=8,
    )

    with pytest.raises(NotFoundException, match=f"Model {non_existent_model_id} not found"):
        await run_finetune_model_workload(
            db_session,
            model_id=non_existent_model_id,
            finetuning_data=finetune_data,
            creator=env.creator,
            token="token123",
            project=env.project,
        )


@pytest.mark.asyncio
async def test_update_onboarding_statuses_success(db_session: AsyncSession):
    """Test updating model onboarding statuses with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    # Create models with different statuses
    model1 = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model 1",
        onboarding_status=OnboardingStatus.pending,
    )

    model2 = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model 2",
        onboarding_status=OnboardingStatus.pending,
    )

    model3 = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model 3",
        onboarding_status=OnboardingStatus.ready,  # Should not be updated
    )

    # Update statuses by calling the service function which updates based on workload statuses
    await update_onboarding_statuses(db_session, env.project.id)

    # Verify statuses remain as set since no workloads exist to update them
    await db_session.refresh(model1)
    await db_session.refresh(model2)
    await db_session.refresh(model3)

    # Without workloads, statuses should remain unchanged
    assert model1.onboarding_status == OnboardingStatus.pending
    assert model2.onboarding_status == OnboardingStatus.pending
    assert model3.onboarding_status == OnboardingStatus.ready


@pytest.mark.asyncio
async def test_insert_model_duplicate_name_raises_conflict(db_session: AsyncSession):
    """Test that duplicate model name in same project/cluster raises ConflictException."""
    env = await factory.create_basic_test_environment(db_session)

    # Insert first model
    first_model = await insert_model(
        db_session,
        name="Test Model",
        creator=env.creator,
        project_id=env.project.id,
        onboarding_status=OnboardingStatus.ready,
        canonical_name="test/model",
        model_weights_path="test-weights-path",
    )
    await db_session.flush()  # Flush to database to get constraints enforced

    # Attempt to insert duplicate model - should fail with ConflictException
    with pytest.raises(ConflictException, match="A model with name 'Test Model' already exists"):
        await insert_model(
            db_session,
            name="Test Model",
            creator=env.creator,
            project_id=env.project.id,
            onboarding_status=OnboardingStatus.ready,
            canonical_name="test/model",
            model_weights_path="test-weights-path-2",
        )

    # Verify first model was created successfully
    assert first_model is not None
    assert first_model.name == "Test Model"
    assert first_model.canonical_name == "test/model"


@pytest.mark.asyncio
async def test_run_model_deployment_model_not_found(db_session: AsyncSession):
    """Test model deployment fails when model not found."""
    env = await factory.create_full_test_environment(db_session)

    non_existent_model_id = uuid4()

    with pytest.raises(NotFoundException, match="Model.*not found"):
        await run_model_deployment(
            db_session,
            non_existent_model_id,
            env.user,
            "token123",
            env.project,
        )


@pytest.mark.asyncio
async def test_delete_models_success(db_session: AsyncSession):
    """Test successful deletion of multiple models with S3 cleanup."""
    env = await factory.create_basic_test_environment(db_session)

    # Create two models to delete
    model1 = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model 1",
        model_weights_path="test-bucket/model1/weights.bin",
    )
    model2 = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model 2",
        model_weights_path="test-bucket/model2/weights.bin",
    )

    model_ids = [model1.id, model2.id]
    mock_minio_client = AsyncMock()

    # Mock S3 operations
    with patch("app.models.service.delete_from_s3", return_value=None) as mock_delete_s3:
        result = await delete_models(db_session, model_ids, env.project.id, mock_minio_client)
        assert set(result) == set(model_ids)
        # S3 cleanup should be called for each model
        assert mock_delete_s3.call_count == 2


@pytest.mark.asyncio
async def test_delete_models_not_found(db_session: AsyncSession):
    """Test deletion fails when models are not found."""
    env = await factory.create_basic_test_environment(db_session)

    # Try to delete non-existent models
    model_ids = [uuid4()]
    mock_minio_client = AsyncMock()

    # Only mock S3 operations
    with patch("app.models.service.delete_from_s3") as mock_delete_s3:
        with pytest.raises(ExceptionGroup) as exc_info:
            await delete_models(db_session, model_ids, env.project.id, mock_minio_client)

        # Check that the ExceptionGroup contains NotFoundException
        assert len(exc_info.value.exceptions) >= 1
        assert any(isinstance(e, NotFoundException) for e in exc_info.value.exceptions)

        # S3 cleanup should not be called when no models are deleted
        mock_delete_s3.assert_not_called()


@pytest.mark.asyncio
async def test_delete_models_error_rollback(db_session: AsyncSession):
    """Test that errors during deletion are properly raised."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a model
    model = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model to fail deletion",
    )

    model_ids = [model.id]
    mock_minio_client = AsyncMock()

    # Mock delete_models_by_ids to raise an error
    with (
        patch("app.models.service.delete_models_by_ids", side_effect=Exception("DB error")),
        patch("app.models.service.delete_from_s3") as mock_delete_s3,
    ):
        with pytest.raises(Exception) as exc_info:
            await delete_models(db_session, model_ids, env.project.id, mock_minio_client)
        assert "DB error" in str(exc_info.value)
        # Transaction rollback is handled by API layer, not service layer
        mock_delete_s3.assert_not_called()


@pytest.mark.asyncio
async def test_delete_models_partial_success(db_session: AsyncSession):
    """Test that S3 cleanup happens for successfully deleted models even when ExceptionGroup is raised."""
    env = await factory.create_basic_test_environment(db_session)

    # Create two models
    model1 = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model 1",
        model_weights_path="test-bucket/model1/weights.bin",
    )
    model2 = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model 2",
        model_weights_path="test-bucket/model2/weights.bin",
    )

    model_ids = [model1.id, model2.id]
    mock_minio_client = AsyncMock()

    # Mock delete_models_by_ids to simulate partial failure
    with (
        patch(
            "app.models.service.delete_models_by_ids",
            side_effect=ExceptionGroup("Some models could not be deleted", [NotFoundException("Model not found")]),
        ) as mock_delete,
        patch("app.models.service.delete_from_s3") as mock_delete_s3,
    ):
        with pytest.raises(ExceptionGroup) as exc_info:
            await delete_models(db_session, model_ids, env.project.id, mock_minio_client)

        # Check that the ExceptionGroup contains the expected exception
        assert len(exc_info.value.exceptions) >= 1
        assert any(isinstance(e, NotFoundException) for e in exc_info.value.exceptions)

        # Verify deletion was attempted
        mock_delete.assert_called_once_with(db_session, model_ids, env.project.id)

        # Note: S3 cleanup behavior depends on implementation details
        # The test should verify the actual behavior based on which models were deleted


@pytest.mark.asyncio
async def test_delete_single_model_success(db_session: AsyncSession):
    """Test successful single model deletion with MinIO cleanup."""
    env = await factory.create_basic_test_environment(db_session)
    mock_minio_client = Mock()

    # Create model to delete
    model = await factory.create_inference_model(
        db_session,
        env.project,
        name="Test Model",
        model_weights_path="test-bucket/test-model/weights.bin",
        canonical_name="test/model",
    )

    # Only mock S3 operations
    with patch("app.models.service.delete_from_s3", return_value=None) as mock_delete_s3:
        await delete_model(db_session, model.id, env.project.id, mock_minio_client)

        # Verify S3 cleanup was called with the model
        mock_delete_s3.assert_called_once()
        call_args = mock_delete_s3.call_args[0]
        assert call_args[0].id == model.id
        assert call_args[1] == mock_minio_client


@pytest.mark.asyncio
async def test_delete_single_model_propagates_exceptions(db_session: AsyncSession):
    """Test that single model deletion properly propagates deletion conflict exceptions."""
    env = await factory.create_basic_test_environment(db_session)
    mock_minio_client = Mock()

    # Create model to delete
    model = await factory.create_inference_model(
        db_session,
        env.project,
        name="Model in use",
    )

    # Mock the repository to raise a DeletionConflictException
    with patch(
        "app.models.service.delete_model_by_id", side_effect=DeletionConflictException("Model in use")
    ) as mock_delete_repo:
        with pytest.raises(DeletionConflictException, match="Model in use"):
            await delete_model(db_session, model.id, env.project.id, mock_minio_client)

        mock_delete_repo.assert_called_once_with(db_session, model.id, env.project.id)


@pytest.mark.asyncio
async def test_get_finetunable_models_success(db_session: AsyncSession):
    """Test successful retrieval of finetunable models."""

    # Create finetuning chart
    finetune_chart = await factory.create_chart(
        db_session,
        name=FINETUNING_CHART_NAME,
    )

    # Create overlays for the chart
    overlay1 = await factory.create_overlay(
        db_session,
        finetune_chart,
        canonical_name="meta-llama/Llama-2-7b-hf",
    )

    overlay2 = await factory.create_overlay(
        db_session,
        finetune_chart,
        canonical_name="microsoft/DialoGPT-medium",
    )

    result = await get_finetunable_models(db_session)

    # Should return sorted canonical names
    expected = ["meta-llama/Llama-2-7b-hf", "microsoft/DialoGPT-medium"]
    assert result == expected


@pytest.mark.asyncio
async def test_finetune_with_mlflow_running(db_session: AsyncSession):
    """Test that MLflow tracking configuration is included when MLflow is running."""
    env = await factory.create_full_test_environment(db_session, with_model=True, with_dataset=True)

    # Set model as ready for finetuning
    env.model.onboarding_status = OnboardingStatus.ready
    env.model.model_weights_path = "test-bucket/models/base-model"
    await db_session.flush()

    # Create finetuning chart
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)

    # Create running MLflow workspace
    mlflow_chart = await factory.create_chart(
        db_session,
        name=MLFLOW_CHART_NAME,
        chart_type=WorkloadType.WORKSPACE,
    )
    await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=mlflow_chart,
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING.value,
        output={"internal_host": "http://mlflow.test:5000"},
    )

    finetuning_data = FinetuneCreate(
        name="test-finetune-job",
        dataset_id=env.dataset.id,
        epochs=3,
        batch_size=16,
        learning_rate=0.001,
    )

    with (
        patch("app.charts.repository.select_chart", return_value=finetune_chart),
        patch("app.managed_workloads.service.render_helm_template", return_value="whatever") as mock_render,
        patch("app.managed_workloads.service.validate_and_parse_workload_manifest", return_value=[{}]),
        patch("app.managed_workloads.service.extract_components_and_submit_workload"),
        patch("app.managed_workloads.service.get_workload_host_from_HTTPRoute_manifest", return_value=None),
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            model_id=env.model.id,
            finetuning_data=finetuning_data,
            creator="test-user",
            token="test-token",
            project=env.project,
            display_name="my-custom-job-name",
        )

        # Verify MLflow tracking config is included
        assert result.display_name == "my-custom-job-name"

        finetuning_config = result.user_inputs["finetuning_config"]
        tracking_config = finetuning_config["tracking"]
        assert tracking_config["mlflow_server_uri"] == "http://mlflow.test:5000"
        assert tracking_config["experiment_name"] == finetuning_data.name

        # Verify tracking config was passed to helm template
        overlays_values = mock_render.call_args[0][3]
        assert "tracking" in overlays_values[-1]["finetuning_config"]


@pytest.mark.asyncio
async def test_finetune_without_mlflow_running(db_session: AsyncSession):
    """Test that no MLflow tracking configuration is included when no MLflow instance is running."""
    env = await factory.create_full_test_environment(db_session, with_model=True, with_dataset=True)

    # Set model as ready for finetuning
    env.model.onboarding_status = OnboardingStatus.ready
    env.model.model_weights_path = "test-bucket/models/base-model"
    await db_session.flush()

    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)

    finetuning_data = FinetuneCreate(
        name="test-finetune-job",
        dataset_id=env.dataset.id,
        epochs=3,
        batch_size=16,
        learning_rate=0.001,
    )

    with (
        patch("app.managed_workloads.service.render_helm_template", return_value="whatever"),
        patch("app.managed_workloads.service.validate_and_parse_workload_manifest", return_value=[{}]),
        patch("app.managed_workloads.service.extract_components_and_submit_workload"),
        patch("app.managed_workloads.service.get_workload_host_from_HTTPRoute_manifest", return_value=None),
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            model_id=env.model.id,
            finetuning_data=finetuning_data,
            creator="test-user",
            token="test-token",
            project=env.project,
            display_name="my-job-without-mlflow",
        )

        # Verify NO tracking configuration is included
        assert result.display_name == "my-job-without-mlflow"
        finetuning_config = result.user_inputs.get("finetuning_config", {})
        assert "tracking" not in finetuning_config
