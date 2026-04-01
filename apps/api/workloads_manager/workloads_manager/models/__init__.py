# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Models package for workloads manager."""

from .base import FileProcessingResult, ProcessingStats, ProcessingStatus
from .overlay import OverlayData, OverlayType, OverlayUploadData
from .workload import Workload, WorkloadMetadata, WorkloadRegistrationResult

__all__ = [
    # Base models
    "ProcessingStatus",
    "ProcessingStats",
    "FileProcessingResult",
    # Workload models
    "Workload",
    "WorkloadMetadata",
    "WorkloadRegistrationResult",
    # Overlay models
    "OverlayData",
    "OverlayType",
    "OverlayUploadData",
    # API models
    "APIResponse",
]
