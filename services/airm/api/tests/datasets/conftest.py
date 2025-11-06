# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Fixtures for dataset tests.
"""

import io
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasets.models import Dataset, DatasetType
from app.datasets.schemas import DatasetCreate
from app.utilities.minio import MinioClient


@pytest.fixture
def project_id():
    """Return a consistent project ID for tests."""
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def cluster_id():
    """Return a consistent cluster ID for tests."""
    return UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def dataset_id():
    """Return a consistent dataset ID for tests."""
    return UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def mock_dataset(dataset_id, project_id, cluster_id):
    """Return a mock Dataset instance with default values."""
    dataset = MagicMock(spec=Dataset)
    dataset.id = dataset_id
    dataset.name = "Test Dataset"
    dataset.description = "Test dataset description"
    dataset.type = DatasetType.FINETUNING
    dataset.path = f"datasets/{project_id}/{cluster_id}/test-dataset.jsonl"
    dataset.created_by = "test@example.com"
    dataset.updated_by = "test@example.com"
    dataset.project_id = project_id
    dataset.cluster_id = cluster_id
    return dataset


@pytest.fixture
def dataset_create():
    """Return a DatasetCreate instance for testing dataset creation."""
    return DatasetCreate(
        description="Test Description",
        type=DatasetType.FINETUNING,
        path="s3://bucket/test-dataset.jsonl",
    )


@pytest.fixture
def mock_jsonl_file():
    """Create a mock JSONL file for testing."""
    file_content = b'{"text": "test"}\n{"text": "test2"}'
    return UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession for testing."""
    mock = AsyncMock(spec=AsyncSession)
    mock.flush = AsyncMock()
    mock.refresh = AsyncMock()
    return mock


@pytest.fixture
def minio_environment(monkeypatch):
    """Set up necessary environment variables for MinIO testing."""
    monkeypatch.setattr("app.utilities.config.MINIO_ACCESS_KEY", "test-access-key")
    monkeypatch.setattr("app.utilities.config.MINIO_URL", "http://localhost:9000")
    monkeypatch.setattr("app.utilities.config.MINIO_SECRET_KEY", "test-secret-key")
    monkeypatch.setattr("app.utilities.config.MINIO_BUCKET", "test-bucket")
    monkeypatch.setattr("app.utilities.config.DATASETS_PATH", "test-bucket/datasets")
    return monkeypatch


@pytest.fixture
def mock_minio_client():
    """Create a mock MinioClient for testing."""
    client = MagicMock(spec=MinioClient)
    client.upload_object = MagicMock()
    client.download_object = MagicMock(return_value=b'{"text": "test"}\n{"text": "test2"}')
    client.client.stat_object = MagicMock(return_value=MagicMock(size=len(b'{"text": "test"}\n{"text": "test2"}')))
    return client
