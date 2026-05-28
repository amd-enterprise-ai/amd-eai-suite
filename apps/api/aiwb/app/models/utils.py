# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import os

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from api_common.exceptions import ValidationException

from ..datasets.utils import slugify
from ..minio import MinioClient
from ..minio.client import handle_s3_operation
from ..minio.config import MINIO_BUCKET, MINIO_MAX_ATTEMPTS, MINIO_MAX_WAIT, MINIO_MIN_WAIT


class InvalidPathError(ValidationException):
    """Exception raised when a path doesn't follow project scoping conventions"""

    pass


def get_finetuned_model_weights_path(base_canonical_name: str, finetuning_name: str, project_name: str) -> str:
    slugified_project = slugify(project_name)
    return os.path.join(slugified_project, "finetuned-models", base_canonical_name, finetuning_name)


@retry(
    wait=wait_exponential(multiplier=1, min=MINIO_MIN_WAIT, max=MINIO_MAX_WAIT),
    stop=stop_after_attempt(MINIO_MAX_ATTEMPTS),
    reraise=True,
)
async def delete_from_s3(prefix: str, client: MinioClient, model_name: str = "") -> None:
    with handle_s3_operation("deleting model weights", f"s3://{MINIO_BUCKET}/{prefix}", model_name):
        await asyncio.to_thread(client.delete_objects, bucket_name=MINIO_BUCKET, prefix=prefix)
        logger.info(f"Successfully deleted model weights from S3: {prefix}")
