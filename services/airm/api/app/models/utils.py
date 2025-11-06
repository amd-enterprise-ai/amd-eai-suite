# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import os

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..datasets.utils import slugify
from ..models.models import InferenceModel
from ..utilities.config import MINIO_BUCKET, MINIO_MAX_ATTEMPTS, MINIO_MAX_WAIT, MINIO_MIN_WAIT
from ..utilities.exceptions import ValidationException
from ..utilities.minio import MinioClient, handle_s3_operation


def format_model_path(model_path: str) -> str:
    """Format a model path to be a valid S3 path."""
    if "://" in model_path:
        return model_path
    return f"s3://{model_path}"


class InvalidPathError(ValidationException):
    """Exception raised when a path doesn't follow project scoping conventions"""

    pass


def validate_project_scoped_path(path: str, project_name: str) -> None:
    """
    Validates that a provided path follows the project-scoped convention.

    Args:
        path: The path to validate (can include bucket prefix)
        project_name: The name of the project

    Raises:
        InvalidPathError: If the path doesn't follow the project scoping convention
    """
    slugified_project = slugify(project_name)

    # Strip bucket prefix if present to get the project-scoped portion
    # Bucket names typically don't contain slashes, so we can detect them
    path_without_bucket = path
    if "/" in path:
        path_parts = path.split("/")
        # If first part looks like a bucket (no project structure), remove it
        if len(path_parts) > 1 and slugified_project in path_parts[1:]:
            # Find where the project starts and take everything from there
            for i, part in enumerate(path_parts):
                if part == slugified_project:
                    path_without_bucket = "/".join(path_parts[i:])
                    break

    path_parts = path_without_bucket.split("/")

    # Check if the slugified project name is present
    if slugified_project not in path_parts:
        raise InvalidPathError(
            f"Path must include the project name '{project_name}' (slugified as '{slugified_project}'). "
            f"Expected format: '[bucket/]{slugified_project}/models/model-name' or '[bucket/]{slugified_project}/finetuned-models/base-model/name'"
        )

    # Ensure path starts with the slugified project name (after any bucket prefix)
    if not path_without_bucket.startswith(f"{slugified_project}/"):
        raise InvalidPathError(
            f"Path must have project-scoped structure starting with '{slugified_project}/'. "
            f"Expected format: '[bucket/]{slugified_project}/models/model-name' or '[bucket/]{slugified_project}/finetuned-models/base-model/name'"
        )


def get_model_weights_path(canonical_name: str, project_name: str) -> str:
    """
    Generate the model weights path with project scoping (without bucket prefix).
    Format: {slugified_project_name}/models/{canonical_name}

    Args:
        canonical_name: The canonical name of the model
        project_name: The name of the project
    """
    slugified_project = slugify(project_name)
    return os.path.join(slugified_project, "models", canonical_name)


def get_finetuned_model_weights_path(base_canonical_name: str, finetuning_name: str, project_name: str) -> str:
    """
    Generate the finetuned model weights path with project scoping (without bucket prefix).
    Format: {slugified_project_name}/finetuned-models/{base_canonical_name}/{finetuning_name}

    Args:
        base_canonical_name: The canonical name of the base model
        finetuning_name: The name of the finetuning run
        project_name: The name of the project
    """
    slugified_project = slugify(project_name)
    return os.path.join(slugified_project, "finetuned-models", base_canonical_name, finetuning_name)


@retry(
    wait=wait_exponential(multiplier=1, min=MINIO_MIN_WAIT, max=MINIO_MAX_WAIT),
    stop=stop_after_attempt(MINIO_MAX_ATTEMPTS),
    reraise=True,
)
async def delete_from_s3(model: InferenceModel, client: MinioClient) -> None:
    """Delete model weights from S3 storage"""
    prefix = model.model_weights_path

    with handle_s3_operation("deleting model weights", f"s3://{MINIO_BUCKET}/{prefix}", model.id):
        await asyncio.to_thread(client.delete_objects, bucket_name=MINIO_BUCKET, prefix=prefix)
        logger.info(f"Successfully deleted model weight {model.id} from S3: {prefix}")
