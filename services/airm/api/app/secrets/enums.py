# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class SecretScope(StrEnum):
    ORGANIZATION = "Organization"
    PROJECT = "Project"


class SecretType(StrEnum):
    EXTERNAL = "External"
    KUBERNETES_SECRET = "KubernetesSecret"


class SecretUseCase(StrEnum):
    HUGGING_FACE = "HuggingFace"


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
