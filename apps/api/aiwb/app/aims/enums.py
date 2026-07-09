# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Enums for AIM CRD resources."""

from enum import StrEnum


class AIMModelStatus(StrEnum):
    """Status of an AIM(Cluster)Model resource.

    Shared between cluster-scoped and namespace-scoped AIMModel CRDs — the
    engine's Go status is `AIMModelStatus` for both.
    """

    NOT_AVAILABLE = "NotAvailable"
    PENDING = "Pending"
    PROGRESSING = "Progressing"
    READY = "Ready"
    DEGRADED = "Degraded"
    FAILED = "Failed"
    ERROR = "Error"
    DELETED = "Deleted"  # API-only status for AIMs removed from cluster


class AIMServiceStatus(StrEnum):
    """Status values for AIMService resources.

    CRD enum: Pending, Starting, Running, Degraded, Failed.
    DELETED is API-only (used by the AIM history syncer, never from K8s).
    """

    PENDING = "Pending"
    STARTING = "Starting"
    RUNNING = "Running"
    FAILED = "Failed"
    DEGRADED = "Degraded"
    DELETED = "Deleted"


class OptimizationMetric(StrEnum):
    """Performance optimization metrics for AIM deployments."""

    LATENCY = "latency"
    THROUGHPUT = "throughput"


class AIMVersionPolicy(StrEnum):
    """Version-matching policy for custom AIMModels deriving profiles from a base.

    Mirrors aim-engine's `ProfileVersionPolicy`. Controls which versions of
    matching base profiles a custom model copies from.

    - PINNED: match profiles whose `status.version` equals the model's image tag.
    - LATEST: match only the latest available `status.version`.
    - ALL: match profiles at any version.
    """

    PINNED = "pinned"
    LATEST = "latest"
    ALL = "all"


class AcceleratorType(StrEnum):
    """Accelerator family for AIMs (matches v1alpha2 AIMProfile spec.acceleratorType).

    Lowercase to mirror aim-engine's wire values; the API filter is case-sensitive.
    """

    CPU = "cpu"
    GPU = "gpu"
