# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Fixtures for MinIO tests."""

from unittest.mock import MagicMock

import pytest
from minio import Minio

from app.minio import MinioClient


@pytest.fixture
def mock_s3_object():
    """Create a mock object with attributes needed for S3 operations testing."""
    obj = MagicMock()
    obj.id = "test-id"
    obj.path = "test-path/test-id.jsonl"
    return obj


@pytest.fixture
def mock_minio_instance():
    """Create a mock MinioClient instance for testing."""
    mock_instance = MagicMock(spec=MinioClient)
    mock_instance.client = MagicMock(spec=Minio)
    return mock_instance
