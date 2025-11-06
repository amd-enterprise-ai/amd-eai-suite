# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Datasets service tests."""

import io
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.models import Dataset, DatasetType
from app.datasets.schemas import DatasetCreate
from app.datasets.service import (
    create_and_upload_dataset,
    delete_datasets,
    download_dataset_file,
    insert_dataset,
)
from app.utilities.exceptions import (
    ConflictException,
    NotFoundException,
    UploadFailedException,
    ValidationException,
)
from app.utilities.minio import MinioClient
from tests import factory


@pytest.mark.asyncio
async def test_insert_dataset_success(db_session: AsyncSession):
    """Test successful dataset insertion with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    # Create dataset schema
    dataset_create = DatasetCreate(
        description="Test Description",
        type=DatasetType.FINETUNING,
        path="s3://bucket/test-dataset.jsonl",
    )
    creator = "test@example.com"

    result = await insert_dataset(db_session, dataset_create, env.project.id, creator)

    assert result.name == "Test Dataset"  # Derived from path
    assert result.description == "Test Description"
    assert result.type == DatasetType.FINETUNING
    assert result.path == "bucket/test-dataset.jsonl"  # Cleaned path (bucket kept since it doesn't match MINIO_BUCKET)
    assert result.project_id == env.project.id
    assert result.created_by == creator

    from app.datasets.repository import select_dataset

    db_dataset = await select_dataset(db_session, result.id, env.project.id)
    assert db_dataset is not None
    assert db_dataset.name == "Test Dataset"


@pytest.mark.asyncio
async def test_insert_dataset_duplicate_name_raises_conflict(db_session: AsyncSession):
    """Test that duplicate dataset names raise ConflictException."""
    env = await factory.create_basic_test_environment(db_session)

    existing_dataset = await factory.create_dataset(
        db_session, env.project, name="Existing Dataset", path="existing-dataset.jsonl"
    )

    dataset_create = DatasetCreate(
        description="Duplicate dataset",
        type=DatasetType.FINETUNING,
        path="s3://bucket/existing-dataset.jsonl",  # Same derived name
    )
    creator = "test@example.com"

    with pytest.raises(ConflictException, match="A dataset with name.*already exists in this project"):
        await insert_dataset(db_session, dataset_create, env.project.id, creator)


@pytest.mark.asyncio
async def test_create_and_upload_dataset_success(db_session: AsyncSession):
    """Test complete dataset creation and upload workflow."""
    env = await factory.create_basic_test_environment(db_session)

    file_content = b"test data content"
    upload_file = UploadFile(filename="test-upload.jsonl", file=io.BytesIO(file_content))

    dataset_create = DatasetCreate(
        description="Uploaded dataset",
        type=DatasetType.FINETUNING,
        path="test-upload.jsonl",
    )
    creator = "test@example.com"

    with (
        patch("app.datasets.service.validate_jsonl") as mock_validate,
        patch("app.datasets.service.sync_dataset_to_s3") as mock_sync,
    ):
        mock_client = AsyncMock(spec=MinioClient)

        result = await create_and_upload_dataset(
            db_session,
            "Test Upload",
            dataset_create.description,
            dataset_create.type,
            upload_file,
            creator,
            env.project,
            mock_client,
        )

    assert result.name == "Test Upload"
    assert result.description == "Uploaded dataset"
    assert result.type == DatasetType.FINETUNING
    assert result.project_id == env.project.id
    assert result.created_by == creator

    mock_validate.assert_called_once_with(upload_file)
    mock_sync.assert_called_once_with(result, upload_file, mock_client)

    from app.datasets.repository import select_dataset

    db_dataset = await select_dataset(db_session, result.id, env.project.id)
    assert db_dataset is not None


@pytest.mark.asyncio
async def test_create_and_upload_dataset_minio_failure(db_session: AsyncSession):
    """Test dataset creation when Minio upload fails."""
    env = await factory.create_basic_test_environment(db_session)

    file_content = b"test data content"
    upload_file = UploadFile(filename="test-upload.jsonl", file=io.BytesIO(file_content))

    dataset_create = DatasetCreate(
        description="Failed upload dataset",
        type=DatasetType.FINETUNING,
        path="test-upload.jsonl",
    )
    creator = "test@example.com"

    with (
        patch("app.datasets.service.validate_jsonl") as mock_validate,
        patch("app.datasets.service.sync_dataset_to_s3") as mock_sync,
    ):
        mock_client = AsyncMock(spec=MinioClient)
        mock_sync.side_effect = UploadFailedException("Minio upload failed")

        with pytest.raises(UploadFailedException, match="Failed to upload dataset file to storage"):
            await create_and_upload_dataset(
                db_session,
                "Test Upload",
                dataset_create.description,
                dataset_create.type,
                upload_file,
                creator,
                env.project,
                mock_client,
            )

    # Note: In this service layer test, the dataset record may still exist
    # since transaction rollback is handled at the API layer, not service layer.
    # The important thing is that the UploadFailedException was raised correctly.


@pytest.mark.asyncio
async def test_download_dataset_file_success(db_session: AsyncSession):
    """Test successful dataset file download."""
    env = await factory.create_basic_test_environment(db_session)

    dataset = await factory.create_dataset(
        db_session, env.project, name="Download Test Dataset", path="download-test.jsonl"
    )

    mock_file_content = b"dataset file content"
    with patch("app.datasets.service.download_from_s3") as mock_download:
        mock_download.return_value = ("download-test.jsonl", mock_file_content)

        mock_client = AsyncMock(spec=MinioClient)
        response = await download_dataset_file(dataset.id, env.project.id, db_session, mock_client)

        assert response is not None
        assert response.media_type == "application/jsonlines"
        assert "download-test.jsonl" in response.headers["Content-Disposition"]

        mock_download.assert_called_once_with(dataset, mock_client)


@pytest.mark.asyncio
async def test_download_dataset_file_not_found(db_session: AsyncSession):
    """Test downloading non-existent dataset file."""
    env = await factory.create_basic_test_environment(db_session)

    non_existent_id = uuid4()

    mock_client = AsyncMock(spec=MinioClient)
    with pytest.raises(NotFoundException, match="Dataset.*not found"):
        await download_dataset_file(non_existent_id, env.project.id, db_session, mock_client)


@pytest.mark.asyncio
async def test_insert_dataset_with_empty_path(db_session: AsyncSession):
    """Test dataset insertion with empty path (should succeed)."""
    env = await factory.create_basic_test_environment(db_session)

    dataset_create = DatasetCreate(
        description="Empty path dataset",
        type=DatasetType.FINETUNING,
        path="",  # Empty path is valid and gets processed
    )
    creator = "test@example.com"

    result = await insert_dataset(db_session, dataset_create, env.project.id, creator)

    assert result is not None
    assert result.description == "Empty path dataset"
    assert result.type == DatasetType.FINETUNING
    assert result.path == ""  # Empty path is preserved
    assert result.name == ""  # Empty name derived from empty path


@pytest.mark.asyncio
async def test_insert_dataset_with_different_types(db_session: AsyncSession):
    """Test inserting datasets with different types."""
    env = await factory.create_basic_test_environment(db_session)

    creator = "test@example.com"

    finetuning_dataset = DatasetCreate(
        description="Finetuning dataset",
        type=DatasetType.FINETUNING,
        path="s3://bucket/finetuning-data.jsonl",
    )

    result1 = await insert_dataset(db_session, finetuning_dataset, env.project.id, creator)
    assert result1.type == DatasetType.FINETUNING

    second_dataset = DatasetCreate(
        description="Second finetuning dataset",
        type=DatasetType.FINETUNING,
        path="s3://bucket/second-finetuning-data.jsonl",
    )

    result2 = await insert_dataset(db_session, second_dataset, env.project.id, creator)
    assert result2.type == DatasetType.FINETUNING

    from app.datasets.repository import list_datasets

    datasets = await list_datasets(db_session, project_id=env.project.id)
    assert len(datasets) == 2

    dataset_types = {d.type for d in datasets}
    assert DatasetType.FINETUNING in dataset_types


@pytest.mark.asyncio
async def test_create_and_upload_dataset_generic_error(db_session: AsyncSession):
    """Test dataset creation with unexpected database error."""
    env = await factory.create_basic_test_environment(db_session)

    file_content = b"test data content"
    upload_file = UploadFile(filename="test-upload.jsonl", file=io.BytesIO(file_content))

    dataset_create = DatasetCreate(
        description="Test dataset",
        type=DatasetType.FINETUNING,
        path="test-upload.jsonl",
    )
    creator = "test@example.com"

    with patch("app.datasets.service.validate_jsonl") as mock_validate:
        mock_client = AsyncMock(spec=MinioClient)
        mock_validate.return_value = None  # Pass validation

        await factory.create_dataset(db_session, env.project, name="Test Dataset")

        with pytest.raises(ConflictException, match="already exists"):
            await create_and_upload_dataset(
                db_session,
                "Test Dataset",  # Same name - should cause constraint violation
                dataset_create.description,
                dataset_create.type,
                upload_file,
                creator,
                env.project,
                mock_client,
            )


@pytest.mark.asyncio
async def test_insert_dataset_project_not_found(db_session: AsyncSession):
    """Test dataset insertion when project doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    dataset_create = DatasetCreate(
        description="Test dataset",
        type=DatasetType.FINETUNING,
        path="s3://bucket/test-dataset.jsonl",
    )
    creator = "test@example.com"

    non_existent_project_id = uuid4()

    with pytest.raises(Exception):  # Could be foreign key constraint or business logic error
        await insert_dataset(db_session, dataset_create, non_existent_project_id, creator)


@pytest.mark.asyncio
async def test_create_and_upload_dataset_sync_error(db_session: AsyncSession):
    """Test dataset creation when S3 sync operation fails."""
    env = await factory.create_basic_test_environment(db_session)

    file_content = b"test data content"
    upload_file = UploadFile(filename="test-upload.jsonl", file=io.BytesIO(file_content))

    dataset_create = DatasetCreate(
        description="Test dataset with sync error",
        type=DatasetType.FINETUNING,
        path="test-upload.jsonl",
    )
    creator = "test@example.com"

    with (
        patch("app.datasets.service.validate_jsonl") as mock_validate,
        patch("app.datasets.service.sync_dataset_to_s3", side_effect=Exception("S3 sync failed")) as mock_sync,
    ):
        mock_client = AsyncMock(spec=MinioClient)

        with pytest.raises(UploadFailedException, match="Failed to upload dataset file"):
            await create_and_upload_dataset(
                db_session,
                "Test Dataset",
                dataset_create.description,
                dataset_create.type,
                upload_file,
                creator,
                env.project,
                mock_client,
            )


@pytest.mark.asyncio
async def test_download_dataset_file_no_content(db_session: AsyncSession):
    """Test downloading dataset that has no content path."""
    env = await factory.create_basic_test_environment(db_session)

    dataset = await factory.create_dataset(
        db_session,
        env.project,
        name="Empty Dataset",
        path="",  # Empty path - indicates no content
    )

    mock_client = AsyncMock(spec=MinioClient)
    with pytest.raises((NotFoundException, ValidationException)):
        await download_dataset_file(dataset.id, env.project.id, db_session, mock_client)


@pytest.mark.asyncio
async def test_delete_datasets_success():
    mock_session = AsyncMock()
    project_id = uuid4()
    dataset_ids = [uuid4(), uuid4()]
    mock_minio_client = AsyncMock()
    # Mock datasets returned by list_datasets
    mock_datasets = [
        Dataset(
            id=dataset_ids[0],
            path="datasets/one",
            project_id=project_id,
            name="A",
            type="FINETUNING",
            created_by="a",
            updated_by="a",
            description="",
            created_at=None,
            updated_at=None,
        ),
        Dataset(
            id=dataset_ids[1],
            path="datasets/two",
            project_id=project_id,
            name="B",
            type="FINETUNING",
            created_by="a",
            updated_by="a",
            description="",
            created_at=None,
            updated_at=None,
        ),
    ]
    with (
        patch("app.datasets.service.list_datasets", return_value=mock_datasets) as mock_list,
        patch("app.datasets.service.delete_datasets_by_ids", return_value=None) as mock_delete,
        patch("app.datasets.service.delete_from_s3", return_value=None) as mock_delete_s3,
    ):
        result = await delete_datasets(mock_session, dataset_ids, project_id, mock_minio_client)
        assert set(result) == set(dataset_ids)
        mock_list.assert_called_once_with(mock_session, project_id, selected_datasets_ids=dataset_ids)
        mock_delete.assert_called_once_with(mock_session, dataset_ids, project_id)
        assert mock_delete_s3.call_count == 2


@pytest.mark.asyncio
async def test_delete_datasets_not_found():
    mock_session = AsyncMock()
    project_id = uuid4()
    dataset_ids = [uuid4()]
    mock_minio_client = AsyncMock()
    # list_datasets returns empty (no datasets found)
    with (
        patch("app.datasets.service.list_datasets", return_value=[]) as mock_list,
        patch("app.datasets.service.delete_datasets_by_ids") as mock_delete,
        patch("app.datasets.service.delete_from_s3") as mock_delete_s3,
    ):
        result = await delete_datasets(mock_session, dataset_ids, project_id, mock_minio_client)
        assert result == []
        mock_list.assert_called_once_with(mock_session, project_id, selected_datasets_ids=dataset_ids)
        mock_delete.assert_called_once_with(mock_session, [], project_id)
        mock_delete_s3.assert_not_called()


@pytest.mark.asyncio
async def test_delete_datasets_error_rollback():
    mock_session = AsyncMock()
    project_id = uuid4()
    dataset_ids = [uuid4()]
    mock_minio_client = AsyncMock()
    mock_dataset = Dataset(
        id=dataset_ids[0],
        path="datasets/one",
        project_id=project_id,
        name="A",
        type="FINETUNING",
        created_by="a",
        updated_by="a",
        description="",
        created_at=None,
        updated_at=None,
    )
    with (
        patch("app.datasets.service.list_datasets", return_value=[mock_dataset]),
        patch("app.datasets.service.delete_datasets_by_ids", side_effect=Exception("DB error")),
        patch("app.datasets.service.delete_from_s3") as mock_delete_s3,
    ):
        with pytest.raises(Exception) as exc_info:
            await delete_datasets(mock_session, dataset_ids, project_id, mock_minio_client)
        assert "DB error" in str(exc_info.value)
        # Transaction rollback is handled by API layer, not service layer
        mock_delete_s3.assert_not_called()
