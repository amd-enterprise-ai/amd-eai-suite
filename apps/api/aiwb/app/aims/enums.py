# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Enums for AIMClusterModel resources."""

from enum import StrEnum


class AIMClusterModelStatus(StrEnum):
    """Status of an AIMClusterModel resource in the cluster."""

    NOT_AVAILABLE = "NotAvailable"
    PENDING = "Pending"
    PROGRESSING = "Progressing"
    READY = "Ready"
    DEGRADED = "Degraded"
    FAILED = "Failed"
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
