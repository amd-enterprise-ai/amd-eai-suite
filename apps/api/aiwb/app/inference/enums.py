# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Inference capability enums."""

from enum import StrEnum


class InferenceCapability(StrEnum):
    """Capability filter values accepted by the inference list endpoint.

    Today only ``chat`` is meaningful — it narrows the list to deployments
    whose model is tagged for chat completions and whose serving stack is
    fully ready. Adding new capabilities here lets clients filter for them
    without endpoint proliferation.
    """

    CHAT = "chat"
