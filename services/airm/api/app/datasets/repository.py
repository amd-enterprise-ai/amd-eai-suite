# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..utilities.exceptions import ConflictException
from ..utilities.models import set_updated_fields
from .models import Dataset, DatasetType
from .schemas import DatasetEdit


async def insert_dataset(
    session: AsyncSession,
    name: str,
    creator: str,
    description: str | None,
    project_id: UUID,
    type: DatasetType,
    path: str,
    id: UUID = None,
) -> Dataset:
    """
    Insert a new dataset record into the database.

    Args:
        session: Database session for the transaction
        name: Dataset name (must be unique within project)
        creator: Email of the user creating the dataset
        description: Optional description text (defaults to empty string if None)
        project_id: UUID of the project containing the dataset
        type: DatasetType enum value (e.g., FINETUNE)
        path: S3 path where dataset content is stored (must be globally unique)
        id: Optional UUID to use for the dataset (auto-generated if None)

    Raises:
        ConflictException: If a dataset with the same path or name already exists in the project
    """
    dataset = Dataset(
        id=id,
        name=name,
        created_by=creator,
        updated_by=creator,
        path=path,
        description=description or "",
        project_id=project_id,
        type=type,
    )
    session.add(dataset)
    try:
        await session.flush()
        await session.refresh(dataset)
        return dataset
    except IntegrityError as e:
        error_message = str(e)
        if "datasets_path_key" in error_message:
            raise ConflictException(
                message=f"A dataset with path {path} already exists",
            )
        elif "datasets_name_project_id_key" in error_message:
            raise ConflictException(
                message=f"A dataset with name '{name}' already exists in this project",
            )
        elif "datasets_project_id_fkey" in error_message:
            raise ConflictException(
                message=f"Project with ID {project_id} not found.",
            )
        raise e


async def select_dataset(
    session: AsyncSession,
    dataset_id: UUID,
    project_id: UUID,
) -> Dataset | None:
    """
    Retrieve a dataset by ID within a specific project.

    Args:
        session: Database session for the query
        dataset_id: UUID of the dataset to retrieve
        project_id: UUID of the project (for scoping and authorization)

    Returns:
        Dataset object if found, None otherwise
    """
    query = select(Dataset).where(Dataset.id == dataset_id, Dataset.project_id == project_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_datasets(
    session: AsyncSession,
    project_id: UUID,
    selected_datasets_ids: list[UUID] | None = None,
    type: DatasetType | None = None,
    name: str | None = None,
) -> list[Dataset]:
    """
    List datasets in a project with optional filtering.

    Args:
        session: Database session for the query
        project_id: UUID of the project to filter datasets by
        selected_datasets_ids: Optional list of specific dataset UUIDs to retrieve
        type: Optional DatasetType enum to filter by (e.g., DatasetType.FINETUNE)
        name: Optional exact name match filter

    Returns:
        List of Dataset objects matching the criteria
    """
    query = select(Dataset).where(Dataset.project_id == project_id)
    if selected_datasets_ids:
        query = query.where(Dataset.id.in_(selected_datasets_ids))
    if type:
        query = query.where(Dataset.type == type)
    if name:
        query = query.where(Dataset.name == name)
    result = await session.execute(query)
    return result.scalars().all()


async def update_dataset(
    session: AsyncSession,
    dataset_id: UUID,
    update_data: DatasetEdit,
    project_id: UUID,
    updater: str,
) -> Dataset | None:
    """
    Update a dataset with only the provided fields, ensuring name and path remain immutable.

    Args:
        session: Database session for the transaction
        dataset_id: UUID of the dataset to update
        update_data: DatasetEdit schema containing the fields to update
        project_id: UUID of the project (for scoping and authorization)
        updater: Email of the user performing the update

    Returns:
        Updated Dataset object if found, None if dataset doesn't exist

    Note:
        name, path, and type fields are immutable and excluded from updates.
        Only description and other mutable fields can be updated.
    """
    dataset = await select_dataset(session, dataset_id, project_id)

    if not dataset:
        return None

    # Convert Pydantic dataset to dict, excluding None values and immutable fields
    update_dict = update_data.model_dump(exclude_unset=True, exclude={"type", "name", "path"})

    # Update dataset attributes
    for field, value in update_dict.items():
        setattr(dataset, field, value)

    set_updated_fields(dataset, updater)
    await session.flush()
    return dataset


async def delete_dataset_by_id(session: AsyncSession, dataset_id: UUID, project_id: UUID) -> bool:
    """
    Delete a single dataset by ID within a project.

    Args:
        session: Database session for the transaction
        dataset_id: UUID of the dataset to delete
        project_id: UUID of the project (for scoping and authorization)

    Returns:
        True if dataset was found and deleted, False if not found

    Note:
        Only deletes from database - S3 cleanup must be handled separately by the service layer.
    """
    dataset = await select_dataset(session, dataset_id, project_id)

    if not dataset:
        return False

    await session.delete(dataset)
    await session.flush()
    return True


async def delete_datasets(session: AsyncSession, existing_ids: list[UUID], project_id: UUID) -> list[UUID]:
    """
    Delete multiple datasets by IDs within a project.

    Args:
        session: Database session for the transaction
        existing_ids: List of dataset UUIDs to delete
        project_id: UUID of the project (for scoping and authorization)

    Returns:
        List of UUIDs that were actually found and deleted

    Note:
        Only deletes from database - S3 cleanup must be handled separately by the service layer.
        Performs verification to ensure only existing datasets in the project are deleted.
    """
    if not existing_ids:
        return []

    # First, get the existing dataset IDs that match our criteria
    existing_query = select(Dataset.id).where(Dataset.id.in_(existing_ids), Dataset.project_id == project_id)
    result = await session.execute(existing_query)
    existing_dataset_ids = [row[0] for row in result.fetchall()]

    if not existing_dataset_ids:
        return []

    # Now delete the datasets
    query = delete(Dataset).where(Dataset.id.in_(existing_dataset_ids), Dataset.project_id == project_id)
    await session.execute(query)
    await session.flush()

    return existing_dataset_ids
