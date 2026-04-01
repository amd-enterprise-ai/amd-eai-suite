# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from ..aims.enums import AIMServiceStatus
from ..workloads.enums import WorkloadStatus

# Single source of truth: AIMServiceStatus -> WorkloadStatus
# DEGRADED merges into FAILED, STARTING merges into PENDING
AIM_TO_WORKLOAD_STATUS = {
    AIMServiceStatus.PENDING: WorkloadStatus.PENDING,
    AIMServiceStatus.STARTING: WorkloadStatus.PENDING,
    AIMServiceStatus.RUNNING: WorkloadStatus.RUNNING,
    AIMServiceStatus.FAILED: WorkloadStatus.FAILED,
    AIMServiceStatus.DEGRADED: WorkloadStatus.FAILED,
}
