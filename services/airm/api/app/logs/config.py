# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

# Loki configuration for workload logging
LOKI_URL = os.getenv("LOKI_URL") or os.getenv(
    "LOKI_BASE_URL", "http://lgtm-stack.otel-lgtm-stack.svc.cluster.local:3100"
)
LOKI_TIMEOUT_SECONDS = int(os.getenv("LOKI_TIMEOUT_SECONDS", 30))

# Default time range for log queries (in days)
LOKI_DEFAULT_TIME_RANGE_DAYS = int(os.getenv("LOKI_DEFAULT_TIME_RANGE_DAYS", 15))
