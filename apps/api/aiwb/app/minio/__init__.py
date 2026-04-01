# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from fastapi import Request
from loguru import logger

from .client import MinioClient
from .config import MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_URL


def init_minio_client() -> MinioClient | None:
    """Initialize Minio client. This will be called at application startup.

    Returns None if initialization fails.
    """
    try:
        if not MINIO_ACCESS_KEY or not MINIO_URL or not MINIO_SECRET_KEY:
            logger.warning("Minio not fully configured. Minio features will be unavailable.")
            return None

        client = MinioClient(
            host=MINIO_URL,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
        )

        logger.info(f"Connected to Minio server at {MINIO_URL}")
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize Minio client: {e}")
        return None


def get_minio_client(request: Request) -> MinioClient:
    """FastAPI dependency to get the initialized Minio client from app.state."""
    if not hasattr(request.app.state, "minio_client") or request.app.state.minio_client is None:
        logger.error("Minio client not initialized in app.state. Check Minio configuration.")
        raise RuntimeError("Minio client not available. Minio may not be configured or initialization failed.")
    return request.app.state.minio_client
