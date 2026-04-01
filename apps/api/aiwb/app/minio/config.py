# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration for MinIO object storage."""

import os

# ============================================================================
# MinIO / Object Storage Configuration
# ============================================================================
MINIO_URL = os.getenv("MINIO_URL", "http://minio.minio-tenant-default.svc.cluster.local:80")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "default-bucket")
MINIO_MAX_ATTEMPTS = int(os.getenv("MINIO_MAX_ATTEMPTS", "3"))
MINIO_MIN_WAIT = int(os.getenv("MINIO_MIN_WAIT", "4"))
MINIO_MAX_WAIT = int(os.getenv("MINIO_MAX_WAIT", "60"))
