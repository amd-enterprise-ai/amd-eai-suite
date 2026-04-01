# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ConflictException
from app.datasets.models import DatasetType
from app.datasets.repository import (
    delete_dataset_by_id,
    delete_datasets,
    insert_dataset,
    list_datasets,
    select_dataset,
)


@pytest.mark.asyncio
async def test_insert_dataset(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    dataset = await insert_dataset(
        db_session,
        name="Test Dataset",
        creator=test_user,
        description="Test description",
        namespace=test_namespace,
        type=DatasetType.FINETUNING,
        path="datasets/test",
    )

    assert dataset.id is not None
    assert dataset.name == "Test Dataset"
    assert dataset.description == "Test description"
    assert dataset.path == "datasets/test"
    assert dataset.created_by == test_user
    assert dataset.namespace == test_namespace
    assert dataset.type == DatasetType.FINETUNING

    specific_id = uuid4()
    dataset2 = await insert_dataset(
        db_session,
        id=specific_id,
        name="Test Dataset 2",
        creator=test_user,
        description="Test description 2",
        namespace=test_namespace,
        type=DatasetType.FINETUNING,
        path="datasets/test2",
    )

    assert dataset2.id == specific_id
    assert dataset2.name == "Test Dataset 2"


@pytest.mark.asyncio
async def test_delete_dataset(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    dataset = await insert_dataset(
        db_session,
        name="Test Dataset",
        creator=test_user,
        description="Test description",
        namespace=test_namespace,
        type=DatasetType.FINETUNING,
        path="datasets/test",
    )

    await delete_dataset_by_id(db_session, dataset.id, test_namespace)

    # Try to retrieve the deleted dataset
    retrieved_dataset = await select_dataset(db_session, dataset.id, test_namespace)
    assert retrieved_dataset is None


@pytest.mark.asyncio
async def test_list_datasets(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    # Create multiple datasets
    datasets = []
    for i in range(5):
        dataset = await insert_dataset(
            db_session,
            name=f"Dataset {i}",
            creator=test_user,
            description=f"Description {i}",
            namespace=test_namespace,
            type=DatasetType.FINETUNING,
            path=f"datasets/test{i}",
        )
        datasets.append(dataset)

    # List all datasets
    all_datasets = await list_datasets(db_session, test_namespace)
    assert len(all_datasets) == 5

    # List datasets of a specific type
    finetuning_datasets = await list_datasets(db_session, test_namespace, type=DatasetType.FINETUNING)
    assert len(finetuning_datasets) == 5

    # List datasets with a specific name
    specific_dataset = await list_datasets(db_session, test_namespace, name="Dataset 3")
    assert len(specific_dataset) == 1
    assert specific_dataset[0].name == "Dataset 3"

    # List datasets by selected IDs
    selected_ids = [datasets[1].id, datasets[3].id]
    selected_datasets = await list_datasets(db_session, test_namespace, selected_datasets_ids=selected_ids)
    assert len(selected_datasets) == 2
    returned_ids = {d.id for d in selected_datasets}
    assert set(selected_ids) == returned_ids


@pytest.mark.asyncio
async def test_delete_datasets(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    # Create multiple datasets
    dataset_ids = []
    for i in range(10):
        dataset = await insert_dataset(
            db_session,
            name=f"Dataset {i}",
            creator=test_user,
            description=f"Description {i}",
            namespace=test_namespace,
            type=DatasetType.FINETUNING,
            path=f"datasets/test{i}",
        )
        dataset_ids.append(dataset.id)

    await delete_datasets(db_session, dataset_ids, test_namespace)

    # Try to list datasets
    all_datasets = await list_datasets(db_session, test_namespace)
    assert len(all_datasets) == 0


@pytest.mark.asyncio
async def test_delete_datasets_with_wrong_ids(db_session: AsyncSession, test_namespace: str) -> None:
    # Try to delete with wrong IDs - should return empty list, not raise exception
    wrong_ids = [uuid4() for _ in range(2)]
    deleted_ids = await delete_datasets(db_session, wrong_ids, test_namespace)
    assert deleted_ids == []


@pytest.mark.asyncio
async def test_unique_constraint_duplicate_name(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test unique constraint on dataset name within a namespace"""
    # Create first dataset
    await insert_dataset(
        db_session,
        name="Unique Dataset",
        creator=test_user,
        description="Test description",
        namespace=test_namespace,
        type=DatasetType.FINETUNING,
        path="datasets/unique-path",
    )

    # Try to create dataset with same name in same namespace
    with pytest.raises(ConflictException, match="already exists"):
        await insert_dataset(
            db_session,
            name="Unique Dataset",  # Same name
            creator=test_user,
            description="Another description",
            namespace=test_namespace,  # Same namespace
            type=DatasetType.FINETUNING,
            path="datasets/different-path",
        )


@pytest.mark.asyncio
async def test_unique_constraint_duplicate_path(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test unique constraint on dataset path (globally unique)"""
    # Create first dataset
    await insert_dataset(
        db_session,
        name="Unique Dataset",
        creator=test_user,
        description="Test description",
        namespace=test_namespace,
        type=DatasetType.FINETUNING,
        path="datasets/unique-path",
    )

    # Try to create dataset with same path (should be globally unique)
    with pytest.raises(ConflictException, match="already exists"):
        await insert_dataset(
            db_session,
            name="Different Dataset Name",
            creator=test_user,
            description="Another description",
            namespace=test_namespace,  # Same namespace
            type=DatasetType.FINETUNING,
            path="datasets/unique-path",  # Same path
        )


@pytest.mark.asyncio
async def test_unique_constraint_case_insensitive_name(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test case insensitivity for dataset name uniqueness"""
    # Create first dataset
    await insert_dataset(
        db_session,
        name="Unique Dataset",
        creator=test_user,
        description="Test description",
        namespace=test_namespace,
        type=DatasetType.FINETUNING,
        path="datasets/unique-path",
    )

    # Try to create dataset with same name but different case
    with pytest.raises(ConflictException, match="already exists"):
        await insert_dataset(
            db_session,
            name="UNIQUE dataset",  # Same name but different case
            creator=test_user,
            description="Another description",
            namespace=test_namespace,  # Same namespace
            type=DatasetType.FINETUNING,
            path="datasets/another-path",
        )
