# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from api_common.exceptions import NotFoundException
from app.minio.client import MinioClient
from app.models.models import InferenceModel, OnboardingStatus
from app.models.utils import delete_from_s3, format_model_path, get_finetuned_model_weights_path


def test_format_model_path() -> None:
    """Test format_model_path handles various input formats."""
    # Already has protocol prefix - should be unchanged
    assert format_model_path("s3://bucket/path") == "s3://bucket/path"

    # No prefix - should add s3://
    assert format_model_path("bucket/path") == "s3://bucket/path"
    assert format_model_path("/absolute/path") == "s3:///absolute/path"

    # Empty string
    assert format_model_path("") == "s3://"

    # None should raise TypeError
    with pytest.raises(TypeError):
        format_model_path(None)  # type: ignore[arg-type]


def test_get_finetuned_model_weights_path_basic() -> None:
    """Test basic functionality of get_finetuned_model_weights_path."""
    result = get_finetuned_model_weights_path("meta-llama/Llama-3.1-8B", "my-finetune", "My Test Project")
    assert result == "my-test-project/finetuned-models/meta-llama/Llama-3.1-8B/my-finetune"


def test_get_finetuned_model_weights_path_with_special_characters() -> None:
    """Test get_finetuned_model_weights_path with special characters in project name."""
    result = get_finetuned_model_weights_path("test/model", "custom-finetune", "Test! @#$%^&*() Project")
    assert result == "test-project/finetuned-models/test/model/custom-finetune"


def test_get_finetuned_model_weights_path_with_already_slugified_name() -> None:
    """Test get_finetuned_model_weights_path with already slugified project name."""
    result = get_finetuned_model_weights_path("test/model", "custom-finetune", "test-project")
    assert result == "test-project/finetuned-models/test/model/custom-finetune"


# ============================================================================
# S3 Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_from_s3_success() -> None:
    """Test delete_from_s3 successfully deletes model weights."""
    # Create a test model
    model = InferenceModel(
        id=uuid4(),
        name="Test Model",
        namespace="test-namespace",
        canonical_name="test/model",
        model_weights_path="test-namespace/models/test-model/weights.bin",
        onboarding_status=OnboardingStatus.ready,
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Mock MinIO client
    mock_minio_client = MagicMock(spec=MinioClient)
    mock_minio_client.delete_objects = MagicMock(spec=[], return_value=None)

    # Mock asyncio.to_thread to call delete_objects synchronously
    with (
        patch("asyncio.to_thread", side_effect=lambda fn, **kwargs: fn(**kwargs)),
        patch("app.models.utils.MINIO_BUCKET", "test-bucket"),
    ):
        # Call delete_from_s3
        await delete_from_s3(model, mock_minio_client)

    # Verify delete_objects was called with correct parameters
    mock_minio_client.delete_objects.assert_called_once()
    call_args = mock_minio_client.delete_objects.call_args
    assert call_args[1]["bucket_name"] == "test-bucket"
    assert call_args[1]["prefix"] == "test-namespace/models/test-model/weights.bin"


@pytest.mark.asyncio
async def test_delete_from_s3_handles_not_found_gracefully() -> None:
    """Test delete_from_s3 handles NotFound errors from S3."""
    # Create a test model
    model = InferenceModel(
        id=uuid4(),
        name="Test Model",
        namespace="test-namespace",
        canonical_name="test/model",
        model_weights_path="test-namespace/models/missing/weights.bin",
        onboarding_status=OnboardingStatus.ready,
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Mock MinIO client to raise NotFoundException
    mock_minio_client = MagicMock(spec=MinioClient)
    mock_minio_client.delete_objects = MagicMock(spec=[], side_effect=NotFoundException("S3 object not found"))

    # Mock asyncio.to_thread to call delete_objects synchronously
    async def async_to_thread(fn, **kwargs):
        return fn(**kwargs)

    with patch("asyncio.to_thread", side_effect=async_to_thread):
        # Call delete_from_s3 - should propagate NotFoundException
        with pytest.raises(NotFoundException, match="S3 object not found"):
            await delete_from_s3(model, mock_minio_client)
