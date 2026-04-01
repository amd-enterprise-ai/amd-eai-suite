# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from ..messaging.schemas import PriorityClass

DEFAULT_PRIORITY_CLASSES = [
    PriorityClass(name="low", priority=-100),
    PriorityClass(name="medium", priority=0),
    PriorityClass(name="high", priority=100),
]
