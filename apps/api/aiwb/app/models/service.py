# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import NotFoundException, ValidationException

from ..charts.config import FINETUNING_CHART_NAME, INFERENCE_CHART_NAME, MLFLOW_CHART_NAME
from ..charts.service import get_chart
from ..charts.utils import render_helm_template
from ..datasets.repository import select_dataset
from ..dispatch.kube_client import KubernetesClient
from ..minio.client import MinioClient
from ..minio.config import MINIO_BUCKET
from ..overlays.repository import list_overlays
from ..secrets.service import get_secret_details
from ..workloads.enums import WorkloadStatus, WorkloadType
from ..workloads.repository import create_workload, get_workloads
from ..workloads.schemas import WorkloadResponse
from ..workloads.utils import apply_manifest, sanitize_user_id
from .models import InferenceModel, OnboardingStatus
from .repository import (
    delete_model_by_id,
    insert_model,
    select_model,
    select_models,
    update_onboarding_statuses,
)
from .schemas import FinetuneCreate, ModelDeployRequest, ModelResponse
from .utils import delete_from_s3, format_model_path, get_finetuned_model_weights_path


async def get_model(
    session: AsyncSession,
    model_id: UUID,
    namespace: str,
) -> InferenceModel:
    await update_onboarding_statuses(session, namespace)
    model = await select_model(session, model_id, namespace=namespace)
    if model is None:
        raise NotFoundException(f"Model {model_id} not found")

    return model


async def get_finetunable_models(session: AsyncSession, chart_name: str = FINETUNING_CHART_NAME) -> list[str]:
    """Get canonical names of all the models that can be finetuned"""
    chart = await get_chart(session, chart_name=chart_name)
    overlays = await list_overlays(session, chart_id=chart.id, include_generic=True)
    return sorted([overlay.canonical_name for overlay in overlays])


async def list_models(
    session: AsyncSession,
    namespace: str,
    onboarding_status: OnboardingStatus | None = None,
    name: str | None = None,
) -> list[InferenceModel]:
    await update_onboarding_statuses(session, namespace)
    return await select_models(
        session=session,
        onboarding_status=onboarding_status,
        name=name,
        namespace=namespace,
    )


async def delete_model(session: AsyncSession, model_id: UUID, namespace: str, minio_client: MinioClient) -> None:
    """Delete a model record and its S3 weights.

    Raises:
        NotFoundException: Model not found in the database.
        DeletionConflictException: Model has active or pending workloads.
        ExternalServiceError, ForbiddenException, ValidationException:
            S3 operation failure — the DB transaction rolls back, leaving both
            the model record and S3 data intact.
    """
    model = await get_model(session, model_id, namespace)
    await delete_model_by_id(session, model_id, namespace)
    try:
        await delete_from_s3(model, minio_client)
    except NotFoundException:
        logger.warning(f"Model weights not found in S3 for model {model_id}, skipping S3 cleanup.")


async def run_finetune_model_workload(
    session: AsyncSession,
    kube_client: KubernetesClient,
    model_id: UUID | str,
    finetuning_data: FinetuneCreate,
    submitter: str,
    namespace: str,
    display_name: str | None = None,
) -> ModelResponse:
    """
    Finetune a model providing either just a canonical name or an existing model's UUID.
    In the first case the model will be downloaded automatically by the workload from HuggingFace.
    In the latter case, the model weights will be downloaded from the storage into the finetuning container.
    """
    try:
        model_id = UUID(model_id) if isinstance(model_id, str) else model_id
    except ValueError:
        pass

    hf_token_secret_name = None
    if finetuning_data.hf_token_secret_name:
        hf_secret = await get_secret_details(
            namespace=namespace,
            secret_name=finetuning_data.hf_token_secret_name,
            kube_client=kube_client,
        )
        hf_token_secret_name = hf_secret.metadata.name

    if isinstance(model_id, UUID):
        model = await get_model(session, model_id, namespace)
        if not model.model_weights_path:
            raise ValidationException(
                f"Base model {model_id} has no weights path. The model must be downloaded before finetuning."
            )
        model_canonical_name = model.canonical_name
    else:
        model = None
        model_canonical_name = model_id

    chart = await get_chart(session, chart_name=FINETUNING_CHART_NAME)

    overlays = await list_overlays(
        session, chart_id=chart.id, canonical_name=model_canonical_name, include_generic=True
    )
    overlay_values = [chart.signature] + [overlay.overlay for overlay in overlays]

    dataset = await select_dataset(session, dataset_id=finetuning_data.dataset_id, namespace=namespace)
    if not dataset:
        raise NotFoundException("Dataset not found")

    finetuning_path = get_finetuned_model_weights_path(model_canonical_name, finetuning_data.name, namespace)

    finetuned_model = await insert_model(
        session=session,
        name=finetuning_data.name,
        submitter=submitter,
        namespace=namespace,
        onboarding_status=OnboardingStatus.pending,
        canonical_name=model_canonical_name,
        model_weights_path=os.path.join(finetuning_path, "checkpoint-final"),
    )

    # Build the finetuning configuration
    finetuning_config: dict[str, dict] = {
        "data_conf": {"training_data": {"datasets": [{"path": os.path.join(MINIO_BUCKET, dataset.path)}]}},
        "batchsize_conf": {"total_train_batch_size": finetuning_data.batch_size},
        "overrides": {"lr_multiplier": finetuning_data.learning_rate},
        "training_args": {"num_train_epochs": finetuning_data.epochs},
    }

    # Check for MLflow tracking configuration
    mlflow_workloads = await get_workloads(
        session=session,
        namespace=namespace,
        workload_types=[WorkloadType.WORKSPACE],
        status_filter=[WorkloadStatus.RUNNING],
        chart_name=MLFLOW_CHART_NAME,
    )

    mlflow_response = WorkloadResponse.model_validate(mlflow_workloads[0]) if mlflow_workloads else None
    if mlflow_response and mlflow_response.endpoints and mlflow_response.endpoints.get("internal"):
        mlflow_uri = mlflow_response.endpoints["internal"]
        # Add http:// prefix if not already present
        if not mlflow_uri.startswith(("http://", "https://")):
            mlflow_uri = f"http://{mlflow_uri}"
        tracking_config = {
            "mlflow_server_uri": mlflow_uri,
            "experiment_name": finetuning_data.name,
        }
        finetuning_config["training_args"]["report_to"] = ["mlflow"]
        finetuning_config["training_args"]["logging_steps"] = 10
        finetuning_config["tracking"] = tracking_config
        logger.info(f"Found running MLflow workspace for namespace {namespace} - URI: {mlflow_uri}")
    else:
        logger.info(f"No running MLflow workspace found for namespace {namespace} - skipping MLflow tracking")

    # All paths need to include the bucket prefix when accessed in the workload
    helm_overrides = {
        "checkpointsRemote": os.path.join(MINIO_BUCKET, finetuning_path),
        "basemodel": os.path.join(MINIO_BUCKET, model.model_weights_path) if model else f"hf://{model_canonical_name}",
        "finetuning_config": finetuning_config,
    }

    # Add HuggingFace token secret if provided
    if hf_token_secret_name:
        helm_overrides["hfTokenSecret"] = {"name": hf_token_secret_name, "key": "token"}

    # Create workload record
    workload = await create_workload(
        session=session,
        display_name=display_name or "",  # Auto-generated if empty
        workload_type=WorkloadType.FINE_TUNING,
        chart_id=chart.id,
        namespace=namespace,
        submitter=submitter,
        status=WorkloadStatus.PENDING,
        model_id=finetuned_model.id,
        dataset_id=finetuning_data.dataset_id,
    )

    logger.info(f"Deploying finetuning workload {workload.id} to namespace {namespace}")

    try:
        # Add helm overrides as the last overlay (highest priority)
        overlay_values.append(helm_overrides)

        manifest = await render_helm_template(
            chart=chart,
            name=workload.name,
            namespace=namespace,
            overlays_values=overlay_values,
        )
        workload.manifest = manifest
        await session.flush()

        await apply_manifest(kube_client, manifest, workload, namespace, submitter)
        logger.info(f"Successfully deployed finetuning workload {workload.id}")

    except Exception as e:
        logger.error(f"Failed to deploy finetuning workload {workload.id}: {e}")
        workload.status = WorkloadStatus.FAILED
        await session.flush()
        raise

    return ModelResponse.model_validate(finetuned_model)


async def run_model_deployment(
    session: AsyncSession,
    kube_client: KubernetesClient,
    model_id: UUID,
    submitter: str,
    namespace: str,
    request: ModelDeployRequest | None = None,
    display_name: str | None = None,
) -> ModelResponse:
    """Deploy a fine-tuned model for inference."""
    model = await get_model(session, model_id, namespace)

    # Check if model is ready for deployment
    if model.onboarding_status != OnboardingStatus.ready:
        raise ValidationException(
            f"Model {model_id} is not ready for deployment. Current status: {model.onboarding_status}"
        )

    chart = await get_chart(session, chart_name=INFERENCE_CHART_NAME)

    # Get model-specific overlays
    overlays = await list_overlays(
        session, chart_id=chart.id, canonical_name=model.canonical_name, include_generic=False
    )
    overlay_values = [chart.signature] + [overlay.overlay for overlay in overlays]

    request_overrides = (
        {
            **({"image": request.image} if request.image else {}),
            **({"gpus": request.gpus} if request.gpus else {}),
            **({"memory_per_gpu": request.memory_per_gpu} if request.memory_per_gpu else {}),
            **({"cpu_per_gpu": request.cpu_per_gpu} if request.cpu_per_gpu else {}),
            **({"replicas": request.replicas} if request.replicas else {}),
        }
        if request
        else {}
    )

    # All paths need to include the bucket prefix
    helm_overrides: dict = {
        **request_overrides,
        "model": format_model_path(os.path.join(MINIO_BUCKET, model.model_weights_path)),
        "metadata": {
            **chart.signature.get("metadata", {}),
            "project_id": namespace,
            "user_id": sanitize_user_id(submitter),
        },
    }

    # Create workload record
    workload = await create_workload(
        session=session,
        display_name=display_name or "",  # Auto-generated if empty
        workload_type=WorkloadType.INFERENCE,
        chart_id=chart.id,
        namespace=namespace,
        submitter=submitter,
        status=WorkloadStatus.PENDING,
        model_id=model.id,
    )

    logger.info(f"Deploying inference workload {workload.id} to namespace {namespace}")

    try:
        # Add helm overrides as the last overlay (highest priority)
        overlay_values.append(helm_overrides)

        manifest = await render_helm_template(
            chart=chart,
            name=workload.name,
            namespace=namespace,
            overlays_values=overlay_values,
        )
        workload.manifest = manifest
        await session.flush()

        await apply_manifest(kube_client, manifest, workload, namespace, submitter)
        logger.info(f"Successfully deployed inference workload {workload.id}")

    except Exception as e:
        logger.error(f"Failed to deploy inference workload {workload.id}: {e}")
        workload.status = WorkloadStatus.FAILED
        await session.flush()
        raise

    return ModelResponse.model_validate(model)
