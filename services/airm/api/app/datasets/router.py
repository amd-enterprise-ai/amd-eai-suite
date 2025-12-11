# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from ..projects.models import Project
from ..utilities.checks import ensure_cluster_healthy
from ..utilities.config import MAX_FILE_SIZE_MB
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException
from ..utilities.minio import MinioClient, get_minio_client
from ..utilities.schema import DeleteOverlaysBatchRequest
from ..utilities.security import get_user_email, validate_and_get_project_from_query
from .models import DatasetType
from .repository import list_datasets
from .schemas import DatasetCreate, DatasetEdit, DatasetResponse, DatasetsResponse
from .service import (
    create_and_upload_dataset,
    delete_datasets,
    download_dataset_file,
    get_dataset_by_id,
    insert_dataset,
    update_dataset_by_id,
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post(
    "",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an existing dataset from S3",
    description="""
        Register an existing JSONL dataset from S3 storage for AI/ML training workflows.
        Requires project membership and healthy cluster status. Links pre-existing S3 objects
        to the dataset management system without uploading new files.

        Automatically derives user-friendly names from S3 paths. Essential for workflows
        where datasets are created externally or through data pipelines.
    """,
)
async def create_dataset(
    dataset: DatasetCreate,
    project: Project = Depends(validate_and_get_project_from_query),
    creator: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
) -> DatasetResponse:
    created_dataset = await insert_dataset(
        session=session,
        dataset=dataset,
        project_id=project.id,
        creator=creator,
    )
    return DatasetResponse.model_validate(created_dataset)


@router.post(
    "/upload",
    response_model=DatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a new training dataset",
    description=f"""
        Upload JSONL training data for AI/ML workloads. Requires project membership
        and healthy cluster. Automatically organizes files using project-based paths
        and ensures atomic operations (database + S3 storage).

        Maximum file size: {MAX_FILE_SIZE_MB}MB. Supports training, validation, and test
        dataset types for machine learning pipelines.
    """,
)
async def upload_dataset(
    name: str = Form(..., description="The name for the dataset"),
    description: str | None = Form(..., description="The description of the dataset"),
    type: DatasetType = Form(..., description="The type of the dataset"),
    jsonl: UploadFile = File(..., description="The JSONL file to upload"),
    project: Project = Depends(validate_and_get_project_from_query),
    author: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
) -> DatasetResponse:
    ensure_cluster_healthy(project)

    dataset = await create_and_upload_dataset(
        session=session,
        name=name,
        description=description,
        type=type,
        file=jsonl,
        author=author,
        project=project,
        minio_client=minio_client,
    )
    return DatasetResponse.model_validate(dataset)


@router.get(
    "",
    response_model=DatasetsResponse,
    status_code=status.HTTP_200_OK,
    summary="List datasets in project",
    description="""
        List training datasets available in a project with optional filtering by type or name.
        Requires project membership. Essential for discovering available data for AI/ML
        workloads and training pipeline setup.
    """,
)
async def get_datasets(
    type: DatasetType | None = Query(None, description="Filter datasets by type (exact match)"),
    name: str | None = Query(None, description="Filter datasets by name (exact match)"),
    project: Project = Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
) -> DatasetsResponse:
    datasets = await list_datasets(
        session=session,
        type=type,
        name=name,
        project_id=project.id,
    )
    return DatasetsResponse(data=[DatasetResponse.model_validate(dataset) for dataset in datasets])


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dataset details",
    description="""
        Retrieve detailed information about a specific dataset including metadata,
        type, and S3 location. Requires project membership. Used for dataset
        inspection before training workload submission.
    """,
)
async def get_dataset(
    dataset_id: UUID,
    project: Project = Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
) -> DatasetResponse:
    dataset = await get_dataset_by_id(session, dataset_id, project.id)
    return DatasetResponse.model_validate(dataset)


@router.put(
    "/{dataset_id}",
    response_model=DatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Update dataset metadata",
    description="""
        Update dataset description and type classification. Requires project membership.
        Dataset name and S3 path remain immutable for consistency across training workflows.
        Useful for refining dataset categorization and documentation.
    """,
)
async def modify_dataset(
    dataset_id: UUID,
    dataset: DatasetEdit,
    project: Project = Depends(validate_and_get_project_from_query),
    updater: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
) -> DatasetResponse:
    updated_dataset = await update_dataset_by_id(session, dataset_id, project.id, dataset, updater)
    return DatasetResponse.model_validate(updated_dataset)


@router.get(
    "/{dataset_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download dataset file",
    description="""
        Download JSONL dataset file for local analysis or external processing.
        Requires project membership and healthy cluster status. Returns streaming
        response for large datasets. Essential for data inspection and offline workflows.
    """,
)
async def download_dataset(
    dataset_id: UUID,
    project: Project = Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
) -> Response:
    ensure_cluster_healthy(project)

    return await download_dataset_file(dataset_id, project.id, session, minio_client)


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dataset",
    description="""
        Remove dataset from project including database record and S3 object cleanup.
        Requires project membership and healthy cluster. Irreversible operation -
        use with caution in production training environments.
    """,
)
async def delete_dataset(
    dataset_id: UUID,
    project: Project = Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
) -> None:
    ensure_cluster_healthy(project)
    await delete_datasets(session, [dataset_id], project.id, minio_client)


@router.post(
    "/delete",
    status_code=status.HTTP_200_OK,
    summary="Bulk delete datasets",
    description="""
        Atomic bulk deletion of multiple datasets from project. Requires project
        membership and healthy cluster. All-or-nothing operation ensures data
        consistency - fails completely if any dataset ID is invalid.
    """,
)
async def batch_delete_datasets(
    data: DeleteOverlaysBatchRequest,
    project: Project = Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
    minio_client: MinioClient = Depends(get_minio_client),
) -> list[UUID]:
    ensure_cluster_healthy(project)
    deleted_ids = await delete_datasets(
        session=session, dataset_ids=data.ids, project_id=project.id, minio_client=minio_client
    )
    missing_ids = set(data.ids) - set(deleted_ids)
    if missing_ids:
        raise NotFoundException(f"Datasets with IDs {list(missing_ids)} not found in this project")
    return deleted_ids
