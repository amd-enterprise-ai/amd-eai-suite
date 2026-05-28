# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class NamespaceStatus(StrEnum):
    ACTIVE = "Active"
    TERMINATING = "Terminating"
    PENDING = "Pending"
    FAILED = "Failed"
    DELETED = "Deleted"
    DELETE_FAILED = "DeleteFailed"
