# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from uuid import UUID, uuid4

from fastapi import Response, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..projects.models import Project
from ..utilities.exceptions import (
    ConflictException,
    NotFoundException,
    UploadFailedException,
    ValidationException,
)
from .models import Dataset
from .repository import delete_datasets as delete_datasets_by_ids
from .repository import insert_dataset as insert_dataset_in_db
from .repository import (
    list_datasets,
    select_dataset,
    update_dataset,
)
from .schemas import DatasetCreate, DatasetEdit, DatasetType
from .utils import (
    MinioClient,
    clean_s3_path,
    delete_from_s3,
    derive_name_from_path,
    download_from_s3,
    get_object_key,
    sync_dataset_to_s3,
    validate_jsonl,
)


async def insert_dataset(
    session: AsyncSession,
    dataset: DatasetCreate,
    project_id: UUID,
    creator: str,
) -> Dataset:
    """
    Register an existing dataset at a given S3 path.
    The name will be derived from the path.

    Args:
        session: Database session
        dataset: The dataset creation parameters
        project_id: The project ID to associate with the dataset
        creator: The email of the user creating the dataset

    Returns:
        The newly created dataset object

    Raises:
        NotFoundException: If the project is not found
        ConflictException: If a dataset with the same path or derived name already exists
    """
    # Clean and validate the provided path
    cleaned_path = clean_s3_path(dataset.path)
    derived_name = derive_name_from_path(cleaned_path)

    # Prepare parameters for database insertion
    params = dataset.model_dump()
    params["creator"] = creator
    params["project_id"] = project_id
    params["path"] = cleaned_path
    params["name"] = derived_name

    return await insert_dataset_in_db(session, **params)


async def create_and_upload_dataset(
    session: AsyncSession,
    name: str,
    description: str | None,
    type: DatasetType,
    file: UploadFile,
    author: str,
    project: Project,
    minio_client: MinioClient,
) -> Dataset:
    """
    Create a new dataset with user-provided name and upload its content.
    The path will be generated based on the name and project name using a slug format.

    This function implements a two-phase process:
    1. Create a database record with a generated path
    2. Upload the file to S3 at that path

    If either step fails, the entire transaction is rolled back by the API layer.

    Args:
        session: Database session
        name: User-provided name for the dataset
        description: Optional description of the dataset
        type: The type of dataset
        file: The JSONL file to upload
        author: The email of the user creating the dataset
        project: The project to associate with the dataset

    Raises:
        ValidationException: If validation fails
        NotFoundException: If the project is not found
        ConflictException: If a dataset with the same name exists
        UploadFailedException: If there are issues with S3 upload
    """
    try:
        # Validate the file first to avoid unnecessary database operations if validation fails
        validate_jsonl(file)
    except Exception as e:
        # Handle validation errors
        logger.error(f"Validation error for dataset {name}: {e}")
        raise ValidationException(
            message="Failed to validate dataset file, please ensure it is a valid JSONL file with the correct format.",
            detail=str(e),
        )

    dataset_db = None

    try:
        # Generate a new UUID for the dataset
        dataset_id = uuid4()

        # Generate the S3 object key using the project name (not ID)
        object_key = get_object_key(name, project.name)

        # Create the dataset record with the generated path
        dataset_db = await insert_dataset_in_db(
            session,
            id=dataset_id,
            name=name,
            creator=author,
            description=description,
            project_id=project.id,
            type=type,
            path=object_key,
        )

        # Ensure the dataset record is created
        await session.flush()

        # Upload the file to S3
        try:
            await file.seek(0)
            await sync_dataset_to_s3(dataset_db, file, minio_client)

        except Exception as e:
            logger.error(f"Failed to upload dataset file for {name} (ID: {dataset_db.id}): {e}")
            raise UploadFailedException(
                message="Failed to upload dataset file to storage",
                detail=str(e),
            )

        return dataset_db

    except (ValidationException, NotFoundException, ConflictException, UploadFailedException):
        # Re-raise known domain exceptions as is without wrapping them
        raise

    except Exception as e:
        # For any other unexpected exceptions
        logger.error(f"Failed to insert dataset record for {name}: {e}")
        raise UploadFailedException(
            message="Failed to create dataset record in database.",
            detail=str(e),
        )


async def download_dataset_file(
    dataset_id: UUID, project_id: UUID, session: AsyncSession, minio_client: MinioClient
) -> Response:
    """
    Download a dataset file from S3 storage and return it as a response.

    Args:
        dataset_id: The UUID of the dataset to download
        project_id: The project ID associated with the dataset
        session: Database session

    Returns:
        A Response object containing the dataset file

    Raises:
        NotFoundException: If the dataset is not found or has no content
    """
    dataset = await select_dataset(session, dataset_id, project_id)
    if not dataset:
        raise NotFoundException(message=f"Dataset {dataset_id} not found")

    # Check if the dataset has content uploaded (i.e., a path is set)
    if not dataset.path:
        raise NotFoundException(message=f"Dataset {dataset_id} has no content to download.")

    file_name, content = await download_from_s3(dataset, minio_client)

    return Response(
        content=content,
        media_type="application/jsonlines",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Type": "application/jsonl; charset=utf-8",
        },
    )


async def get_dataset_by_id(session: AsyncSession, dataset_id: UUID, project_id: UUID) -> Dataset:
    """Get a dataset by ID, raising NotFoundException if not found."""
    dataset = await select_dataset(session, dataset_id, project_id)
    if not dataset:
        raise NotFoundException(f"Dataset with ID {dataset_id} not found in this project")
    return dataset


async def update_dataset_by_id(
    session: AsyncSession, dataset_id: UUID, project_id: UUID, update_data: DatasetEdit, updater: str
) -> Dataset:
    """Update a dataset, raising NotFoundException if not found."""
    dataset = await update_dataset(session, dataset_id, update_data, project_id, updater)
    if not dataset:
        raise NotFoundException(f"Dataset with ID {dataset_id} not found in this project")
    return dataset


async def delete_datasets(
    session: AsyncSession, dataset_ids: list[UUID], project_id: UUID, minio_client: MinioClient
) -> list[UUID]:
    """Delete datasets from database and S3 storage."""
    datasets = await list_datasets(session, project_id, selected_datasets_ids=dataset_ids)
    existing_ids = [ds.id for ds in datasets]

    # Delete from database first (will be rolled back if S3 operations fail)
    await delete_datasets_by_ids(session, existing_ids, project_id)

    # Delete from S3 storage
    await asyncio.gather(*(delete_from_s3(ds, minio_client) for ds in datasets), return_exceptions=True)

    return existing_ids
