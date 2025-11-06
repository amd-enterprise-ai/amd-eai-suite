# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.datasets.models import Dataset
from app.datasets.utils import (
    download_from_s3,
    extract_bucket_and_key,
    get_object_key,
    sync_dataset_to_s3,
    validate_jsonl,
    verify_s3_sync,
)
from app.utilities.exceptions import ExternalServiceError, ForbiddenException, NotFoundException, ValidationException
from app.utilities.minio import (
    MinioClient,
)


def test_minio_client_init():
    # Test with default values
    with (
        patch("app.utilities.minio.MINIO_URL", "http://localhost:9000"),
        patch("app.utilities.minio.MINIO_ACCESS_KEY", "minioadmin"),
        patch("app.utilities.minio.MINIO_SECRET_KEY", "minioadmin"),
    ):
        client = MinioClient()
        assert client.host == "http://localhost:9000"
        assert client.access_key == "minioadmin"
        assert client.secret_key == "minioadmin"

    # Test with custom values
    client = MinioClient(host="custom_host", access_key="custom_access", secret_key="custom_secret")
    assert client.host == "custom_host"
    assert client.access_key == "custom_access"
    assert client.secret_key == "custom_secret"


def test_minio_client_create_client():
    # Test with HTTP URL
    with patch("app.utilities.minio.Minio") as mock_minio:
        client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
        # Check that Minio was called with secure=False
        mock_minio.assert_called_once()
        args, kwargs = mock_minio.call_args
        assert kwargs.get("secure") is False

    # Test with HTTPS test_sync_dataset_to_s3_success
    with patch("app.utilities.minio.Minio") as mock_minio:
        client = MinioClient(host="https://localhost:9000", access_key="access_key", secret_key="secret_key")
        # Check that Minio was called with secure=True
        mock_minio.assert_called_once()
        args, kwargs = mock_minio.call_args
        assert kwargs.get("secure") is True


def test_minio_client_create_client_missing_credentials():
    with patch.object(
        MinioClient,
        "create_client",
        side_effect=ValueError("MinIO configuration environment variables are not set: MINIO_URL"),
    ):
        with pytest.raises(ValueError) as exc_info:
            MinioClient(host="", access_key="access_key", secret_key="secret_key")
        assert "MinIO configuration environment variables are not set" in str(exc_info.value)

    with patch.object(
        MinioClient,
        "create_client",
        side_effect=ValueError("MinIO configuration environment variables are not set: MINIO_ACCESS_KEY"),
    ):
        with pytest.raises(ValueError) as exc_info:
            MinioClient(host="host", access_key="", secret_key="secret_key")
        assert "MinIO configuration environment variables are not set" in str(exc_info.value)

    with patch.object(
        MinioClient,
        "create_client",
        side_effect=ValueError("MinIO configuration environment variables are not set: MINIO_SECRET_KEY"),
    ):
        with pytest.raises(ValueError) as exc_info:
            MinioClient(host="host", access_key="access_key", secret_key="")
        assert "MinIO configuration environment variables are not set" in str(exc_info.value)


def test_minio_client_upload_object():
    client = MagicMock(spec=Minio)
    minio_client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
    minio_client.client = client

    data = b"test data"
    minio_client.upload_object("bucket", "object", data)

    client.put_object.assert_called_once()
    args, kwargs = client.put_object.call_args
    assert args[0] == "bucket"
    assert args[1] == "object"
    assert kwargs["length"] == len(data)


def test_minio_client_download_object():
    client = MagicMock(spec=Minio)
    minio_client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
    minio_client.client = client

    mock_response = MagicMock()
    mock_response.read.return_value = b"test data"
    client.get_object.return_value = mock_response

    result = minio_client.download_object("bucket", "object")

    client.get_object.assert_called_once_with("bucket", "object")
    assert result == b"test data"


# Tests for the old get_minio_client function have been removed since it's replaced with dependency injection


def test_extract_bucket_and_key():
    # Valid path
    bucket, key = extract_bucket_and_key("bucket/path/to/file.jsonl")
    assert bucket == "bucket"
    assert key == "path/to/file.jsonl"

    # Invalid path
    with pytest.raises(ValueError) as exc_info:
        extract_bucket_and_key("invalid-path")
    assert "Invalid path format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_verify_s3_sync_success():
    client = MagicMock(spec=MinioClient)
    client.client = MagicMock()  # Add the client attribute
    client.client.stat_object.return_value = MagicMock(size=10)

    result = await verify_s3_sync(client, "bucket", "object", b"0123456789")

    client.client.stat_object.assert_called_once_with("bucket", "object")
    assert result is True


@pytest.mark.asyncio
async def test_verify_s3_sync_size_mismatch():
    client = MagicMock(spec=MinioClient)
    client.client = MagicMock()  # Add the client attribute
    client.client.stat_object.return_value = MagicMock(size=5)

    with pytest.raises(ExternalServiceError) as exc_info:
        await verify_s3_sync(client, "bucket", "object", b"0123456789")

    assert "Failed to verify verifying upload" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_dataset_to_s3_success():
    # Arrange
    dataset = MagicMock()
    dataset.id = "test-id"
    dataset.path = "datasets/test-id.jsonl"  # Set the path explicitly

    file_content = b'{"text": "test"}\n{"text": "test2"}'
    file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

    mock_client = MagicMock(spec=MinioClient)

    with (
        patch("app.datasets.utils.verify_s3_sync", return_value=True),
    ):
        # Act
        result = await sync_dataset_to_s3(dataset, file, mock_client)

        # Assert
        mock_client.upload_object.assert_called_once()
        assert result == "default-bucket/datasets/test-id.jsonl"


@pytest.mark.asyncio
async def test_sync_dataset_to_s3_s3_error():
    # Arrange
    dataset = MagicMock()
    dataset.id = "test-id"
    dataset.path = "datasets/test-id.jsonl"

    file_content = b'{"text": "test"}\n{"text": "test2"}'
    file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

    mock_client = MagicMock(spec=MinioClient)
    # Create a proper S3Error with all required arguments
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
        # Act & Assert
        with pytest.raises(ForbiddenException):  # AccessDenied maps to ForbiddenException
            await sync_dataset_to_s3(dataset, file, mock_client)


@pytest.mark.asyncio
async def test_download_from_s3_success():
    # Arrange
    dataset = MagicMock()
    dataset.id = "test-id"
    # Update this to match the new behavior - path now only contains the key portion
    dataset.path = "datasets/test-id.jsonl"

    mock_client = MagicMock(spec=MinioClient)
    mock_client.download_object.return_value = b'{"text": "test"}\n{"text": "test2"}'

    # Act
    file_name, content = await download_from_s3(dataset, mock_client)

    # Assert
    # The bucket is now MINIO_BUCKET and object_name is dataset.path directly
    mock_client.download_object.assert_called_once_with(
        bucket_name="default-bucket", object_name="datasets/test-id.jsonl"
    )
    assert file_name == "test-id.jsonl"
    assert content == b'{"text": "test"}\n{"text": "test2"}'


@pytest.mark.asyncio
async def test_download_from_s3_error():
    # Arrange
    dataset = MagicMock()
    dataset.id = "test-id"
    dataset.path = "datasets/test-id.jsonl"  # Path now only contains the key portion

    mock_client = MagicMock(spec=MinioClient)
    # Create a proper S3Error with all required arguments
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
        # Act & Assert
        with pytest.raises(NotFoundException):  # NoSuchKey maps to NotFoundException
            await download_from_s3(dataset, mock_client)


def test_validate_jsonl_success():
    # Valid file
    file_content = b'{"text": "test"}\n{"text": "test2"}'
    file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

    with patch("app.utilities.config.MAX_FILE_SIZE_BYTES", 1000):
        result = validate_jsonl(file)
        assert result is True


def test_validate_jsonl_invalid_extension():
    # Invalid extension
    file_content = b'{"text": "test"}\n{"text": "test2"}'
    file = UploadFile(filename="test.txt", file=io.BytesIO(file_content))

    with pytest.raises(ValidationException) as exc_info:
        validate_jsonl(file)

    assert "Invalid file format" in exc_info.value.message


@pytest.fixture
def mock_dataset():
    dataset = MagicMock(spec=Dataset)
    dataset.id = "test-id"
    dataset.author = "test-org"
    dataset.created_at = "2025-01-01"
    dataset.updated_at = "2025-01-02"
    return dataset


@pytest.mark.asyncio
async def test_sync_and_download_success(mock_dataset):
    # Configure mocked MinioClient
    mock_minio_instance = MagicMock(spec=MinioClient)
    mock_minio_instance.client = MagicMock(spec=Minio)  # Add the client attribute
    content = b'{"field1": "value1"}\n{"field2": "value2"}'

    # Set the path attribute on the mock dataset
    mock_dataset.path = "datasets/test-id.jsonl"

    upload = UploadFile(filename="test.jsonl", file=io.BytesIO(content))

    # Configure mock to match the file we're uploading
    mock_stat = MagicMock()
    mock_stat.size = len(content)
    mock_minio_instance.client.stat_object.return_value = mock_stat

    # Execute
    path = await sync_dataset_to_s3(mock_dataset, upload, mock_minio_instance)

    # Verify file was uploaded with correct parameters
    mock_minio_instance.upload_object.assert_called_once()
    call_args = mock_minio_instance.upload_object.call_args[1]
    assert call_args["bucket_name"] == "default-bucket"
    assert call_args["object_name"] == "datasets/test-id.jsonl"

    # Verify dataset was updated with bucket path
    assert path == "default-bucket/datasets/test-id.jsonl"

    # Test download - path is already set on the mock_dataset
    mock_minio_instance.download_object.return_value = content
    file_name, file_content = await download_from_s3(mock_dataset, mock_minio_instance)

    mock_minio_instance.download_object.assert_called_once()
    call_args = mock_minio_instance.download_object.call_args[1]
    assert call_args["bucket_name"] == "default-bucket"
    assert call_args["object_name"] == "datasets/test-id.jsonl"
    assert file_name == "test-id.jsonl"
    assert file_content == content


def test_extract_bucket_and_key_with_path():
    # Test extract_bucket_and_key function directly with a specific path
    path = "custom-bucket/path/to/file.jsonl"
    bucket, key = extract_bucket_and_key(path)
    assert bucket == "custom-bucket"
    assert key == "path/to/file.jsonl"

    path = "another-bucket/another/path/file.txt"
    bucket, key = extract_bucket_and_key(path)
    assert bucket == "another-bucket"
    assert key == "another/path/file.txt"


def test_slugify():
    """Test the slugify function for creating path-safe dataset names"""
    from app.datasets.utils import slugify

    assert slugify("Test Dataset") == "test-dataset"

    assert slugify("Test! @#$%^&*() Dataset") == "test-dataset"

    assert slugify("Test!!!Dataset") == "test-dataset"

    assert slugify("---Test Dataset---") == "test-dataset"

    assert slugify("Test Dataset 123") == "test-dataset-123"

    assert slugify("Téśt Dàtáśét") == "téśt-dàtáśét"

    assert slugify("test-dataset") == "test-dataset"


def test_derive_name_from_path():
    """Test deriving dataset names from S3 paths"""
    from app.datasets.utils import derive_name_from_path

    assert derive_name_from_path("datasets/test-dataset.jsonl") == "Test Dataset"

    assert derive_name_from_path("datasets/user/cluster/test-dataset.jsonl") == "Test Dataset"

    assert derive_name_from_path("datasets/test-dataset.json") == "Test Dataset"
    assert derive_name_from_path("datasets/test-dataset.csv") == "Test Dataset"
    assert derive_name_from_path("datasets/test-dataset.txt") == "Test Dataset"

    assert derive_name_from_path("datasets/test_dataset.jsonl") == "Test Dataset"

    assert derive_name_from_path("datasets/test-dataset") == "Test Dataset"

    assert derive_name_from_path("datasets/test-complex-dataset_name.jsonl") == "Test Complex Dataset Name"


def test_clean_s3_path():
    """Test cleaning and validating S3 paths"""
    from app.datasets.utils import clean_s3_path

    assert clean_s3_path("datasets/test.jsonl") == "datasets/test.jsonl"

    assert clean_s3_path("s3://bucket/datasets/test.jsonl") == "bucket/datasets/test.jsonl"

    # Test with matching bucket prefix - should extract just the key
    assert clean_s3_path("default-bucket/datasets/test.jsonl") == "datasets/test.jsonl"

    # Test with different bucket - should return the path as is
    with patch("app.utilities.config.MINIO_BUCKET", "correct-bucket"):
        # Different bucket name is just treated as part of the path
        assert clean_s3_path("wrong-bucket/datasets/test.jsonl") == "wrong-bucket/datasets/test.jsonl"


def test_get_object_key():
    """Test the get_object_key function that uses project name"""

    # Simple name
    assert get_object_key("Test Dataset", "Project A") == "project-a/datasets/test-dataset.jsonl"

    # Complex names
    assert (
        get_object_key("Complex Name with Spaces!", "Complex Project Name")
        == "complex-project-name/datasets/complex-name-with-spaces.jsonl"
    )

    # With special characters
    assert (
        get_object_key("Dataset with !@#$%^&*()", "Project with !@#$%^&*()")
        == "project-with/datasets/dataset-with.jsonl"
    )
