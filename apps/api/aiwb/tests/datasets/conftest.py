# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Fixtures for dataset tests.

Note: Shared MinIO fixtures (minio_environment, mock_minio_client) are defined
in the parent tests/conftest.py since they are used by both datasets and models tests.
"""

import io
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile

from app.datasets.models import DatasetType
from app.datasets.schemas import DatasetResponse


@pytest.fixture
def dataset_id():
    """Return a consistent dataset ID for tests."""
    return UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def mock_jsonl_file():
    """Create a mock JSONL file for testing."""
    file_content = b'{"text": "test"}\n{"text": "test2"}'
    return UploadFile(filename="test.jsonl", file=io.BytesIO(file_content))


def make_dataset_response(
    id: UUID | None = None,
    name: str = "Test Dataset",
    description: str = "Test dataset description",
    path: str = "test-namespace/datasets/test-dataset.jsonl",
    type: DatasetType = DatasetType.FINETUNING,
    namespace: str = "test-namespace",
    created_at: str = "2025-01-01T00:00:00Z",
    updated_at: str = "2025-01-01T00:00:00Z",
    created_by: str = "test@example.com",
    updated_by: str = "test@example.com",
) -> DatasetResponse:
    """
    Create a DatasetResponse for testing router responses.

    This factory reduces code duplication in router tests by providing
    sensible defaults for all fields while allowing customization.

    Args:
        id: Dataset UUID (auto-generated if not provided)
        name: Human-readable name for the dataset
        description: Description of the dataset
        path: S3 path to the dataset file
        type: Type of dataset (default: FINETUNING)
        namespace: Namespace the dataset belongs to
        created_at: Creation timestamp (ISO format string)
        updated_at: Update timestamp (ISO format string)
        created_by: Email of the user who created the dataset
        updated_by: Email of the user who last updated the dataset

    Returns:
        DatasetResponse instance ready for use in router tests

    Example:
        # Create with defaults
        response = make_dataset_response()

        # Create with custom values
        response = make_dataset_response(
            name="Custom Dataset",
            type=DatasetType.EVALUATION,
        )
    """
    return DatasetResponse(
        id=id or uuid4(),
        name=name,
        description=description,
        path=path,
        type=type,
        namespace=namespace,
        created_at=created_at,
        updated_at=updated_at,
        created_by=created_by,
        updated_by=updated_by,
    )
