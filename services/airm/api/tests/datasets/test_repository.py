# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.models import DatasetType
from app.datasets.repository import (
    delete_dataset_by_id,
    delete_datasets,
    insert_dataset,
    list_datasets,
    select_dataset,
    update_dataset,
)
from app.datasets.schemas import DatasetEdit
from app.utilities.exceptions import ConflictException
from tests import factory


async def test_insert_dataset(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id
    creator = env.creator

    dataset = await insert_dataset(
        db_session,
        name="Test Dataset",
        creator=creator,
        description="Test description",
        project_id=project_id,
        type=DatasetType.FINETUNING,
        path="datasets/test",
    )

    assert dataset.id is not None
    assert dataset.name == "Test Dataset"
    assert dataset.description == "Test description"
    assert dataset.path == "datasets/test"
    assert dataset.created_by == creator
    assert dataset.project_id == project_id
    assert dataset.type == DatasetType.FINETUNING

    specific_id = uuid4()
    dataset2 = await insert_dataset(
        db_session,
        id=specific_id,
        name="Test Dataset 2",
        creator=creator,
        description="Test description 2",
        project_id=project_id,
        type=DatasetType.FINETUNING,
        path="datasets/test2",
    )

    assert dataset2.id == specific_id
    assert dataset2.name == "Test Dataset 2"


@pytest.mark.asyncio
async def test_update_dataset(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id
    creator = env.creator

    dataset = await insert_dataset(
        db_session,
        name="Original Name",
        creator=creator,
        description="Original description",
        project_id=project_id,
        type=DatasetType.FINETUNING,
        path="datasets/original",
    )

    # Update the dataset with only the description field
    # Note that name and path fields should be immutable (excluded from DatasetEdit)
    updated_dataset = await update_dataset(
        db_session,
        dataset.id,
        DatasetEdit(
            description="Updated description",
            # name and path should be excluded from the schema
        ),
        project_id=project_id,
        updater="updater@example.com",
    )

    # Verify the update - only description should change
    assert updated_dataset.id == dataset.id
    assert updated_dataset.name == "Original Name"  # Name should remain unchanged
    assert updated_dataset.description == "Updated description"
    assert updated_dataset.path == "datasets/original"  # Path should remain unchanged
    assert updated_dataset.created_by == creator
    assert updated_dataset.updated_by == "updater@example.com"


@pytest.mark.asyncio
async def test_delete_dataset(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id
    creator = env.creator

    dataset = await insert_dataset(
        db_session,
        name="Test Dataset",
        creator=creator,
        description="Test description",
        project_id=project_id,
        type=DatasetType.FINETUNING,
        path="datasets/test",
    )

    await delete_dataset_by_id(db_session, dataset.id, project_id)

    # Try to retrieve the deleted dataset
    retrieved_dataset = await select_dataset(db_session, dataset.id, project_id)
    assert retrieved_dataset is None


@pytest.mark.asyncio
async def test_list_models(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id
    creator = env.creator

    # Create multiple datasets
    datasets = []
    for i in range(5):
        dataset = await insert_dataset(
            db_session,
            name=f"Dataset {i}",
            creator=creator,
            description=f"Description {i}",
            project_id=project_id,
            type=DatasetType.FINETUNING,
            path=f"datasets/test{i}",
        )
        datasets.append(dataset)

    # List all datasets
    all_datasets = await list_datasets(db_session, project_id)
    assert len(all_datasets) == 5

    # List datasets of a specific type
    finetuning_datasets = await list_datasets(db_session, project_id, type=DatasetType.FINETUNING)
    assert len(finetuning_datasets) == 5

    # List datasets with a specific name
    specific_dataset = await list_datasets(db_session, project_id, name="Dataset 3")
    assert len(specific_dataset) == 1
    assert specific_dataset[0].name == "Dataset 3"

    # List datasets by selected IDs
    selected_ids = [datasets[1].id, datasets[3].id]
    selected_datasets = await list_datasets(db_session, project_id, selected_datasets_ids=selected_ids)
    assert len(selected_datasets) == 2
    returned_ids = {d.id for d in selected_datasets}
    assert set(selected_ids) == returned_ids


@pytest.mark.asyncio
async def test_delete_datasets(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id
    creator = env.creator

    # Create multiple datasets
    dataset_ids = []
    for i in range(10):
        dataset = await insert_dataset(
            db_session,
            name=f"Dataset {i}",
            creator=creator,
            description=f"Description {i}",
            project_id=project_id,
            type=DatasetType.FINETUNING,
            path=f"datasets/test{i}",
        )
        dataset_ids.append(dataset.id)

    await delete_datasets(db_session, dataset_ids, project_id)

    # Try to list datasets
    all_datasets = await list_datasets(db_session, project_id)
    assert len(all_datasets) == 0


@pytest.mark.asyncio
async def test_delete_datasets_with_wrong_ids(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id

    # Try to delete with wrong IDs - should return empty list, not raise exception
    wrong_ids = [uuid4() for _ in range(2)]
    deleted_ids = await delete_datasets(db_session, wrong_ids, project_id)
    assert deleted_ids == []


@pytest.mark.asyncio
async def test_unique_constraints(db_session: AsyncSession):
    """Test the unique constraints on dataset name and path"""
    env = await factory.create_basic_test_environment(db_session)
    project_id = env.project.id
    creator = env.creator

    # Create first dataset
    dataset1 = await insert_dataset(
        db_session,
        name="Unique Dataset",
        creator=creator,
        description="Test description",
        project_id=project_id,
        type=DatasetType.FINETUNING,
        path="datasets/unique-path",
    )

    # Since we're expecting IntegrityErrors, we need to handle them properly
    # and rollback the session after each failed attempt

    # Test 1: Try to create dataset with same name in same scope
    try:
        await insert_dataset(
            db_session,
            name="Unique Dataset",  # Same name
            creator=creator,
            description="Another description",
            # Same cluster
            project_id=project_id,  # Same project
            type=DatasetType.FINETUNING,
            path="datasets/different-path",
        )
        assert False, "Expected ConflictException for duplicate name was not raised"
    except ConflictException:
        # This is expected, rollback the transaction
        await db_session.rollback()

    # Test 2: Try to create dataset with same path (should be globally unique)
    try:
        await insert_dataset(
            db_session,
            name="Different Dataset Name",
            creator=creator,
            description="Another description",
            project_id=project_id,  # Same project
            type=DatasetType.FINETUNING,
            path="datasets/unique-path",  # Same path
        )
        assert False, "Expected ConflictException for duplicate path was not raised"
    except ConflictException:
        # This is expected, rollback the transaction
        await db_session.rollback()

    # Test 3: Check case insensitivity for name uniqueness
    try:
        await insert_dataset(
            db_session,
            name="UNIQUE dataset",  # Same name but different case
            creator=creator,
            description="Another description",
            project_id=project_id,  # Same project
            type=DatasetType.FINETUNING,
            path="datasets/another-path",
        )
        assert False, "Expected ConflictException for case-insensitive duplicate name was not raised"
    except ConflictException:
        # This is expected, rollback the transaction
        await db_session.rollback()
