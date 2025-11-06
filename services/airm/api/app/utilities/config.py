# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_URL = os.getenv("MINIO_URL", "http://minio.minio-tenant-default.svc.cluster.local:80")
MINIO_MAX_ATTEMPTS = int(os.getenv("MINIO_MAX_ATTEMPTS", 3))
MINIO_MIN_WAIT = int(os.getenv("MINIO_MIN_WAIT", 4))
MINIO_MAX_WAIT = int(os.getenv("MINIO_MAX_WAIT", 60))

MINIO_BUCKET = os.getenv("MINIO_BUCKET", "default-bucket")
DATASETS_PATH = os.environ.get("DATASETS_PATH", os.path.join(MINIO_BUCKET, "datasets"))

CLUSTER_AUTH_URL = os.getenv("CLUSTER_AUTH_URL", "")
CLUSTER_AUTH_ADMIN_TOKEN = os.getenv("CLUSTER_AUTH_ADMIN_TOKEN", "")
