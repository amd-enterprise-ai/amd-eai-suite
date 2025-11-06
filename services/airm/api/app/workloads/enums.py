# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class WorkloadType(StrEnum):
    MODEL_DOWNLOAD = "MODEL_DOWNLOAD"
    INFERENCE = "INFERENCE"
    FINE_TUNING = "FINE_TUNING"
    WORKSPACE = "WORKSPACE"
    CUSTOM = "CUSTOM"
