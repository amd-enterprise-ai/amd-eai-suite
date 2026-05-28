# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


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


class ProjectSecretStatus(StrEnum):
    PENDING = "Pending"
    SYNCED = "Synced"
    FAILED = "Failed"
    SYNCED_ERROR = "SyncedError"
    DELETE_FAILED = "DeleteFailed"
    DELETED = "Deleted"
    DELETING = "Deleting"
    UNKNOWN = "Unknown"


class SecretKind(StrEnum):
    EXTERNAL_SECRET = "ExternalSecret"
    KUBERNETES_SECRET = "KubernetesSecret"


class SecretScope(StrEnum):
    ORGANIZATION = "Organization"
    PROJECT = "Project"
