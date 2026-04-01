# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for dataset utility functions (path handling, validation, name derivation)."""

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from minio.error import S3Error

from api_common.exceptions import ExternalServiceError, ForbiddenException, NotFoundException, ValidationException
from app.datasets.models import Dataset
from app.datasets.utils import (
    clean_s3_path,
    delete_from_s3,
    derive_name_from_path,
    download_from_s3,
    get_object_key,
    slugify,
    sync_dataset_to_s3,
    validate_jsonl,
    verify_s3_sync,
)
from app.minio.client import MinioClient


def test_validate_jsonl_success():
    """Test validation of a valid JSONL file."""
    file_content = b'{"text": "test"}\n{"text": "test2"}'
    file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

    with patch("app.datasets.config.MAX_FILE_SIZE_BYTES", 1000):
        # Should not raise an exception
        validate_jsonl(file)


def test_validate_jsonl_invalid_extension():
    """Test validation fails for invalid file extension."""
    file_content = b'{"text": "test"}\n{"text": "test2"}'
    file = UploadFile(filename="test.txt", file=io.BytesIO(file_content))

    with pytest.raises(ValidationException) as exc_info:
        validate_jsonl(file)

    assert "Invalid file format" in exc_info.value.message


def test_slugify():
    """Test the slugify function for creating path-safe dataset names."""
    assert slugify("Test Dataset") == "test-dataset"
    assert slugify("Test! @#$%^&*() Dataset") == "test-dataset"
    assert slugify("Test!!!Dataset") == "test-dataset"
    assert slugify("---Test Dataset---") == "test-dataset"
    assert slugify("Test Dataset 123") == "test-dataset-123"
    assert slugify("Téśt Dàtáśét") == "téśt-dàtáśét"
    assert slugify("test-dataset") == "test-dataset"


def test_derive_name_from_path():
    """Test deriving dataset names from S3 paths."""
    assert derive_name_from_path("datasets/test-dataset.jsonl") == "Test Dataset"
    assert derive_name_from_path("datasets/user/cluster/test-dataset.jsonl") == "Test Dataset"
    assert derive_name_from_path("datasets/test-dataset.json") == "Test Dataset"
    assert derive_name_from_path("datasets/test-dataset.csv") == "Test Dataset"
    assert derive_name_from_path("datasets/test-dataset.txt") == "Test Dataset"
    assert derive_name_from_path("datasets/test_dataset.jsonl") == "Test Dataset"
    assert derive_name_from_path("datasets/test-dataset") == "Test Dataset"
    assert derive_name_from_path("datasets/test-complex-dataset_name.jsonl") == "Test Complex Dataset Name"


def test_clean_s3_path():
    """Test cleaning and validating S3 paths."""
    assert clean_s3_path("datasets/test.jsonl") == "datasets/test.jsonl"
    assert clean_s3_path("s3://bucket/datasets/test.jsonl") == "bucket/datasets/test.jsonl"

    # Test with matching bucket prefix - should extract just the key
    assert clean_s3_path("default-bucket/datasets/test.jsonl") == "datasets/test.jsonl"

    # Test with different bucket - should return the path as is
    with patch("app.minio.config.MINIO_BUCKET", "correct-bucket"):
        assert clean_s3_path("wrong-bucket/datasets/test.jsonl") == "wrong-bucket/datasets/test.jsonl"


def test_get_object_key():
    """Test the get_object_key function that uses project name."""
    assert get_object_key("Test Dataset", "Project A") == "project-a/datasets/test-dataset.jsonl"
    assert (
        get_object_key("Complex Name with Spaces!", "Complex Project Name")
        == "complex-project-name/datasets/complex-name-with-spaces.jsonl"
    )
    assert (
        get_object_key("Dataset with !@#$%^&*()", "Project with !@#$%^&*()")
        == "project-with/datasets/dataset-with.jsonl"
    )


def test_validate_jsonl_file_too_large():
    """Test validation fails for files exceeding size limit."""
    # Create a file that exceeds the limit
    file_content = b'{"text": "test"}\n' * 1000
    file = UploadFile(filename="large.jsonl", file=io.BytesIO(file_content))

    # Patch both the bytes and MB constants used in the validation
    with (
        patch("app.datasets.utils.MAX_FILE_SIZE_BYTES", 100),
        patch("app.datasets.utils.MAX_FILE_SIZE_MB", 0),
    ):
        with pytest.raises(ValidationException) as exc_info:
            validate_jsonl(file)

        assert "File size exceeds" in exc_info.value.message


def test_validate_jsonl_empty_file():
    """Test validation of empty JSONL file."""
    file_content = b""
    file = UploadFile(filename="empty.jsonl", file=io.BytesIO(file_content))

    with patch("app.datasets.config.MAX_FILE_SIZE_BYTES", 1000):
        # Should not raise an exception for empty file (size is within limit)
        validate_jsonl(file)


def test_validate_jsonl_file_at_size_limit():
    """Test validation of file exactly at size limit."""
    file_content = b'{"text": "x"}' * 10
    file = UploadFile(filename="limit.jsonl", file=io.BytesIO(file_content))

    file_size = len(file_content)
    with patch("app.datasets.config.MAX_FILE_SIZE_BYTES", file_size):
        # Should not raise an exception when exactly at limit
        validate_jsonl(file)


# ============================================================================
# S3 Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_verify_s3_sync_success():
    """Test successful S3 sync verification."""
    content = b'{"text": "test"}\n{"text": "test2"}'
    bucket = "test-bucket"
    object_key = "test-namespace/datasets/test.jsonl"

    # Create mock client with nested .client attribute
    mock_client = MagicMock(spec=MinioClient)
    mock_stat = MagicMock(spec=["size"])
    mock_stat.size = len(content)
    mock_inner_client = MagicMock(spec=["stat_object"])
    mock_inner_client.stat_object = MagicMock(return_value=mock_stat)
    mock_client.client = mock_inner_client

    # Should not raise exception on success
    result = await verify_s3_sync(mock_client, bucket, object_key, content)
    assert result is True

    # Verify stat_object was called with correct parameters
    mock_inner_client.stat_object.assert_called_once_with(bucket, object_key)


@pytest.mark.asyncio
async def test_verify_s3_sync_size_mismatch():
    """Test S3 sync verification fails on size mismatch."""
    content = b'{"text": "test"}\n{"text": "test2"}'
    bucket = "test-bucket"
    object_key = "test-namespace/datasets/test.jsonl"

    # Create mock client with wrong size
    mock_client = MagicMock(spec=MinioClient)
    mock_stat = MagicMock(spec=["size"])
    mock_stat.size = len(content) + 100  # Wrong size
    mock_inner_client = MagicMock(spec=["stat_object"])
    mock_inner_client.stat_object = MagicMock(return_value=mock_stat)
    mock_client.client = mock_inner_client

    # Should raise ExternalServiceError when verification fails
    with pytest.raises(ExternalServiceError, match="verify"):
        await verify_s3_sync(mock_client, bucket, object_key, content)


@pytest.mark.asyncio
async def test_sync_dataset_to_s3_success(mock_jsonl_file):
    """Test successful dataset upload to S3."""
    # Create a mock dataset
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/test.jsonl"

    # Create mock client with nested .client attribute
    mock_client = MagicMock(spec=MinioClient)
    mock_stat = MagicMock(spec=["size"])
    mock_stat.size = len(b'{"text": "test"}\n{"text": "test2"}')
    mock_inner_client = MagicMock(spec=["stat_object"])
    mock_inner_client.stat_object = MagicMock(return_value=mock_stat)
    mock_client.client = mock_inner_client
    mock_client.upload_object = MagicMock()

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        result = await sync_dataset_to_s3(dataset, mock_jsonl_file, mock_client)

    # Verify path includes bucket
    assert result == "test-bucket/test-namespace/datasets/test.jsonl"

    # Verify upload_object was called
    assert mock_client.upload_object.called
    call_args = mock_client.upload_object.call_args
    assert call_args[1]["bucket_name"] == "test-bucket"
    assert call_args[1]["object_name"] == "test-namespace/datasets/test.jsonl"


@pytest.mark.asyncio
async def test_sync_dataset_to_s3_upload_failure(mock_jsonl_file):
    """Test dataset upload fails when S3 upload errors."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/test.jsonl"

    # Create mock client that raises S3Error on upload
    mock_client = MagicMock(spec=MinioClient)
    s3_error = S3Error(
        code="InternalError",
        message="Internal server error",
        resource="/test-bucket/test-namespace/datasets/test.jsonl",
        request_id="test-request-id",
        host_id="test-host-id",
        response=MagicMock(spec=["status"], status=500),
    )
    mock_client.upload_object = MagicMock(side_effect=s3_error)

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        # Generic S3 errors get mapped to ExternalServiceError
        with pytest.raises(ExternalServiceError, match="Storage service error"):
            await sync_dataset_to_s3(dataset, mock_jsonl_file, mock_client)


@pytest.mark.asyncio
async def test_sync_dataset_to_s3_verification_failure(mock_jsonl_file):
    """Test dataset upload fails when verification detects size mismatch."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/test.jsonl"

    # Create mock client with upload success but wrong size in stat
    mock_client = MagicMock(spec=MinioClient)
    mock_client.upload_object = MagicMock()
    mock_stat = MagicMock(spec=["size"])
    mock_stat.size = 999999  # Wrong size
    mock_inner_client = MagicMock(spec=["stat_object"])
    mock_inner_client.stat_object = MagicMock(return_value=mock_stat)
    mock_client.client = mock_inner_client

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        with pytest.raises(ExternalServiceError, match="verify"):
            await sync_dataset_to_s3(dataset, mock_jsonl_file, mock_client)


@pytest.mark.asyncio
async def test_download_from_s3_success():
    """Test successful dataset download from S3."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/test-dataset.jsonl"

    content = b'{"text": "test"}\n{"text": "test2"}'
    mock_client = MagicMock(spec=MinioClient)
    mock_client.download_object = MagicMock(return_value=content)

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        file_name, result_content = await download_from_s3(dataset, mock_client)

    assert file_name == "test-dataset.jsonl"
    assert result_content == content

    # Verify download_object was called with correct parameters
    mock_client.download_object.assert_called_once_with(
        bucket_name="test-bucket", object_name="test-namespace/datasets/test-dataset.jsonl"
    )


@pytest.mark.asyncio
async def test_download_from_s3_not_found():
    """Test download fails when file doesn't exist in S3."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/missing.jsonl"

    mock_client = MagicMock(spec=MinioClient)
    # Simulate S3 NoSuchKey error
    s3_error = S3Error(
        code="NoSuchKey",
        message="The specified key does not exist",
        resource="/test-bucket/test-namespace/datasets/missing.jsonl",
        request_id="test-request-id",
        host_id="test-host-id",
        response=MagicMock(spec=["status"], status=404),
    )
    mock_client.download_object = MagicMock(side_effect=s3_error)

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        # S3Error with NoSuchKey gets mapped to NotFoundException
        with pytest.raises(NotFoundException, match="File not found"):
            await download_from_s3(dataset, mock_client)


@pytest.mark.asyncio
async def test_download_from_s3_nested_path():
    """Test download correctly extracts filename from nested path."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "project-name/datasets/subfolder/nested-file.jsonl"

    content = b'{"text": "nested"}'
    mock_client = MagicMock(spec=MinioClient)
    mock_client.download_object = MagicMock(return_value=content)

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        file_name, result_content = await download_from_s3(dataset, mock_client)

    # Should extract just the filename
    assert file_name == "nested-file.jsonl"


@pytest.mark.asyncio
async def test_delete_from_s3_success():
    """Test successful dataset deletion from S3."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/test-dataset.jsonl"

    mock_client = MagicMock(spec=MinioClient)
    mock_client.delete_object = MagicMock()

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        await delete_from_s3(dataset, mock_client)

    # Verify delete_object was called with correct parameters
    mock_client.delete_object.assert_called_once_with(
        bucket_name="test-bucket", object_name="test-namespace/datasets/test-dataset.jsonl"
    )


@pytest.mark.asyncio
async def test_delete_from_s3_not_found():
    """Test delete handles non-existent files."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/missing.jsonl"

    mock_client = MagicMock(spec=MinioClient)
    # Simulate S3 NoSuchKey error
    s3_error = S3Error(
        code="NoSuchKey",
        message="The specified key does not exist",
        resource="/test-bucket/test-namespace/datasets/missing.jsonl",
        request_id="test-request-id",
        host_id="test-host-id",
        response=MagicMock(spec=["status"], status=404),
    )
    mock_client.delete_object = MagicMock(side_effect=s3_error)

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        # S3Error with NoSuchKey gets mapped to NotFoundException
        with pytest.raises(NotFoundException, match="File not found"):
            await delete_from_s3(dataset, mock_client)


@pytest.mark.asyncio
async def test_delete_from_s3_access_denied():
    """Test delete fails with appropriate error when access is denied."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.path = "test-namespace/datasets/protected.jsonl"

    mock_client = MagicMock(spec=MinioClient)
    # Simulate S3 AccessDenied error
    s3_error = S3Error(
        code="AccessDenied",
        message="Access Denied",
        resource="/test-bucket/test-namespace/datasets/protected.jsonl",
        request_id="test-request-id",
        host_id="test-host-id",
        response=MagicMock(spec=["status"], status=403),
    )
    mock_client.delete_object = MagicMock(side_effect=s3_error)

    with patch("app.datasets.utils.MINIO_BUCKET", "test-bucket"):
        # S3Error with AccessDenied gets mapped to ForbiddenException
        with pytest.raises(ForbiddenException, match="Access denied"):
            await delete_from_s3(dataset, mock_client)
