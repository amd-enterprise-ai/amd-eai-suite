# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..managed_workloads.schemas import ChartWorkloadResponse
from ..secrets.service import resolve_hf_token_reference
from ..utilities.checks import ensure_cluster_healthy
from ..utilities.database import get_session
from ..utilities.minio import get_minio_client
from ..utilities.security import BearerToken, get_user, get_user_email, validate_and_get_project_from_query
from .models import OnboardingStatus
from .schemas import (
    DeleteModelsBatchRequest,
    FinetunableModelsResponse,
    FinetuneCreate,
    ModelDeployRequest,
    ModelEdit,
    ModelResponse,
)
from .service import (
    delete_model,
    delete_models,
    get_finetunable_models,
    get_model,
    list_models,
    run_finetune_model_workload,
    run_model_deployment,
    update_model_by_id,
    update_onboarding_statuses,
)

router = APIRouter(prefix="/models", tags=["Models"])


@router.get(
    "",
    response_model=list[ModelResponse],
    status_code=status.HTTP_200_OK,
    summary="List available models with filtering.",
    description="""
    List all the models available in the project with filtering by type, onboarding status, name.
    """,
)
async def get_models(
    onboarding_status: OnboardingStatus | None = Query(None, description="Filter by onboarding status"),
    name: str | None = Query(None, description="Filter by name (exact match)"),
    project=Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
) -> list[ModelResponse]:
    await update_onboarding_statuses(session, project.id)
    return await list_models(
        session=session,
        onboarding_status=onboarding_status,
        name=name,
        project_id=project.id,
    )


@router.get(
    "/finetunable",
    response_model=FinetunableModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="List available finetunable models.",
    description="""List the canonical names of all the finetunable models.""",
)
async def get_finetunable_models_endpoint(session: AsyncSession = Depends(get_session)) -> FinetunableModelsResponse:
    models = await get_finetunable_models(session)
    return FinetunableModelsResponse(models=models)


@router.get(
    "/{model_id}",
    response_model=ModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific model by ID.",
    description="Get detailed information about a specific model by ID.",
)
async def get_model_endpoint(
    model_id: UUID,
    project=Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
) -> ModelResponse:
    await update_onboarding_statuses(session, project.id)
    return await get_model(session, model_id, project.id)


@router.put(
    "/{model_id}",
    response_model=ModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing model",
    description="Allows partially updating a model with the provided fields. Only the provided fields will be updated; others remain unchanged.",
)
async def modify_model(
    model_id: UUID,
    model: ModelEdit,
    project=Depends(validate_and_get_project_from_query),
    user=Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
) -> ModelResponse:
    await update_onboarding_statuses(session, project.id)
    return await update_model_by_id(session, model_id, project.id, model, user)


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a model",
    description="Deletes a model by ID.",
)
async def delete_single_model(
    model_id: UUID,
    project=Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
    minio_client=Depends(get_minio_client),
):
    ensure_cluster_healthy(project)
    await delete_model(session, model_id, project.id, minio_client=minio_client)


@router.post(
    "/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete multiple models by their IDs",
    description="Deletes multiple models by their IDs. If some IDs do not exist, the request fails.",
)
async def batch_delete_models(
    data: DeleteModelsBatchRequest,
    project=Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
    minio_client=Depends(get_minio_client),
):
    ensure_cluster_healthy(project)
    deleted_ids = await delete_models(session=session, ids=data.ids, project_id=project.id, minio_client=minio_client)
    return deleted_ids


@router.post(
    "/{model_id:path}/finetune",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ChartWorkloadResponse,
    summary="Finetune an existing model",
    description="Finetunes a huggingface model or an existing model using the provided training data.",
)
async def finetune_model(
    model_id: UUID | str,
    finetuning_data: FinetuneCreate,
    project=Depends(validate_and_get_project_from_query),
    display_name: str | None = Query(None, description="User-friendly display name for the workload"),
    token: str = Depends(BearerToken),
    author=Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
):
    ensure_cluster_healthy(project)

    # Convert string to UUID if valid, otherwise keep as string
    try:
        model_id = UUID(model_id) if isinstance(model_id, str) else model_id
    except ValueError:
        pass

    hf_secret_name = None

    if finetuning_data.hf_token_secret_id:
        resolved = await resolve_hf_token_reference(
            session=session,
            project=project,
            token_secret_id=finetuning_data.hf_token_secret_id,
        )
        hf_secret_name = resolved.name

    workload = await run_finetune_model_workload(
        session=session,
        model_id=model_id,
        finetuning_data=finetuning_data,
        project=project,
        creator=author,
        token=token,
        display_name=display_name,
        hf_token_secret_name=hf_secret_name,
    )
    return workload


@router.post(
    "/{model_id}/deploy",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="deploy_model",
    response_model=ChartWorkloadResponse,
    summary="Deploy a model for inference",
    description="Creates a deployment workload that runs the model in inference mode.",
)
async def deploy_model(
    model_id: UUID,
    request: ModelDeployRequest | None = None,
    project=Depends(validate_and_get_project_from_query),
    display_name: str | None = Query(None, description="User-friendly display name for the workload"),
    token: str = Depends(BearerToken),
    author=Depends(get_user),
    session: AsyncSession = Depends(get_session),
) -> ChartWorkloadResponse:
    ensure_cluster_healthy(project)

    return await run_model_deployment(
        session=session,
        model_id=model_id,
        creator=author,
        token=token,
        project=project,
        request=request,
        display_name=display_name,
    )
