# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from api_common.auth.security import get_user_email
from api_common.database import get_session
from api_common.exceptions import NotFoundException
from api_common.schemas import DeleteBatchRequest, ListResponse

from ..minio import MinioClient, get_minio_client
from ..namespaces.security import ensure_access_to_workbench_namespace
from .config import MAX_FILE_SIZE_MB
from .models import DatasetType
from .repository import list_datasets
from .schemas import DatasetResponse
from .service import create_and_upload_dataset, delete_datasets, download_dataset_file, get_dataset_by_id

router = APIRouter(prefix="/namespaces/{namespace}/datasets", tags=["Datasets"])


@router.post(
    "/upload",
    response_model=DatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a new training dataset",
    description=dedent(f"""
        Upload JSONL training data for AI/ML workloads. Requires namespace membership
        and healthy cluster. Automatically organizes files using namespace-based paths
        and ensures atomic operations (database + S3 storage).

        Maximum file size: {MAX_FILE_SIZE_MB}MB. Supports training, validation, and test
        dataset types for machine learning pipelines.
    """),
)
async def upload_dataset(
    name: str = Form(..., description="The name for the dataset"),
    description: str | None = Form(default=None, description="The description of the dataset"),
    type: DatasetType = Form(..., description="The type of the dataset"),
    jsonl: UploadFile = File(..., description="The JSONL file to upload"),
    author: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
) -> DatasetResponse:
    dataset = await create_and_upload_dataset(
        session=session,
        name=name,
        description=description,
        type=type,
        file=jsonl,
        author=author,
        namespace=namespace,
        minio_client=minio_client,
    )
    return DatasetResponse.model_validate(dataset)


@router.get(
    "",
    response_model=ListResponse[DatasetResponse],
    status_code=status.HTTP_200_OK,
    summary="List datasets in namespace",
    description=dedent("""
        List training datasets available in a namespace with optional filtering by type or name.
        Requires namespace membership. Essential for discovering available data for AI/ML
        workloads and training pipeline setup.
    """),
)
async def get_datasets(
    type: DatasetType | None = Query(None, description="Filter datasets by type (exact match)"),
    name: str | None = Query(None, description="Filter datasets by name (exact match)"),
    session: AsyncSession = Depends(get_session),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
) -> ListResponse[DatasetResponse]:
    datasets = await list_datasets(
        session=session,
        type=type,
        name=name,
        namespace=namespace,
    )
    return ListResponse(data=[DatasetResponse.model_validate(dataset) for dataset in datasets])


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dataset details",
    description=dedent("""
        Retrieve detailed information about a specific dataset including metadata,
        type, and S3 location. Requires namespace membership. Used for dataset
        inspection before training workload submission.
    """),
)
async def get_dataset(
    dataset_id: UUID,
    session: AsyncSession = Depends(get_session),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
) -> DatasetResponse:
    dataset = await get_dataset_by_id(session, dataset_id, namespace)
    return DatasetResponse.model_validate(dataset)


@router.get(
    "/{dataset_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download dataset file",
    description=dedent("""
        Download JSONL dataset file for local analysis or external processing.
        Requires namespace membership and healthy cluster status. Returns streaming
        response for large datasets. Essential for data inspection and offline workflows.
    """),
)
async def download_dataset(
    dataset_id: UUID,
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
) -> Response:
    return await download_dataset_file(dataset_id, namespace, session, minio_client)


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dataset",
    description=dedent("""
        Remove dataset from namespace including database record and S3 object cleanup.
        Requires namespace membership and healthy cluster. Irreversible operation -
        use with caution in production training environments.
    """),
)
async def delete_dataset(
    dataset_id: UUID,
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
) -> None:
    await delete_datasets(session, [dataset_id], namespace, minio_client)


@router.post(
    "/delete",
    status_code=status.HTTP_200_OK,
    summary="Bulk delete datasets",
    description=dedent("""
        Atomic bulk deletion of multiple datasets from namespace. Requires namespace
        membership and healthy cluster. All-or-nothing operation ensures data
        consistency - fails completely if any dataset ID is invalid.
    """),
)
async def batch_delete_datasets(
    data: DeleteBatchRequest,
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
) -> list[UUID]:
    deleted_ids = await delete_datasets(
        session=session, dataset_ids=data.ids, namespace=namespace, minio_client=minio_client
    )
    missing_ids = set(data.ids) - set(deleted_ids)
    if missing_ids:
        raise NotFoundException(f"Datasets with IDs {list(missing_ids)} not found in this namespace")
    return deleted_ids
