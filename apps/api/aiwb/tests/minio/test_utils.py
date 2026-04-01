# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Tests for MinIO utility functions including sync, download, and verification.
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from api_common.exceptions import ExternalServiceError, ForbiddenException, NotFoundException
from app.datasets.utils import (
    download_from_s3,
    sync_dataset_to_s3,
    verify_s3_sync,
)
from app.minio import MinioClient


def test_minio_client_create_client():
    # Test with HTTP URL
    with patch("app.minio.client.Minio") as mock_minio:
        client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
        # Check that Minio was called with secure=False
        mock_minio.assert_called_once()
        args, kwargs = mock_minio.call_args
        assert kwargs.get("secure") is False

    # Test with HTTPS
    with patch("app.minio.client.Minio") as mock_minio:
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


@pytest.mark.asyncio
async def test_verify_s3_sync_success() -> None:
    client = MagicMock(spec=MinioClient)
    client.client = MagicMock()
    client.client.stat_object.return_value = MagicMock(size=10)

    result = await verify_s3_sync(client, "bucket", "object", b"0123456789")

    client.client.stat_object.assert_called_once_with("bucket", "object")
    assert result is True


@pytest.mark.asyncio
async def test_verify_s3_sync_size_mismatch() -> None:
    client = MagicMock(spec=MinioClient)
    client.client = MagicMock()
    client.client.stat_object.return_value = MagicMock(size=5)

    with pytest.raises(ExternalServiceError) as exc_info:
        await verify_s3_sync(client, "bucket", "object", b"0123456789")

    assert "Failed to verify verifying upload" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_dataset_to_s3_success() -> None:
    dataset = MagicMock()
    dataset.id = "test-id"
    dataset.path = "datasets/test-id.jsonl"

    file_content = b'{"text": "test"}\n{"text": "test2"}'
    file = UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))

    mock_client = MagicMock(spec=MinioClient)

    with patch("app.datasets.utils.verify_s3_sync", return_value=True):
        result = await sync_dataset_to_s3(dataset, file, mock_client)

        mock_client.upload_object.assert_called_once()
        assert result == "default-bucket/datasets/test-id.jsonl"


@pytest.mark.asyncio
async def test_sync_dataset_to_s3_s3_error() -> None:
    dataset = MagicMock()
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

    with patch("app.minio.config.MINIO_BUCKET", "bucket"):
        with pytest.raises(ForbiddenException):
            await sync_dataset_to_s3(dataset, file, mock_client)


@pytest.mark.asyncio
async def test_download_from_s3_success() -> None:
    dataset = MagicMock()
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
async def test_download_from_s3_error() -> None:
    dataset = MagicMock()
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

    with patch("app.minio.config.MINIO_BUCKET", "bucket"):
        with pytest.raises(NotFoundException):
            await download_from_s3(dataset, mock_client)


@pytest.mark.asyncio
async def test_sync_and_download_success(mock_s3_object: MagicMock, mock_minio_instance: MagicMock) -> None:
    """Test full sync and download flow."""
    # Set path to match expected S3 structure
    mock_s3_object.path = "datasets/test-id.jsonl"

    content = b'{"field1": "value1"}\n{"field2": "value2"}'
    upload = UploadFile(filename="test.jsonl", file=io.BytesIO(content))

    # Configure mock to match the file we're uploading
    mock_stat = MagicMock()
    mock_stat.size = len(content)
    mock_minio_instance.client.stat_object.return_value = mock_stat

    # Execute upload
    path = await sync_dataset_to_s3(mock_s3_object, upload, mock_minio_instance)

    # Verify file was uploaded with correct parameters
    mock_minio_instance.upload_object.assert_called_once()
    call_args = mock_minio_instance.upload_object.call_args[1]
    assert call_args["bucket_name"] == "default-bucket"
    assert call_args["object_name"] == "datasets/test-id.jsonl"
    assert path == "default-bucket/datasets/test-id.jsonl"

    # Test download
    mock_minio_instance.download_object.return_value = content
    file_name, file_content = await download_from_s3(mock_s3_object, mock_minio_instance)

    mock_minio_instance.download_object.assert_called_once()
    call_args = mock_minio_instance.download_object.call_args[1]
    assert call_args["bucket_name"] == "default-bucket"
    assert call_args["object_name"] == "datasets/test-id.jsonl"
    assert file_name == "test-id.jsonl"
    assert file_content == content
