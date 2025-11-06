# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Tests for the dataset service functions using real database operations.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.models import DatasetType
from app.datasets.schemas import DatasetCreate
from app.datasets.service import create_and_upload_dataset, download_dataset_file, insert_dataset
from app.utilities.exceptions import (
    ConflictException,
    NotFoundException,
    UploadFailedException,
    ValidationException,
)
from app.utilities.minio import MinioClient
from tests import factory


class TestInsertDataset:
    """Tests for the insert_dataset function using real database operations."""

    @pytest.mark.asyncio
    async def test_insert_dataset_success(self, db_session: AsyncSession):
        """Test successful insertion of a dataset."""
        env = await factory.create_basic_test_environment(db_session)

        # Create dataset schema with S3 path that needs cleaning

        dataset_create = DatasetCreate(
            path="/test-data/my-dataset.jsonl",  # Path that will be cleaned
            description="Test dataset for insertion",
            type=DatasetType.FINETUNING,
        )

        creator = "test@example.com"

        # Mock only the S3 path utilities (business logic, not database operations)
        with (
            patch("app.datasets.service.clean_s3_path", return_value="test-data/my-dataset.jsonl"),
            patch("app.datasets.service.derive_name_from_path", return_value="my-dataset"),
        ):
            result = await insert_dataset(db_session, dataset_create, env.project.id, creator)

            assert result.name == "my-dataset"
            assert result.path == "test-data/my-dataset.jsonl"
            assert result.project_id == env.project.id
            assert result.description == "Test dataset for insertion"
            assert result.created_by == creator

    @pytest.mark.asyncio
    async def test_insert_dataset_path_conflict(self, db_session: AsyncSession):
        """Test handling of path conflict during dataset insertion."""
        env = await factory.create_basic_test_environment(db_session)

        # Create first dataset to establish conflict
        _ = await factory.create_dataset(
            db_session, env.project, name="existing-dataset", path="conflicting-path.jsonl"
        )

        # Try to create another dataset with same path (this will trigger DB constraint)
        dataset_create = DatasetCreate(
            path="/conflicting-path.jsonl",  # Same path after cleaning
            description="Conflicting dataset",
            type=DatasetType.FINETUNING,
        )

        creator = "test@example.com"

        # Mock path utilities to return conflicting path
        with (
            patch("app.datasets.service.clean_s3_path", return_value="conflicting-path.jsonl"),
            patch("app.datasets.service.derive_name_from_path", return_value="conflicting-dataset"),
        ):
            with pytest.raises(ConflictException) as exc_info:
                await insert_dataset(db_session, dataset_create, env.project.id, creator)
            assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_insert_dataset_name_conflict(self, db_session: AsyncSession):
        """Test handling of name conflict during dataset insertion."""
        env = await factory.create_basic_test_environment(db_session)

        # Create first dataset to establish name conflict
        existing_dataset = await factory.create_dataset(
            db_session, env.project, name="duplicate-name", path="first-path.jsonl"
        )

        # Try to create another dataset with same name (different path)
        dataset_create = DatasetCreate(
            path="/different-path.jsonl", description="Dataset with duplicate name", type=DatasetType.FINETUNING
        )

        creator = "test@example.com"

        # Mock path utilities to return same derived name
        with (
            patch("app.datasets.service.clean_s3_path", return_value="different-path.jsonl"),
            patch("app.datasets.service.derive_name_from_path", return_value="duplicate-name"),
        ):
            with pytest.raises(ConflictException) as exc_info:
                await insert_dataset(db_session, dataset_create, env.project.id, creator)
            assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_insert_dataset_project_not_found(self, db_session: AsyncSession):
        """Test handling of project not found during dataset insertion."""
        env = await factory.create_basic_test_environment(db_session)

        dataset_create = DatasetCreate(
            path="/test-path.jsonl", description="Dataset for non-existent project", type=DatasetType.FINETUNING
        )

        fake_project_id = uuid4()
        creator = "test@example.com"

        with (
            patch("app.datasets.service.clean_s3_path", return_value="test-path.jsonl"),
            patch("app.datasets.service.derive_name_from_path", return_value="test-dataset"),
        ):
            with pytest.raises(ConflictException) as exc_info:
                await insert_dataset(db_session, dataset_create, fake_project_id, creator)
            assert "not found" in str(exc_info.value)


class TestCreateAndUploadDataset:
    """Tests for the create_and_upload_dataset function using real database operations."""

    @pytest.mark.asyncio
    async def test_create_and_upload_success(self, db_session: AsyncSession):
        """Test successful creation and upload of a dataset."""
        env = await factory.create_basic_test_environment(db_session)

        name = "Test Dataset"
        description = "Test Description"
        dataset_type = DatasetType.FINETUNING
        author = "test@example.com"
        object_key = "test-project/datasets/test-dataset.jsonl"

        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.seek = AsyncMock()

        # Mock external services and utilities (not database operations)
        with (
            patch("app.datasets.service.validate_jsonl", return_value=True),
            patch("app.datasets.service.get_object_key", return_value=object_key),
            patch("app.datasets.service.sync_dataset_to_s3"),
        ):
            mock_minio_client = AsyncMock(spec=MinioClient)
            result = await create_and_upload_dataset(
                db_session,
                name,
                description,
                dataset_type,
                mock_file,
                author,
                env.project,
                mock_minio_client,
            )

            assert result.name == name
            assert result.description == description
            assert result.path == object_key
            assert result.project_id == env.project.id
            assert result.type == dataset_type
            assert result.created_by == author

    @pytest.mark.asyncio
    async def test_create_and_upload_name_conflict(self, db_session: AsyncSession):
        """Test handling of name conflict during dataset creation and upload."""
        env = await factory.create_basic_test_environment(db_session)

        # Create existing dataset with conflicting name
        existing_dataset = await factory.create_dataset(
            db_session, env.project, name="Conflicting Name", path="existing-path.jsonl"
        )

        name = "Conflicting Name"  # Same name as existing dataset
        description = "Test Description"
        dataset_type = DatasetType.FINETUNING
        author = "test@example.com"
        object_key = "test-project/datasets/new-dataset.jsonl"

        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.seek = AsyncMock()

        # Mock external services
        with (
            patch("app.datasets.service.validate_jsonl", return_value=True),
            patch("app.datasets.service.get_object_key", return_value=object_key),
        ):
            with pytest.raises(ConflictException) as exc_info:
                mock_minio_client = AsyncMock(spec=MinioClient)
                await create_and_upload_dataset(
                    db_session,
                    name,
                    description,
                    dataset_type,
                    mock_file,
                    author,
                    env.project,
                    mock_minio_client,
                )
            assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_and_upload_upload_error(self, db_session: AsyncSession):
        """Test handling of upload error during dataset creation and upload."""
        env = await factory.create_basic_test_environment(db_session)

        name = "Test Dataset"
        description = "Test Description"
        dataset_type = DatasetType.FINETUNING
        author = "test@example.com"
        object_key = "test-project/datasets/test-dataset.jsonl"

        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.seek = AsyncMock()

        # Mock external services - S3 upload fails
        with (
            patch("app.datasets.service.validate_jsonl", return_value=True),
            patch("app.datasets.service.get_object_key", return_value=object_key),
            patch(
                "app.datasets.service.sync_dataset_to_s3",
                side_effect=Exception("Upload failed"),
            ),
        ):
            with pytest.raises(UploadFailedException) as exc_info:
                mock_minio_client = AsyncMock(spec=MinioClient)
                await create_and_upload_dataset(
                    db_session,
                    name,
                    description,
                    dataset_type,
                    mock_file,
                    author,
                    env.project,
                    mock_minio_client,
                )
            assert "Failed to upload dataset file to storage" == exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_and_upload_validation_error(self, db_session: AsyncSession):
        """Test handling of validation error during dataset creation and upload."""
        env = await factory.create_basic_test_environment(db_session)

        name = "Test Dataset"
        description = "Test Description"
        dataset_type = DatasetType.FINETUNING
        author = "test@example.com"

        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)

        # Mock validation to fail
        with patch("app.datasets.service.validate_jsonl", side_effect=Exception("Invalid JSONL format")):
            with pytest.raises(ValidationException) as exc_info:
                mock_minio_client = AsyncMock(spec=MinioClient)
                await create_and_upload_dataset(
                    db_session,
                    name,
                    description,
                    dataset_type,
                    mock_file,
                    author,
                    env.project,
                    mock_minio_client,
                )
            assert "Failed to validate dataset file" in str(exc_info.value)


class TestDownloadDatasetFile:
    """Tests for the download_dataset_file function using real database operations."""

    @pytest.mark.asyncio
    async def test_download_success(self, db_session: AsyncSession):
        """Test successful download of a dataset file."""
        env = await factory.create_basic_test_environment(db_session)

        # Create dataset with content path
        dataset = await factory.create_dataset(
            db_session,
            env.project,
            name="downloadable-dataset",
            path="datasets/test-project/downloadable-dataset.jsonl",
        )

        file_name = "downloadable-dataset.jsonl"
        content = b'{"text": "test"}\n{"text": "test2"}'

        # Mock only the S3 download operation (external service)
        with patch("app.datasets.service.download_from_s3", return_value=(file_name, content)):
            mock_minio_client = AsyncMock(spec=MinioClient)
            response = await download_dataset_file(dataset.id, env.project.id, db_session, mock_minio_client)

            assert response.body == content
            assert response.headers["Content-Type"] == "application/jsonl; charset=utf-8"
            assert response.headers["Content-Disposition"] == f'attachment; filename="{file_name}"'

    @pytest.mark.asyncio
    async def test_download_dataset_not_found(self, db_session: AsyncSession):
        """Test handling of dataset not found during download."""
        env = await factory.create_basic_test_environment(db_session)
        fake_dataset_id = uuid4()

        with pytest.raises(NotFoundException) as exc_info:
            mock_minio_client = AsyncMock(spec=MinioClient)
            await download_dataset_file(fake_dataset_id, env.project.id, db_session, mock_minio_client)
        assert f"Dataset {fake_dataset_id} not found" == exc_info.value.message

    @pytest.mark.asyncio
    async def test_download_no_content(self, db_session: AsyncSession):
        """Test handling of dataset with no content during download."""
        env = await factory.create_basic_test_environment(db_session)

        # Create dataset without content (empty path)
        dataset = await factory.create_dataset(
            db_session,
            env.project,
            name="empty-dataset",
            path="",  # Empty path means no content
        )

        with pytest.raises(NotFoundException) as exc_info:
            mock_minio_client = AsyncMock(spec=MinioClient)
            await download_dataset_file(dataset.id, env.project.id, db_session, mock_minio_client)
        assert f"Dataset {dataset.id} has no content to download." == exc_info.value.message


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
