# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ConflictException, DeletionConflictException, NotFoundException, ValidationException
from app.charts.config import FINETUNING_CHART_NAME, INFERENCE_CHART_NAME, MLFLOW_CHART_NAME
from app.dispatch.crds import K8sMetadata
from app.dispatch.kube_client import KubernetesClient
from app.minio.client import MinioClient
from app.models.models import OnboardingStatus
from app.models.repository import insert_model, select_model, update_onboarding_statuses
from app.models.schemas import FinetuneCreate, ModelDeployRequest
from app.models.service import (
    delete_model,
    get_finetunable_models,
    get_model,
    list_models,
    run_finetune_model_workload,
    run_model_deployment,
)
from app.overlays.models import Overlay
from app.secrets.schemas import SecretResponse
from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.schemas import WorkloadResponse
from tests import factory


@pytest.mark.asyncio
async def test_get_model_success(db_session: AsyncSession, test_namespace: str) -> None:
    """Test successfully getting a model by ID."""
    model = await factory.create_inference_model(db_session, namespace=test_namespace)

    with patch("app.models.service.update_onboarding_statuses", wraps=update_onboarding_statuses) as spy:
        result = await get_model(db_session, model.id, test_namespace)
        spy.assert_called_once()

    assert result is not None
    assert result.id == model.id
    assert result.name == model.name
    assert result.namespace == test_namespace


@pytest.mark.asyncio
async def test_get_model_not_found(db_session: AsyncSession, test_namespace: str) -> None:
    """Test get_model raises NotFoundException when model doesn't exist."""
    non_existent_id = uuid4()

    with pytest.raises(NotFoundException, match=f"Model {non_existent_id} not found"):
        await get_model(db_session, non_existent_id, test_namespace)


@pytest.mark.asyncio
async def test_list_models_success(db_session: AsyncSession, test_namespace: str) -> None:
    """Test listing models in a namespace."""
    await factory.create_inference_model(db_session, namespace=test_namespace, name="Model 1")
    await factory.create_inference_model(db_session, namespace=test_namespace, name="Model 2")

    with patch("app.models.service.update_onboarding_statuses", wraps=update_onboarding_statuses) as spy:
        result = await list_models(db_session, namespace=test_namespace)
        spy.assert_called_once()

    assert len(result) == 2
    names = {m.name for m in result}
    assert "Model 1" in names
    assert "Model 2" in names


@pytest.mark.asyncio
async def test_list_models_with_status_filter(db_session: AsyncSession, test_namespace: str) -> None:
    """Test listing models with onboarding status filter."""
    # Create models with different statuses
    await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Ready Model", onboarding_status=OnboardingStatus.ready
    )
    await factory.create_inference_model(
        db_session, namespace=test_namespace, name="Pending Model", onboarding_status=OnboardingStatus.pending
    )

    # List only ready models
    result = await list_models(db_session, namespace=test_namespace, onboarding_status=OnboardingStatus.ready)

    assert len(result) == 1
    assert result[0].name == "Ready Model"


@pytest.mark.asyncio
async def test_delete_model_success(db_session: AsyncSession, test_namespace: str) -> None:
    """Test successfully deleting a model with S3 cleanup."""
    # Create a model
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Model to Delete",
        model_weights_path="test-bucket/test-model/weights.bin",
    )
    model_id = model.id

    mock_minio_client = MagicMock(spec=MinioClient)

    with (
        patch("app.models.service.delete_from_s3", return_value=None) as mock_delete_s3,
        patch("app.models.service.update_onboarding_statuses", wraps=update_onboarding_statuses) as spy,
    ):
        await delete_model(db_session, model_id, test_namespace, mock_minio_client)
        mock_delete_s3.assert_called_once()
        spy.assert_called_once()


@pytest.mark.asyncio
async def test_delete_model_not_found(db_session: AsyncSession, test_namespace: str) -> None:
    """Test delete_model raises NotFoundException when model doesn't exist."""
    non_existent_id = uuid4()
    mock_minio_client = MagicMock(spec=MinioClient)

    with pytest.raises(NotFoundException, match=f"Model {non_existent_id} not found"):
        await delete_model(db_session, non_existent_id, test_namespace, mock_minio_client)


@pytest.mark.asyncio
async def test_insert_model_duplicate_name_raises_conflict(db_session: AsyncSession, test_namespace: str) -> None:
    """Test that inserting a model with duplicate name raises ConflictException."""
    # Insert first model
    await insert_model(
        db_session,
        name="Test Model",
        submitter="test@example.com",
        namespace=test_namespace,
        onboarding_status=OnboardingStatus.ready,
        canonical_name="test/model",
        model_weights_path="test-weights-path",
    )

    # Attempt to insert duplicate model - should fail
    with pytest.raises(ConflictException, match="already exists"):
        await insert_model(
            db_session,
            name="Test Model",
            submitter="test@example.com",
            namespace=test_namespace,
            onboarding_status=OnboardingStatus.ready,
            canonical_name="test/model-duplicate",
            model_weights_path="test-weights-path-2",
        )


@pytest.mark.asyncio
async def test_get_finetunable_models_success(db_session: AsyncSession) -> None:
    """Test successfully getting finetunable models from overlays."""
    # Create finetuning chart
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)

    # Mock overlays with canonical names
    mock_overlay1 = MagicMock(spec=Overlay)
    mock_overlay1.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay2 = MagicMock(spec=Overlay)
    mock_overlay2.canonical_name = "microsoft/DialoGPT-medium"

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=[mock_overlay1, mock_overlay2]),
    ):
        result = await get_finetunable_models(db_session)

    # Should return sorted canonical names
    expected = ["meta-llama/Llama-3.1-8B", "microsoft/DialoGPT-medium"]
    assert result == expected


@pytest.mark.asyncio
async def test_get_finetunable_models_empty(db_session: AsyncSession) -> None:
    """Test get_finetunable_models returns empty list when no overlays exist."""
    # Create finetuning chart
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=[]),
    ):
        result = await get_finetunable_models(db_session)

    assert result == []


@pytest.mark.asyncio
async def test_delete_model_with_s3_not_found(db_session: AsyncSession, test_namespace: str) -> None:
    """Test delete_model handles NotFoundException from S3 deletion gracefully."""

    # Create a model
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Model with Missing S3",
        model_weights_path="missing-bucket/missing-model/weights.bin",
    )
    model_id = model.id

    mock_minio_client = MagicMock(spec=MinioClient)

    # Mock S3 deletion to raise NotFoundException
    with patch("app.models.service.delete_from_s3", side_effect=NotFoundException("S3 object not found")):
        # Should not raise - just log warning
        await delete_model(db_session, model_id, test_namespace, mock_minio_client)

    # Verify model was still deleted from database
    deleted_model = await select_model(db_session, model_id, test_namespace)
    assert deleted_model is None


@pytest.mark.asyncio
async def test_delete_model_with_active_workload_does_not_delete_s3(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Deleting a model with an active workload must raise before touching S3."""
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Active Model",
        onboarding_status=OnboardingStatus.ready,
        model_weights_path="bucket/weights",
    )
    chart = await factory.create_chart(db_session)
    await factory.create_workload(
        db_session,
        namespace=test_namespace,
        model_id=model.id,
        status=WorkloadStatus.RUNNING,
        chart=chart,
    )

    mock_minio_client = MagicMock(spec=MinioClient)

    with patch("app.models.service.delete_from_s3") as mock_delete_s3:
        with pytest.raises(DeletionConflictException):
            await delete_model(db_session, model.id, test_namespace, mock_minio_client)

        mock_delete_s3.assert_not_called()

    # Model record must still exist
    assert await select_model(db_session, model.id, test_namespace) is not None


@pytest.mark.asyncio
async def test_delete_model_pending_with_active_workload_does_not_delete_s3(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Deleting a pending model being onboarded must raise before touching S3."""
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Pending Model",
        onboarding_status=OnboardingStatus.pending,
        model_weights_path="bucket/pending-weights",
    )
    chart = await factory.create_chart(db_session)
    await factory.create_workload(
        db_session,
        namespace=test_namespace,
        model_id=model.id,
        status=WorkloadStatus.PENDING,
        chart=chart,
    )

    mock_minio_client = MagicMock(spec=MinioClient)

    with patch("app.models.service.delete_from_s3") as mock_delete_s3:
        with pytest.raises(DeletionConflictException):
            await delete_model(db_session, model.id, test_namespace, mock_minio_client)

        mock_delete_s3.assert_not_called()

    assert await select_model(db_session, model.id, test_namespace) is not None


# ============================================================================
# Orchestration Tests - run_finetune_model_workload
# ============================================================================


@pytest.mark.asyncio
async def test_run_finetune_model_workload_with_uuid(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload with existing model UUID."""
    # Create base model
    base_model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Base Model",
        canonical_name="meta-llama/Llama-3.1-8B",
        model_weights_path="models/base-model/weights.bin",
        onboarding_status=OnboardingStatus.ready,
    )

    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request
    finetuning_data = FinetuneCreate(
        name="Finetuned Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock) as mock_apply,
        patch("app.models.service.update_onboarding_statuses", wraps=update_onboarding_statuses) as spy,
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=base_model.id,
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

        mock_apply.assert_called_once()
        spy.assert_called_once()

        assert result.name == "Finetuned Model"
        assert result.canonical_name == "meta-llama/Llama-3.1-8B"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_with_canonical_name(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload with canonical name (HuggingFace download)."""
    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request
    finetuning_data = FinetuneCreate(
        name="HF Finetuned Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock) as mock_apply,
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",  # Pass canonical name as string
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

        # Verify apply_manifest was called
        mock_apply.assert_called_once()

        # Verify result
        assert result.name == "HF Finetuned Model"
        assert result.canonical_name == "meta-llama/Llama-3.1-8B"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_includes_mlflow_tracking_when_mlflow_workspace_running(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Finetuning config gets MLflow tracking from workload endpoints (internal), not output."""
    finetuning_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    mlflow_chart = await factory.create_chart(db_session, name=MLFLOW_CHART_NAME)
    dataset = await factory.create_dataset(db_session, namespace=test_namespace)
    mlflow_workload = await factory.create_workload(
        db_session,
        namespace=test_namespace,
        chart=mlflow_chart,
        status=WorkloadStatus.RUNNING,
        workload_type=WorkloadType.WORKSPACE,
        include_isolation_data=False,
    )
    mlflow_response = WorkloadResponse.model_validate(mlflow_workload)
    expected_uri = mlflow_response.endpoints["internal"]

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    kube_client = MagicMock()
    with (
        patch("app.models.service.get_workloads", new_callable=AsyncMock, return_value=[mlflow_workload]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=kube_client,
            model_id="test/model",
            finetuning_data=FinetuneCreate(name="my-run", dataset_id=dataset.id),
            submitter="test@example.com",
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    overrides = helm_overrides_captured[0]
    assert "finetuning_config" in overrides
    tracking = overrides["finetuning_config"].get("tracking")
    assert tracking is not None
    assert tracking["mlflow_server_uri"] == expected_uri
    assert tracking["experiment_name"] == "my-run"
    assert overrides["finetuning_config"]["training_args"]["report_to"] == ["mlflow"]


@pytest.mark.asyncio
async def test_run_finetune_model_workload_skips_mlflow_tracking_when_no_mlflow_workspace(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Finetuning config has no tracking when no running MLflow workspace."""
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    dataset = await factory.create_dataset(db_session, namespace=test_namespace)

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    kube_client = MagicMock()
    with (
        patch("app.models.service.get_workloads", new_callable=AsyncMock, return_value=[]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=kube_client,
            model_id="test/model",
            finetuning_data=FinetuneCreate(name="my-run", dataset_id=dataset.id),
            submitter="test@example.com",
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    overrides = helm_overrides_captured[0]
    assert "finetuning_config" in overrides
    assert "tracking" not in overrides["finetuning_config"]


@pytest.mark.asyncio
async def test_run_finetune_model_workload_without_hf_token_does_not_call_get_secret_details(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload does not call get_secret_details when hf_token_secret_name is absent."""
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)
    finetuning_data = FinetuneCreate(
        name="No HF Token Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
        patch("app.models.service.get_secret_details") as mock_get_secret,
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )
        mock_get_secret.assert_not_called()


@pytest.mark.asyncio
async def test_run_finetune_model_workload_with_hf_token(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload includes HF token secret when provided."""
    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request with HF token secret name
    finetuning_data = FinetuneCreate(
        name="HF Token Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
        hf_token_secret_name="hf-token-secret",
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    hf_secret = SecretResponse(metadata=K8sMetadata(name="hf-token-secret", namespace=test_namespace))

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest") as mock_render,
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
        patch("app.models.service.get_secret_details", return_value=hf_secret) as mock_get_secret,
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

        # Verify render was called with HF token secret
        call_args = mock_render.call_args
        overlays = call_args[1]["overlays_values"]
        helm_overrides = overlays[-1]

        assert "hfTokenSecret" in helm_overrides
        assert helm_overrides["hfTokenSecret"]["name"] == "hf-token-secret"
        assert helm_overrides["hfTokenSecret"]["key"] == "token"

        mock_get_secret.assert_called_once_with(
            namespace=test_namespace,
            secret_name="hf-token-secret",
            kube_client=mock_kube_client,
        )


@pytest.mark.asyncio
async def test_run_finetune_model_workload_dataset_not_found(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload raises NotFoundException when dataset doesn't exist."""
    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request with non-existent dataset
    finetuning_data = FinetuneCreate(
        name="Model with Missing Dataset",
        dataset_id=uuid4(),  # Non-existent dataset
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        pytest.raises(NotFoundException, match="Dataset not found"),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )


@pytest.mark.asyncio
async def test_run_finetune_model_workload_model_without_weights(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload raises ValidationException when model has no weights."""
    # Create model without weights
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Model Without Weights",
        canonical_name="test/model",
        model_weights_path=None,  # No weights
        onboarding_status=OnboardingStatus.pending,
    )

    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request
    finetuning_data = FinetuneCreate(
        name="Finetuned Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)

    with pytest.raises(ValidationException, match="has no weights path"):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model.id,
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )


@pytest.mark.asyncio
async def test_run_finetune_model_workload_deployment_failure(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload sets workload status to FAILED on deployment error."""
    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request
    finetuning_data = FinetuneCreate(
        name="Failed Deployment",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", side_effect=Exception("K8s deployment failed")),
        pytest.raises(Exception, match="K8s deployment failed"),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )


# ============================================================================
# Orchestration Tests - run_model_deployment
# ============================================================================


@pytest.mark.asyncio
async def test_run_model_deployment_success(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test run_model_deployment successfully deploys a ready model."""
    # Create a ready model
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Ready Model",
        canonical_name="meta-llama/Llama-3.1-8B",
        model_weights_path="models/ready-model/weights.bin",
        onboarding_status=OnboardingStatus.ready,
    )

    # Create chart
    chart = await factory.create_chart(db_session, name=INFERENCE_CHART_NAME, chart_type=WorkloadType.INFERENCE)

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock) as mock_apply,
        patch("app.models.service.update_onboarding_statuses", wraps=update_onboarding_statuses) as spy,
    ):
        result = await run_model_deployment(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model.id,
            submitter=test_user,
            namespace=test_namespace,
        )

        mock_apply.assert_called_once()
        spy.assert_called_once()

        assert result.name == "Ready Model"
        assert result.id == model.id


@pytest.mark.asyncio
async def test_run_model_deployment_with_custom_specs(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_model_deployment with custom deployment specifications."""
    # Create a ready model
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Custom Spec Model",
        canonical_name="test/model",
        model_weights_path="models/custom/weights.bin",
        onboarding_status=OnboardingStatus.ready,
    )

    # Create chart
    chart = await factory.create_chart(db_session, name=INFERENCE_CHART_NAME, chart_type=WorkloadType.INFERENCE)

    # Create deployment request with custom specs
    request = ModelDeployRequest(
        image="custom-image:latest",
        gpus=4,
        memory_per_gpu=32,
        cpu_per_gpu=8,
        replicas=2,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest") as mock_render,
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        await run_model_deployment(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model.id,
            submitter=test_user,
            namespace=test_namespace,
            request=request,
        )

        # Verify render was called with custom specs
        call_args = mock_render.call_args
        overlays = call_args[1]["overlays_values"]
        helm_overrides = overlays[-1]

        assert helm_overrides["image"] == "custom-image:latest"
        assert helm_overrides["gpus"] == 4
        assert helm_overrides["memory_per_gpu"] == 32
        assert helm_overrides["cpu_per_gpu"] == 8
        assert helm_overrides["replicas"] == 2


@pytest.mark.asyncio
async def test_run_model_deployment_model_not_ready(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_model_deployment raises ValidationException when model is not ready."""
    # Create a pending model
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Pending Model",
        canonical_name="test/model",
        model_weights_path="models/pending/weights.bin",
        onboarding_status=OnboardingStatus.pending,
    )

    # Create chart
    chart = await factory.create_chart(db_session, name=INFERENCE_CHART_NAME, chart_type=WorkloadType.INFERENCE)

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)

    with pytest.raises(ValidationException, match="not ready for deployment"):
        await run_model_deployment(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model.id,
            submitter=test_user,
            namespace=test_namespace,
        )


@pytest.mark.asyncio
async def test_run_model_deployment_model_not_found(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_model_deployment raises NotFoundException when model doesn't exist."""
    # Create chart
    chart = await factory.create_chart(db_session, name=INFERENCE_CHART_NAME, chart_type=WorkloadType.INFERENCE)

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    non_existent_id = uuid4()

    with pytest.raises(NotFoundException, match="not found"):
        await run_model_deployment(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=non_existent_id,
            submitter=test_user,
            namespace=test_namespace,
        )


@pytest.mark.asyncio
async def test_run_model_deployment_failure(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test run_model_deployment sets workload status to FAILED on deployment error."""
    # Create a ready model
    model = await factory.create_inference_model(
        db_session,
        namespace=test_namespace,
        name="Failed Deployment",
        canonical_name="test/model",
        model_weights_path="models/failed/weights.bin",
        onboarding_status=OnboardingStatus.ready,
    )

    # Create chart
    chart = await factory.create_chart(db_session, name=INFERENCE_CHART_NAME, chart_type=WorkloadType.INFERENCE)

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.overlay = {}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", side_effect=Exception("K8s deployment failed")),
        pytest.raises(Exception, match="K8s deployment failed"),
    ):
        await run_model_deployment(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model.id,
            submitter=test_user,
            namespace=test_namespace,
        )
