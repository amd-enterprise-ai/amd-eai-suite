# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class ProjectStatus(StrEnum):
    PENDING = "Pending"
    FAILED = "Failed"
    PARTIALLY_READY = "PartiallyReady"
    READY = "Ready"
    DELETING = "Deleting"
