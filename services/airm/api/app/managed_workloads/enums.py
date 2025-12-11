# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from airm.messaging.schemas import WorkloadStatus

from ..models.models import OnboardingStatus


def workload_status_to_model_status(status: WorkloadStatus) -> OnboardingStatus:
    """Maps the workload status from k8s to the onboarding status."""
    match status:
        case WorkloadStatus.PENDING | WorkloadStatus.RUNNING | WorkloadStatus.DELETING | WorkloadStatus.UNKNOWN:
            # Pending, running, deleting, or unknown: still transitioning
            return OnboardingStatus.pending
        case WorkloadStatus.COMPLETE:
            # Complete: workload is ready
            return OnboardingStatus.ready
        case WorkloadStatus.FAILED | WorkloadStatus.DELETE_FAILED | WorkloadStatus.DELETED | WorkloadStatus.TERMINATED:
            # Failed, delete failed, deleted, or terminated: onboarding failed or workload removed/killed
            return OnboardingStatus.failed
        case _:
            # Default: treat as pending
            return OnboardingStatus.pending
