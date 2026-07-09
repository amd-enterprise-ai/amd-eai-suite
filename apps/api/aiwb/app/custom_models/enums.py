# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class OnboardPhase(StrEnum):
    """Derived onboarding phase for a custom (BYOM) model.

    Composed from three Kubernetes resources — the AIMModel CR status,
    AIMProfile presence and annotation, and AIMArtifact phase — into a
    single enum value the UI can switch on.
    """

    PENDING = "Pending"
    IMPORTING = "Importing"
    READY = "Ready"
    FAILED = "Failed"
