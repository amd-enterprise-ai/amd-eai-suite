# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Test managed workloads enums module.
"""

import pytest

from airm.messaging.schemas import WorkloadStatus
from app.managed_workloads.enums import workload_status_to_model_status
from app.models.models import OnboardingStatus


@pytest.mark.parametrize(
    "workload_status,expected_onboarding_status",
    [
        (WorkloadStatus.PENDING, OnboardingStatus.pending),
        (WorkloadStatus.RUNNING, OnboardingStatus.pending),
        (WorkloadStatus.COMPLETE, OnboardingStatus.ready),
        (WorkloadStatus.FAILED, OnboardingStatus.failed),
        (WorkloadStatus.UNKNOWN, OnboardingStatus.pending),
    ],
)
def test_workload_status_to_model_status_mapping(workload_status, expected_onboarding_status):
    """Test workload status to model status mapping for all defined statuses."""
    result = workload_status_to_model_status(workload_status)
    assert result == expected_onboarding_status


def test_workload_status_to_model_status_undefined_status():
    """Test workload status to model status mapping with undefined status returns default."""

    # Create a mock status that's not in the mapping
    class MockWorkloadStatus:
        pass

    undefined_status = MockWorkloadStatus()
    result = workload_status_to_model_status(undefined_status)

    # Should return the default value (OnboardingStatus.pending)
    assert result == OnboardingStatus.pending
