# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class WorkloadStatus(StrEnum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETE = "Complete"
    FAILED = "Failed"
    DELETING = "Deleting"
    DELETED = "Deleted"
    UNKNOWN = "Unknown"


class WorkloadType(StrEnum):
    INFERENCE = "INFERENCE"
    FINE_TUNING = "FINE_TUNING"
    WORKSPACE = "WORKSPACE"
