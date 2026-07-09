# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration for workloads management."""

import os

# Time in seconds before a workload with no CRD is marked as DELETED
WORKLOAD_UPDATE_GRACE_PERIOD = int(os.getenv("SYNCER_PENDING_TIMEOUT_SECONDS", "60"))
