# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import io
from collections.abc import Generator
from contextlib import contextmanager

import urllib3
from fastapi import Request
from loguru import logger
from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from .config import (
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_URL,
)
from .exceptions import (
    BaseAirmException,
    ExternalServiceError,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)


class MinioClient:
    def __init__(self, host: str = None, access_key: str = None, secret_key: str = None):
        self.host = host or MINIO_URL
        self.access_key = access_key or MINIO_ACCESS_KEY
        self.secret_key = secret_key or MINIO_SECRET_KEY
        self.client = self.create_client()

    def create_client(self):
        credentials = {
            "MINIO_URL": self.host,
            "MINIO_ACCESS_KEY": self.access_key,
            "MINIO_SECRET_KEY": self.secret_key,
        }

        missing_credentials = [key for key, value in credentials.items() if not value]
        if missing_credentials:
            raise ValueError(f"MinIO configuration environment variables are not set: {', '.join(missing_credentials)}")

        # Strip any URL scheme from host
        minio_host = credentials["MINIO_URL"].replace("https://", "").replace("http://", "")

        # Determine if we should use HTTPS based on original URL
        use_https = not credentials["MINIO_URL"].startswith("http://")

        if use_https:
            urllib3.disable_warnings()

        return Minio(
            minio_host,
            access_key=credentials["MINIO_ACCESS_KEY"],
            secret_key=credentials["MINIO_SECRET_KEY"],
            secure=use_https,
            cert_check=False,
        )

    def upload_object(self, bucket_name: str, object_name: str, data: bytes) -> None:
        buffer = io.BytesIO(data)
        self.client.put_object(bucket_name, object_name, buffer, length=len(data))
        buffer.close()

    def download_object(self, bucket_name: str, object_name: str) -> bytes:
        return self.client.get_object(bucket_name, object_name).read()

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """
        Delete an object from the specified bucket.
        """
        self.client.remove_object(bucket_name, object_name)
        logger.info(f"Successfully deleted object {object_name} from bucket {bucket_name}")

    def delete_objects(self, bucket_name: str, prefix: str) -> None:
        """
        Delete all objects in prefix from the specified bucket.
        """
        objects = list(self.client.list_objects(bucket_name, prefix, recursive=True))

        if not objects:
            logger.info(f"No objects found with prefix {prefix} in bucket {bucket_name}")
            return

        delete_objects = [DeleteObject(obj.object_name) for obj in objects]
        errors = self.client.remove_objects(bucket_name, delete_objects)
        if errors:
            error_messages = [f"Error deleting {error.object_name}: {error.message}" for error in errors]
            error_message = ", ".join(error_messages)
            logger.error(f"Errors occurred while deleting objects: {error_message}")
            raise ExternalServiceError(message="Failed to delete some objects", detail=error_message)
        logger.info(
            f"Successfully deleted {len(delete_objects)} objects with prefix {prefix} from bucket {bucket_name}"
        )


class S3SyncError(Exception):
    """Custom error for S3 sync verification failures"""

    pass


def map_s3_error_to_domain_exception(s3_error: S3Error, context: str) -> BaseAirmException:
    """
    Map S3Error to appropriate domain exception based on error code.

    Args:
        s3_error: The S3Error exception from minio client
        context: Context message describing the operation (e.g., S3 path)

    Returns:
        Appropriate domain exception for the S3 error type
    """
    error_code = s3_error.code

    if error_code in ["NoSuchKey", "NoSuchBucket"]:
        return NotFoundException(message=f"File not found in storage: {context}", detail=str(s3_error))
    elif error_code == "AccessDenied":
        return ForbiddenException(message=f"Access denied to storage: {context}", detail=str(s3_error))
    elif error_code in ["InvalidRequest", "MalformedXML", "InvalidArgument"]:
        return ValidationException(message=f"Invalid storage request: {context}", detail=str(s3_error))
    else:
        # For InternalError, SlowDown, ServiceUnavailable, etc.
        return ExternalServiceError(message=f"Storage service error: {context}", detail=str(s3_error))


@contextmanager
def handle_s3_operation(operation: str, context: str, resource_id: str | None = None) -> Generator[None]:
    """
    Context manager for consistent S3 error handling and logging.

    Args:
        operation: Description of the operation being performed (e.g., "uploading dataset")
        context: S3 path or context for the operation (e.g., "s3://bucket/path/file.ext")
        resource_id: Optional resource identifier for logging (e.g., dataset.id)

    Raises:
        NotFoundException: For NoSuchKey, NoSuchBucket errors (404)
        ForbiddenException: For AccessDenied errors (403)
        ValidationException: For InvalidRequest, MalformedXML errors (400)
        ExternalServiceError: For S3 service errors or S3SyncError (502)

    Example:
        with handle_s3_operation("uploading dataset", f"s3://{bucket}/{key}", dataset.id):
            client.upload_object(bucket_name=bucket, object_name=key, data=content)
    """
    try:
        yield
    except S3Error as e:
        resource_info = f" {resource_id}" if resource_id else ""
        logger.error(f"S3 error {operation}{resource_info}: {e}")
        raise map_s3_error_to_domain_exception(e, context)
    except S3SyncError as e:
        resource_info = f" {resource_id}" if resource_id else ""
        logger.error(f"S3 sync error {operation}{resource_info}: {e}")
        raise ExternalServiceError(message=f"Failed to verify {operation}: {context}", detail=str(e))


def init_minio_client() -> MinioClient:
    """Initialize Minio client. This will be called at application startup."""
    if not MINIO_ACCESS_KEY or not MINIO_URL or not MINIO_SECRET_KEY:
        logger.error("Minio not fully configured.")
        raise ValueError("Minio not fully configured")

    client = MinioClient(
        host=MINIO_URL,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
    )

    logger.info(f"Connected to Minio server at {MINIO_URL}")
    return client


def get_minio_client(request: Request) -> MinioClient:
    """FastAPI dependency to get the initialized Minio client from app.state."""
    if not hasattr(request.app.state, "minio_client") or request.app.state.minio_client is None:
        logger.error("Minio client not initialized in app.state. Check Minio configuration.")
        raise RuntimeError("Minio client not available. Minio may not be configured or initialization failed.")
    return request.app.state.minio_client
