# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class WorkloadDeviceMetricKind(StrEnum):
    VRAM_UTILIZATION = "vram_utilization"
    GPU_UTILIZATION = "gpu_utilization"
    POWER_USAGE = "power_usage"
