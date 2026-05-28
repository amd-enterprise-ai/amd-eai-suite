# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class QuotaStatus(StrEnum):
    PENDING = "Pending"
    READY = "Ready"
    DELETING = "Deleting"
    FAILED = "Failed"
    DELETED = "Deleted"
