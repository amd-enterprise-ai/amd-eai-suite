# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Tests for S3 operations including upload, download, and validation functions.
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from minio.error import S3Error

from app.datasets.models import Dataset
from app.datasets.utils import (
    download_from_s3,
    extract_bucket_and_key,
    sync_dataset_to_s3,
    validate_jsonl,
    verify_s3_sync,
)
from app.utilities.exceptions import ExternalServiceError, ForbiddenException, NotFoundException, ValidationException
from app.utilities.minio import (
    MinioClient,
)


class TestExtractBucketAndKey:
    """Tests for the extract_bucket_and_key function."""

    def test_valid_path(self):
        """Test extracting bucket and key from a valid path."""
        bucket, key = extract_bucket_and_key("bucket/path/to/file.jsonl")
        assert bucket == "bucket"
        assert key == "path/to/file.jsonl"

    def test_invalid_path(self):
        """Test that an invalid path raises a ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_bucket_and_key("invalid-path")
        assert "Invalid path format" in str(exc_info.value)

    def test_path_with_multiple_parts(self):
        """Test extracting bucket and key from a path with multiple parts."""
        bucket, key = extract_bucket_and_key("custom-bucket/path/to/nested/file.jsonl")
        assert bucket == "custom-bucket"
        assert key == "path/to/nested/file.jsonl"


class TestVerifyS3Sync:
    """Tests for the verify_s3_sync function."""

    @pytest.mark.asyncio
    async def test_verify_success(self):
        """Test successful verification of an S3 sync operation."""
        client = MagicMock(spec=MinioClient)
        client.client = MagicMock()  # Add the client attribute
        client.client.stat_object.return_value = MagicMock(size=10)

        result = await verify_s3_sync(client, "bucket", "object", b"0123456789")

        client.client.stat_object.assert_called_once_with("bucket", "object")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_size_mismatch(self):
        """Test size mismatch during S3 sync verification."""
        client = MagicMock(spec=MinioClient)
        client.client = MagicMock()  # Add the client attribute
        client.client.stat_object.return_value = MagicMock(size=5)

        with pytest.raises(ExternalServiceError) as exc_info:
            await verify_s3_sync(client, "bucket", "object", b"0123456789")

        assert "Failed to verify verifying upload" in str(exc_info.value)


class TestSyncDatasetToS3:
    """Tests for the sync_dataset_to_s3 function."""

    @pytest.mark.asyncio
    async def test_sync_success(self):
        """Test successful synchronization of a dataset to S3."""
        dataset = MagicMock(spec=Dataset)
        dataset.id = "test-id"
        dataset.path = "datasets/test-id.jsonl"  # Set the path explicitly

        file_content = b'{"text": "test"}\n{"text": "test2"}'
        file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

        mock_client = MagicMock(spec=MinioClient)

        with (
            patch("app.datasets.utils.verify_s3_sync", return_value=True),
        ):
            result = await sync_dataset_to_s3(dataset, file, mock_client)

            mock_client.upload_object.assert_called_once()
            assert result == "default-bucket/datasets/test-id.jsonl"

    @pytest.mark.asyncio
    async def test_sync_s3_error(self):
        """Test handling of S3Error during dataset synchronization."""
        dataset = MagicMock(spec=Dataset)
        dataset.id = "test-id"
        dataset.path = "datasets/test-id.jsonl"

        file_content = b'{"text": "test"}\n{"text": "test2"}'
        file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

        mock_client = MagicMock(spec=MinioClient)
        s3_error = S3Error(
            code="AccessDenied",
            message="Access Denied",
            resource="/bucket/object",
            request_id="request123",
            host_id="host123",
            response="response",
        )
        mock_client.upload_object.side_effect = s3_error

        with patch("app.utilities.config.MINIO_BUCKET", "bucket"):
            with pytest.raises(ForbiddenException):  # AccessDenied maps to ForbiddenException
                await sync_dataset_to_s3(dataset, file, mock_client)


class TestDownloadFromS3:
    """Tests for the download_from_s3 function."""

    @pytest.mark.asyncio
    async def test_download_success(self):
        """Test successful downloading of a dataset from S3."""
        dataset = MagicMock(spec=Dataset)
        dataset.id = "test-id"
        dataset.path = "datasets/test-id.jsonl"

        mock_client = MagicMock(spec=MinioClient)
        mock_client.download_object.return_value = b'{"text": "test"}\n{"text": "test2"}'

        file_name, content = await download_from_s3(dataset, mock_client)

        mock_client.download_object.assert_called_once_with(
            bucket_name="default-bucket", object_name="datasets/test-id.jsonl"
        )
        assert file_name == "test-id.jsonl"
        assert content == b'{"text": "test"}\n{"text": "test2"}'

    @pytest.mark.asyncio
    async def test_download_error(self):
        """Test handling of S3Error during dataset download."""
        dataset = MagicMock(spec=Dataset)
        dataset.id = "test-id"
        dataset.path = "datasets/test-id.jsonl"

        mock_client = MagicMock(spec=MinioClient)
        s3_error = S3Error(
            code="NoSuchKey",
            message="The specified key does not exist",
            resource="/bucket/datasets/test-id.jsonl",
            request_id="request123",
            host_id="host123",
            response="response",
        )
        mock_client.download_object.side_effect = s3_error

        with patch("app.utilities.config.MINIO_BUCKET", "bucket"):
            with pytest.raises(NotFoundException):  # NoSuchKey maps to NotFoundException
                await download_from_s3(dataset, mock_client)


class TestValidateJsonl:
    """Tests for the validate_jsonl function."""

    def test_valid_file(self):
        """Test validation of a valid JSONL file."""
        file_content = b'{"text": "test"}\n{"text": "test2"}'
        file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

        result = validate_jsonl(file)
        assert result is True

    def test_invalid_extension(self):
        """Test validation of a file with an invalid extension."""
        file_content = b'{"text": "test"}\n{"text": "test2"}'
        file = UploadFile(filename="test.txt", file=io.BytesIO(file_content))

        with pytest.raises(ValidationException) as exc_info:
            validate_jsonl(file)

        assert "Invalid file format" in exc_info.value.message


class TestIntegrationS3Operations:
    """Integration tests for S3 operations with multiple functions working together."""

    @pytest.fixture
    def mock_dataset(self):
        """Create a mock dataset for testing."""
        dataset = MagicMock(spec=Dataset)
        dataset.id = "test-id"
        dataset.author = "test-org"
        dataset.created_at = "2025-01-01"
        dataset.updated_at = "2025-01-02"
        dataset.path = "datasets/test-id.jsonl"
        return dataset

    @pytest.mark.asyncio
    async def test_upload_and_download_flow(self, mock_dataset):
        """Test the complete flow of uploading and then downloading a dataset file."""
        # Configure mocked MinioClient
        mock_minio_instance = MagicMock(spec=MinioClient)
        mock_minio_instance.client = MagicMock()  # Add the client attribute
        content = b'{"field1": "value1"}\n{"field2": "value2"}'

        upload = UploadFile(filename="test.jsonl", file=io.BytesIO(content))

        # Configure mock to match the file we're uploading
        mock_stat = MagicMock()
        mock_stat.size = len(content)
        mock_minio_instance.client.stat_object.return_value = mock_stat

        # Upload test
        path = await sync_dataset_to_s3(mock_dataset, upload, mock_minio_instance)

        # Verify file was uploaded with correct parameters
        mock_minio_instance.upload_object.assert_called_once()
        call_args = mock_minio_instance.upload_object.call_args[1]
        assert call_args["bucket_name"] == "default-bucket"
        assert call_args["object_name"] == "datasets/test-id.jsonl"
        assert path == "default-bucket/datasets/test-id.jsonl"

        # Download test
        mock_minio_instance.download_object.return_value = content
        file_name, file_content = await download_from_s3(mock_dataset, mock_minio_instance)

        # Verify download was called with correct parameters
        mock_minio_instance.download_object.assert_called_once()
        call_args = mock_minio_instance.download_object.call_args[1]
        assert call_args["bucket_name"] == "default-bucket"
        assert call_args["object_name"] == "datasets/test-id.jsonl"
        assert file_name == "test-id.jsonl"
        assert file_content == content


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
