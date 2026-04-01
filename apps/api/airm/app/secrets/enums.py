# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class SecretUseCase(StrEnum):
    HUGGING_FACE = "HuggingFace"
    IMAGE_PULL_SECRET = "ImagePullSecret"
    S3 = "S3"
    GENERIC = "Generic"
    DATABASE = "Database"


class SecretStatus(StrEnum):
    UNASSIGNED = "Unassigned"
    PENDING = "Pending"
    SYNCED = "Synced"
    PARTIALLY_SYNCED = "PartiallySynced"
    SYNCED_ERROR = "SyncedError"
    FAILED = "Failed"
    DELETING = "Deleting"
    DELETED = "Deleted"
    DELETE_FAILED = "DeleteFailed"
    UNKNOWN = "Unknown"
