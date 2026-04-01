# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_email
from api_common.database import get_session
from api_common.schemas import ListResponse

from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..minio import MinioClient, get_minio_client
from ..namespaces.security import ensure_access_to_workbench_namespace
from .models import OnboardingStatus
from .schemas import FinetuneCreate, ModelDeployRequest, ModelResponse
from .service import (
    delete_model,
    get_finetunable_models,
    get_model,
    list_models,
    run_finetune_model_workload,
    run_model_deployment,
)

router = APIRouter(tags=["Models"])


@router.get(
    "/finetunable",
    response_model=ListResponse[str],
    status_code=status.HTTP_200_OK,
    summary="List available finetunable models.",
    description=dedent("""List the canonical names of all the finetunable models."""),
)
async def get_finetunable_models_endpoint(session: AsyncSession = Depends(get_session)) -> ListResponse[str]:
    models = await get_finetunable_models(session)
    return ListResponse(data=models)


@router.get(
    "/namespaces/{namespace}/models",
    response_model=ListResponse[ModelResponse],
    status_code=status.HTTP_200_OK,
    summary="List available models",
    description="List all fine-tuned models in a namespace with optional filtering",
)
async def get_models(
    onboarding_status: OnboardingStatus | None = Query(None, description="Filter by onboarding status"),
    name: str | None = Query(None, description="Filter by name (exact match)"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
) -> ListResponse[ModelResponse]:
    models = await list_models(
        session=session,
        onboarding_status=onboarding_status,
        name=name,
        namespace=namespace,
    )
    return ListResponse(data=models)


@router.get(
    "/namespaces/{namespace}/models/{model_id}",
    response_model=ModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific model by ID",
    description="Get detailed information about a specific model",
)
async def get_model_endpoint(
    model_id: UUID = Path(..., description="Model ID"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
) -> ModelResponse:
    return await get_model(session, model_id, namespace)


@router.delete(
    "/namespaces/{namespace}/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a model",
    description="Delete a model by ID",
)
async def delete_single_model(
    model_id: UUID = Path(..., description="Model ID"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
) -> None:
    await delete_model(session, model_id, namespace, minio_client=minio_client)


@router.post(
    "/namespaces/{namespace}/models/{model_id:path}/finetune",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ModelResponse,
    summary="Finetune a model",
    description="Finetune a huggingface model or an existing model using training data",
)
async def finetune_model(
    model_id: UUID | str = Path(..., description="Model ID or canonical name"),
    display_name: str | None = Query(None, description="User-friendly display name for the workload"),
    finetuning_data: FinetuneCreate = Body(...),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    submitter: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ModelResponse:
    return await run_finetune_model_workload(
        session=session,
        kube_client=kube_client,
        model_id=model_id,
        finetuning_data=finetuning_data,
        namespace=namespace,
        submitter=submitter,
        display_name=display_name,
    )


@router.post(
    "/namespaces/{namespace}/models/{model_id}/deploy",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="deploy_model",
    response_model=ModelResponse,
    summary="Deploy a model for inference",
    description="Create a deployment workload that runs the model in inference mode",
)
async def deploy_model(
    model_id: UUID = Path(..., description="Model ID"),
    display_name: str | None = Query(None, description="User-friendly display name for the workload"),
    request: ModelDeployRequest | None = None,
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    submitter: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ModelResponse:
    return await run_model_deployment(
        session=session,
        kube_client=kube_client,
        model_id=model_id,
        submitter=submitter,
        namespace=namespace,
        request=request,
        display_name=display_name,
    )
