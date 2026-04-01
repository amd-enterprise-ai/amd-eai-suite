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

from api_common.exceptions import ConflictException, NotFoundException, UploadFailedException, ValidationException
from app.datasets.models import DatasetType
from app.datasets.repository import list_datasets, select_dataset
from app.datasets.service import create_and_upload_dataset, delete_datasets, download_dataset_file, get_dataset_by_id
from app.minio import MinioClient
from tests import factory


@pytest.mark.asyncio
async def test_create_and_upload_dataset_success(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test complete dataset creation and upload workflow."""
    file_content = b'{"text": "test"}\n{"text": "test2"}'
    upload_file = UploadFile(filename="test-upload.jsonl", file=io.BytesIO(file_content))

    name = "Test Upload"
    description = "Uploaded dataset"
    dataset_type = DatasetType.FINETUNING

    with (
        patch("app.datasets.service.validate_jsonl") as mock_validate,
        patch("app.datasets.service.sync_dataset_to_s3") as mock_sync,
    ):
        mock_client = AsyncMock(spec=MinioClient)

        result = await create_and_upload_dataset(
            db_session,
            name,
            description,
            dataset_type,
            upload_file,
            test_user,
            test_namespace,
            mock_client,
        )

    assert result.name == name
    assert result.description == description
    assert result.type == dataset_type
    assert result.namespace == test_namespace
    assert result.created_by == test_user

    mock_validate.assert_called_once_with(upload_file)
    mock_sync.assert_called_once_with(result, upload_file, mock_client)

    db_dataset = await select_dataset(db_session, result.id, test_namespace)
    assert db_dataset is not None


@pytest.mark.asyncio
async def test_create_and_upload_dataset_minio_failure(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test dataset creation when Minio upload fails."""
    file_content = b'{"text": "test"}\n'
    upload_file = UploadFile(filename="test-upload.jsonl", file=io.BytesIO(file_content))

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
                "Failed upload",
                DatasetType.FINETUNING,
                upload_file,
                test_user,
                test_namespace,
                mock_client,
            )


@pytest.mark.asyncio
async def test_create_and_upload_dataset_duplicate_name(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test that duplicate dataset names raise ConflictException."""
    # Create existing dataset
    await factory.create_dataset(
        db_session, name="Existing Dataset", path="existing-dataset.jsonl", namespace=test_namespace
    )

    file_content = b'{"text": "test"}\n'
    upload_file = UploadFile(filename="duplicate.jsonl", file=io.BytesIO(file_content))

    with patch("app.datasets.service.validate_jsonl"):
        mock_client = AsyncMock(spec=MinioClient)

        with pytest.raises(ConflictException, match="already exists"):
            await create_and_upload_dataset(
                db_session,
                "Existing Dataset",  # Duplicate name
                "Duplicate dataset",
                DatasetType.FINETUNING,
                upload_file,
                test_user,
                test_namespace,
                mock_client,
            )


@pytest.mark.asyncio
async def test_create_and_upload_dataset_validation_failure(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test dataset creation when validation fails."""
    file_content = b"invalid json content"
    upload_file = UploadFile(filename="invalid.jsonl", file=io.BytesIO(file_content))

    with patch("app.datasets.service.validate_jsonl") as mock_validate:
        mock_validate.side_effect = ValidationException("Invalid JSONL format")
        mock_client = AsyncMock(spec=MinioClient)

        with pytest.raises(ValidationException):
            await create_and_upload_dataset(
                db_session,
                "Invalid Dataset",
                "Invalid upload",
                DatasetType.FINETUNING,
                upload_file,
                test_user,
                test_namespace,
                mock_client,
            )


@pytest.mark.asyncio
async def test_download_dataset_file_success(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test successful dataset file download."""
    dataset = await factory.create_dataset(
        db_session, name="Download Test Dataset", path="download-test.jsonl", namespace=test_namespace
    )

    mock_file_content = b'{"text": "dataset content"}\n'
    with patch("app.datasets.service.download_from_s3") as mock_download:
        mock_download.return_value = ("download-test.jsonl", mock_file_content)

        mock_client = AsyncMock(spec=MinioClient)
        response = await download_dataset_file(dataset.id, test_namespace, db_session, mock_client)

        assert response is not None
        assert response.media_type == "application/jsonlines"
        assert "download-test.jsonl" in response.headers["Content-Disposition"]

        mock_download.assert_called_once_with(dataset, mock_client)


@pytest.mark.asyncio
async def test_download_dataset_file_not_found(db_session: AsyncSession, test_namespace: str) -> None:
    """Test downloading non-existent dataset file."""
    non_existent_id = uuid4()

    mock_client = AsyncMock(spec=MinioClient)
    with pytest.raises(NotFoundException, match="Dataset.*not found"):
        await download_dataset_file(non_existent_id, test_namespace, db_session, mock_client)


@pytest.mark.asyncio
async def test_get_dataset_by_id_success(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test retrieving a dataset by ID."""
    dataset = await factory.create_dataset(
        db_session, name="Test Dataset", path="test-dataset.jsonl", namespace=test_namespace
    )

    result = await get_dataset_by_id(db_session, dataset.id, test_namespace)

    assert result.id == dataset.id
    assert result.name == dataset.name
    assert result.namespace == test_namespace


@pytest.mark.asyncio
async def test_get_dataset_by_id_not_found(db_session: AsyncSession, test_namespace: str) -> None:
    """Test retrieving non-existent dataset raises NotFoundException."""
    non_existent_id = uuid4()

    with pytest.raises(NotFoundException, match="Dataset.*not found"):
        await get_dataset_by_id(db_session, non_existent_id, test_namespace)


@pytest.mark.asyncio
async def test_delete_datasets_success(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test successful deletion of multiple datasets."""
    # Create test datasets
    dataset1 = await factory.create_dataset(
        db_session, name="Dataset 1", path="dataset-1.jsonl", namespace=test_namespace
    )
    dataset2 = await factory.create_dataset(
        db_session, name="Dataset 2", path="dataset-2.jsonl", namespace=test_namespace
    )

    with patch("app.datasets.service.delete_from_s3") as mock_delete_s3:
        mock_client = AsyncMock(spec=MinioClient)

        deleted_ids = await delete_datasets(db_session, [dataset1.id, dataset2.id], test_namespace, mock_client)

        assert len(deleted_ids) == 2
        assert dataset1.id in deleted_ids
        assert dataset2.id in deleted_ids

        # Verify S3 deletion was called for both datasets
        assert mock_delete_s3.call_count == 2

        # Verify datasets are deleted from database
        remaining = await list_datasets(db_session, test_namespace)
        assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_datasets_with_wrong_ids(db_session: AsyncSession, test_namespace: str) -> None:
    """Test deletion with non-existent IDs returns empty list."""
    wrong_ids = [uuid4(), uuid4()]

    mock_client = AsyncMock(spec=MinioClient)
    deleted_ids = await delete_datasets(db_session, wrong_ids, test_namespace, mock_client)

    assert deleted_ids == []


@pytest.mark.asyncio
async def test_delete_datasets_s3_failure_continues(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test that S3 deletion failure doesn't prevent database deletion."""
    dataset = await factory.create_dataset(
        db_session, name="Test Dataset", path="test-dataset.jsonl", namespace=test_namespace
    )

    with patch("app.datasets.service.delete_from_s3") as mock_delete_s3:
        mock_delete_s3.side_effect = Exception("S3 deletion failed")
        mock_client = AsyncMock(spec=MinioClient)

        # Deletion should still succeed and return the ID
        deleted_ids = await delete_datasets(db_session, [dataset.id], test_namespace, mock_client)

        assert dataset.id in deleted_ids

        # Verify dataset is deleted from database even though S3 deletion failed
        remaining = await list_datasets(db_session, test_namespace)
        assert len(remaining) == 0


@pytest.mark.asyncio
async def test_delete_datasets_namespace_isolation(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test that datasets can only be deleted from their own namespace."""
    other_namespace = "other-namespace"

    # Create dataset in test_namespace
    dataset = await factory.create_dataset(
        db_session, name="Test Dataset", path="test-dataset.jsonl", namespace=test_namespace
    )

    mock_client = AsyncMock(spec=MinioClient)

    # Try to delete from different namespace
    deleted_ids = await delete_datasets(db_session, [dataset.id], other_namespace, mock_client)

    # Should not delete because namespace doesn't match
    assert deleted_ids == []

    # Verify dataset still exists in original namespace
    result = await select_dataset(db_session, dataset.id, test_namespace)
    assert result is not None
