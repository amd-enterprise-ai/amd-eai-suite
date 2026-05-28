# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class StorageScope(StrEnum):
    ORGANIZATION = "Organization"


class StorageType(StrEnum):
    S3 = "S3"


class StorageStatus(StrEnum):
    UNASSIGNED = "Unassigned"
    PENDING = "Pending"
    SYNCED = "Synced"
    PARTIALLY_SYNCED = "PartiallySynced"
    SYNCED_ERROR = "SyncedError"
    FAILED = "Failed"
    DELETING = "Deleting"
    DELETED = "Deleted"
    DELETE_FAILED = "DeleteFailed"


class ProjectStorageStatus(StrEnum):
    PENDING = "Pending"
    SYNCED = "Synced"
    FAILED = "Failed"
    SYNCED_ERROR = "SyncedError"
    DELETE_FAILED = "DeleteFailed"
    DELETED = "Deleted"
    DELETING = "Deleting"
    UNKNOWN = "Unknown"
