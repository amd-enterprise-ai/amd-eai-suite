# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_email
from api_common.database import get_session
from api_common.schemas import ListResponse, QueryParam

from ..aims.crds import AIMModelResource
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..minio import MinioClient, get_minio_client
from ..namespaces.security import ensure_access_to_workbench_namespace
from ..workloads.schemas import DisplayNameQuery
from .schemas import FinetunableModelResponse, FinetuneCreate, FinetuneJobResponse
from .service import (
    delete_model,
    get_aim_model,
    get_finetunable_models,
    list_aim_models,
    run_finetune_model_workload,
)

router = APIRouter(tags=["Models"])


@router.get(
    "/finetunable",
    response_model=ListResponse[FinetunableModelResponse],
    status_code=status.HTTP_200_OK,
    summary="List available finetunable models.",
    description=dedent("""List finetunable models compatible with the cluster's current GPU hardware."""),
)
async def get_finetunable_models_endpoint(
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[FinetunableModelResponse]:
    models = await get_finetunable_models(session, kube_client)
    return ListResponse(data=models)


@router.get(
    "/namespaces/{namespace}/aims/models",
    response_model=ListResponse[AIMModelResource],
    status_code=status.HTTP_200_OK,
    summary="List available models",
    description="List all fine-tuned models in a namespace (completed AIMModel CRs)",
)
async def get_models(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[AIMModelResource]:
    models = await list_aim_models(
        kube_client=kube_client,
        namespace=namespace,
    )
    return ListResponse(data=models)


@router.get(
    "/namespaces/{namespace}/aims/models/{resource_name}",
    response_model=AIMModelResource,
    status_code=status.HTTP_200_OK,
    summary="Get a specific AIMModel by resource name",
    description="Get an AIMModel CR from Kubernetes by its resource name or model ID label",
)
async def get_model_endpoint(
    resource_name: str = Path(..., description="AIMModel CR resource name or model UUID"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> AIMModelResource:
    return await get_aim_model(kube_client, namespace, resource_name)


@router.delete(
    "/namespaces/{namespace}/aims/models/{resource_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a model",
    description="Delete a fine-tuned model's AIMModel CR and S3 weights. "
    "Returns 409 if active deployments exist; pass force=true to proceed anyway.",
)
async def delete_single_model(
    resource_name: str = Path(..., description="AIMModel CR name"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
    minio_client: MinioClient = Depends(get_minio_client),
    session: AsyncSession = Depends(get_session),
    force: bool = Query(False, description="Delete even if active deployments exist"),
) -> None:
    await delete_model(kube_client, resource_name, namespace, minio_client=minio_client, force=force, session=session)


@router.post(
    "/namespaces/{namespace}/models/{model_id:path}/finetune",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=FinetuneJobResponse,
    summary="Finetune a model",
    description="Finetune a huggingface model or an existing model using training data",
)
async def finetune_model(
    query: QueryParam[DisplayNameQuery],
    model_id: UUID | str = Path(..., description="Model ID or canonical name"),
    finetuning_data: FinetuneCreate = Body(...),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    submitter: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> FinetuneJobResponse:
    return await run_finetune_model_workload(
        session=session,
        kube_client=kube_client,
        model_id=model_id,
        finetuning_data=finetuning_data,
        namespace=namespace,
        submitter=submitter,
        display_name=query.display_name,
    )
