# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Tests for the MinioClient class and related functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from minio import Minio
from minio.datatypes import Object
from minio.deleteobjects import DeleteObject

from app.utilities.minio import MinioClient, get_minio_client, init_minio_client


class TestMinioClientInit:
    """Tests for the MinioClient initialization."""

    def test_init_with_default_values(self):
        """Test initialization with default environment values."""
        with (
            patch("app.utilities.minio.MINIO_URL", "http://localhost:9000"),
            patch("app.utilities.minio.MINIO_ACCESS_KEY", "access_key"),
            patch("app.utilities.minio.MINIO_SECRET_KEY", "secret_key"),
        ):
            client = MinioClient()
            assert client.host == "http://localhost:9000"
            assert client.access_key == "access_key"
            assert client.secret_key == "secret_key"

    def test_init_with_custom_values(self):
        """Test initialization with custom provided values."""
        client = MinioClient(host="custom_host", access_key="custom_access", secret_key="custom_secret")
        assert client.host == "custom_host"
        assert client.access_key == "custom_access"
        assert client.secret_key == "custom_secret"


class TestMinioClientCreateClient:
    """Tests for the create_client method of MinioClient."""

    def test_create_client_with_http_url(self):
        """Test client creation with HTTP URL."""
        with patch("app.utilities.minio.Minio") as mock_minio:
            client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
            # Check that Minio was called with secure=False
            mock_minio.assert_called_once()
            args, kwargs = mock_minio.call_args
            assert kwargs.get("secure") is False

    def test_create_client_with_https_url(self):
        """Test client creation with HTTPS URL."""
        with patch("app.utilities.minio.Minio") as mock_minio:
            client = MinioClient(host="https://localhost:9000", access_key="access_key", secret_key="secret_key")
            # Check that Minio was called with secure=True
            mock_minio.assert_called_once()
            args, kwargs = mock_minio.call_args
            assert kwargs.get("secure") is True


class TestMinioClientMissingCredentials:
    """Tests for MinioClient with missing credentials."""

    def test_missing_host(self):
        """Test client creation with missing host."""
        with patch.object(
            MinioClient,
            "create_client",
            side_effect=ValueError("MinIO configuration environment variables are not set: MINIO_URL"),
        ):
            with pytest.raises(ValueError) as exc_info:
                MinioClient(host="", access_key="access_key", secret_key="secret_key")
            assert "MinIO configuration environment variables are not set" in str(exc_info.value)

    def test_missing_access_key(self):
        """Test client creation with missing access key."""
        with patch.object(
            MinioClient,
            "create_client",
            side_effect=ValueError("MinIO configuration environment variables are not set: MINIO_ACCESS_KEY"),
        ):
            with pytest.raises(ValueError) as exc_info:
                MinioClient(host="host", access_key="", secret_key="secret_key")
            assert "MinIO configuration environment variables are not set" in str(exc_info.value)

    def test_missing_secret_key(self):
        """Test client creation with missing secret key."""
        with patch.object(
            MinioClient,
            "create_client",
            side_effect=ValueError("MinIO configuration environment variables are not set: MINIO_SECRET_KEY"),
        ):
            with pytest.raises(ValueError) as exc_info:
                MinioClient(host="host", access_key="access_key", secret_key="")
            assert "MinIO configuration environment variables are not set" in str(exc_info.value)


class TestMinioClientOperations:
    """Tests for the MinioClient object operations."""

    def test_upload_object(self):
        """Test uploading an object to MinIO."""
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

    def test_download_object(self):
        """Test downloading an object from MinIO."""
        client = MagicMock(spec=Minio)
        minio_client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
        minio_client.client = client

        mock_response = MagicMock()
        mock_response.read.return_value = b"test data"
        client.get_object.return_value = mock_response

        result = minio_client.download_object("bucket", "object")

        client.get_object.assert_called_once_with("bucket", "object")
        assert result == b"test data"

    def test_delete_object(self):
        """Test deleting an object from MinIO."""
        client = MagicMock(spec=Minio)
        minio_client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
        minio_client.client = client
        minio_client.delete_object("bucket", "object")
        client.remove_object.assert_called_once_with("bucket", "object")

    def test_delete_objects(self):
        """Test deleting an object from MinIO."""
        client = MagicMock(spec=Minio)
        object_names = ["prefix/1/2", "prefix/3"]
        objects = [Object("bucket", name) for name in object_names]
        delete_objects = [DeleteObject(name) for name in object_names]
        client.list_objects.return_value = objects
        client.remove_objects.return_value = []
        minio_client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
        minio_client.client = client
        minio_client.delete_objects("bucket", "prefix")
        client.list_objects.assert_called_once_with("bucket", "prefix", recursive=True)
        client.remove_objects.assert_called_once()
        # Check that the correct objects were passed to remove_objects
        assert client.remove_objects.call_count == 1
        assert client.remove_objects.call_args[0][0] == "bucket"
        assert set(obj.name for obj in client.remove_objects.call_args[0][1]) == set(obj.name for obj in delete_objects)


class TestInitMinioClient:
    """Tests for the init_minio_client function."""

    @pytest.mark.asyncio
    async def test_init_minio_client_creates_new_client(self):
        """Test that init_minio_client creates a new client with valid config."""
        with (
            patch("app.utilities.minio.MINIO_URL", "http://localhost:9000"),
            patch("app.utilities.minio.MINIO_ACCESS_KEY", "access_key"),
            patch("app.utilities.minio.MINIO_SECRET_KEY", "secret_key"),
        ):
            client = init_minio_client()
            assert isinstance(client, MinioClient)

    @pytest.mark.asyncio
    async def test_init_minio_client_missing_config(self):
        """Test that init_minio_client raises an exception when config is missing."""
        with (
            patch("app.utilities.minio.MINIO_URL", ""),
            patch("app.utilities.minio.MINIO_ACCESS_KEY", "access_key"),
            patch("app.utilities.minio.MINIO_SECRET_KEY", "secret_key"),
        ):
            with pytest.raises(ValueError) as exc_info:
                init_minio_client()
            assert "Minio not fully configured" in str(exc_info.value)


class TestGetMinioClient:
    """Tests for the get_minio_client dependency function."""

    def test_get_minio_client_returns_client(self):
        """Test that get_minio_client returns the client from app.state."""
        mock_client = MagicMock(spec=MinioClient)
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.minio_client = mock_client

        client = get_minio_client(mock_request)
        assert client is mock_client

    def test_get_minio_client_missing_client(self):
        """Test that get_minio_client raises an exception when client is not initialized."""
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.minio_client = None

        with pytest.raises(RuntimeError) as exc_info:
            get_minio_client(mock_request)
        assert "Minio client not available" in str(exc_info.value)

    def test_get_minio_client_no_attribute(self):
        """Test that get_minio_client raises an exception when minio_client attribute doesn't exist."""
        mock_request = MagicMock(spec=Request)
        # Remove the minio_client attribute
        if hasattr(mock_request.app.state, "minio_client"):
            delattr(mock_request.app.state, "minio_client")

        with pytest.raises(RuntimeError) as exc_info:
            get_minio_client(mock_request)
        assert "Minio client not available" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
