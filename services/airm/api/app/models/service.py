# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import os
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus

from ..charts.config import FINETUNING_CHART_NAME, INFERENCE_CHART_NAME, MLFLOW_CHART_NAME
from ..charts.service import get_chart
from ..datasets.repository import select_dataset
from ..managed_workloads.repository import select_workloads
from ..managed_workloads.schemas import ChartWorkloadResponse
from ..managed_workloads.service import submit_chart_workload
from ..messaging.sender import MessageSender
from ..overlays.repository import list_overlays
from ..projects.models import Project
from ..users.models import User
from ..utilities.config import MINIO_BUCKET
from ..utilities.exceptions import NotFoundException, ValidationException
from ..utilities.minio import MinioClient
from ..workloads.enums import WorkloadType
from .models import InferenceModel, OnboardingStatus
from .repository import (
    delete_model_by_id,
    insert_model,
    select_model,
    select_models,
    update_model,
    update_onboarding_statuses,
)
from .repository import delete_models as delete_models_by_ids
from .schemas import FinetuneCreate, ModelDeployRequest, ModelEdit
from .utils import delete_from_s3, format_model_path, get_finetuned_model_weights_path


async def get_model(
    session: AsyncSession,
    model_id: UUID,
    project_id: UUID,
) -> InferenceModel:
    model = await select_model(session, model_id, project_id=project_id)
    if model is None:
        raise NotFoundException(f"Model {model_id} not found")

    return model


async def get_finetunable_models(session: AsyncSession) -> list[str]:
    """Get canonical names of all the models that can be finetuned"""
    chart = await get_chart(session, chart_name=FINETUNING_CHART_NAME)
    overlays = await list_overlays(session, chart_id=chart.id, include_generic=True)
    return sorted([overlay.canonical_name for overlay in overlays])


async def list_models(
    session: AsyncSession,
    project_id: UUID,
    onboarding_status: OnboardingStatus | None = None,
    name: str | None = None,
) -> list[InferenceModel]:
    await update_onboarding_statuses(session, project_id)
    return await select_models(
        session=session,
        onboarding_status=onboarding_status,
        name=name,
        project_id=project_id,
    )


async def update_model_by_id(
    session: AsyncSession, model_id: UUID, project_id: UUID, update_data: ModelEdit, updater: str
) -> InferenceModel:
    """Update a model, raising NotFoundException if not found."""
    model = await get_model(session, model_id, project_id)
    return await update_model(session, model, update_data, updater)


async def delete_model(session: AsyncSession, model_id: UUID, project_id: UUID, minio_client: MinioClient) -> None:
    """Delete a model, raising NotFoundException if not found or DeletionConflictException if ready."""
    model = await get_model(session, model_id, project_id)
    await delete_model_by_id(session, model_id, project_id)
    await delete_from_s3(model, minio_client)


async def delete_models(
    session: AsyncSession, ids: list[UUID], project_id: UUID, minio_client: MinioClient
) -> list[UUID]:
    """Delete multiple models by IDs, returning the list of actually deleted IDs."""
    models_list = await select_models(session, project_id=project_id, selected_model_ids=ids)
    model_map = {model.id: model for model in models_list}

    successfully_deleted_ids = set()
    exception_to_raise = None

    try:
        deleted_ids = await delete_models_by_ids(session, ids, project_id)
        successfully_deleted_ids = set(deleted_ids)
    except ExceptionGroup as eg:
        # Find out which models were actually deleted despite errors
        remaining_models = await select_models(session, project_id=project_id, selected_model_ids=ids)
        remaining_ids = {model.id for model in remaining_models}

        existing_ids = set(model_map.keys())
        successfully_deleted_ids = existing_ids - remaining_ids

        exception_to_raise = eg

    # Clean up S3 storage
    await asyncio.gather(
        *(
            delete_from_s3(model_map[model_id], minio_client)
            for model_id in successfully_deleted_ids
            if model_id in model_map
        ),
        return_exceptions=True,
    )

    if exception_to_raise:
        raise exception_to_raise

    return list(successfully_deleted_ids)


async def run_finetune_model_workload(
    session: AsyncSession,
    model_id: UUID | str,
    finetuning_data: FinetuneCreate,
    creator: str,
    token: str,
    project: Project,
    message_sender: MessageSender,
    display_name: str | None = None,
    hf_token_secret_name: str | None = None,
) -> ChartWorkloadResponse:
    """
    Finetune a model providing either just a canonical name or an existing model's UUID.
    In the first case the model will be downloaded automatically by the workload from HuggingFace.
    In the latter case, the model weights will be downloaded from the storage into the finetuning container.
    """

    if isinstance(model_id, UUID):
        model = await get_model(session, model_id, project.id)
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

    dataset = await select_dataset(session, dataset_id=finetuning_data.dataset_id, project_id=project.id)
    if not dataset:
        raise NotFoundException("Dataset not found")

    finetuning_path = get_finetuned_model_weights_path(model_canonical_name, finetuning_data.name, project.name)

    finetuned_model = await insert_model(
        session=session,
        name=finetuning_data.name,
        creator=creator,
        project_id=project.id,
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
    mlflow_workloads = await select_workloads(
        session=session,
        project_id=project.id,
        type=[WorkloadType.WORKSPACE],
        status=[WorkloadStatus.RUNNING],
        chart_name=MLFLOW_CHART_NAME,
    )

    if mlflow_workloads:
        mlflow_uri = mlflow_workloads[0].output["internal_host"]
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
        logger.info(f"Found running MLflow workspace for project {project.id} - URI: {mlflow_uri}")

    # All paths need to include the bucket prefix when accessed in the workload
    user_inputs = {
        "checkpointsRemote": os.path.join(MINIO_BUCKET, finetuning_path),  # this should not include "checkpoint-final"
        "basemodel": os.path.join(MINIO_BUCKET, model.model_weights_path) if model else f"hf://{model_canonical_name}",
        "finetuning_config": finetuning_config,
    }

    # Add HuggingFace token secret if provided
    if hf_token_secret_name:
        user_inputs["hfTokenSecret"] = {"name": hf_token_secret_name, "key": "token"}

    return await submit_chart_workload(
        session=session,
        creator=creator,
        token=token,
        project=project,
        chart=chart,
        overlays_values=overlay_values,
        user_inputs=user_inputs,
        message_sender=message_sender,
        model=finetuned_model,
        dataset=dataset,
        display_name=display_name,
    )


async def run_model_deployment(
    session: AsyncSession,
    model_id: UUID,
    creator: User,
    token: str,
    project: Project,
    message_sender: MessageSender,
    request: ModelDeployRequest | None = None,
    display_name: str | None = None,
) -> ChartWorkloadResponse:
    model = await get_model(session, model_id, project.id)

    # For deployment, model weights must already exist, so path should be present
    if not model.model_weights_path:
        raise ValidationException(
            f"Model {model_id} has no weights path. The model must be downloaded before deployment."
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

    # All paths need to include the bucket prefix when accessed in the workload
    user_inputs: dict = {
        **request_overrides,
        "model": format_model_path(os.path.join(MINIO_BUCKET, model.model_weights_path)),
        "metadata": {
            **chart.signature.get("metadata", {}),
            "project_id": str(project.id),
            "user_id": str(creator.id),
        },
    }

    return await submit_chart_workload(
        session=session,
        creator=creator.email,
        token=token,
        project=project,
        chart=chart,
        overlays_values=overlay_values,
        user_inputs=user_inputs,
        message_sender=message_sender,
        model=model,
        display_name=display_name,
    )
