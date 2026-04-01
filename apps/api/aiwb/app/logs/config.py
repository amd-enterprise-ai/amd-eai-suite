# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration for Loki logging."""

import os

# ============================================================================
# Loki / Logging Configuration
# ============================================================================
LOKI_URL = os.getenv("LOKI_URL") or os.getenv(
    "LOKI_BASE_URL", "http://lgtm-stack.otel-lgtm-stack.svc.cluster.local:3100"
)
LOKI_TIMEOUT_SECONDS = int(os.getenv("LOKI_TIMEOUT_SECONDS", "30"))
LOKI_KEEPALIVE_TIMEOUT_SECONDS = int(os.getenv("LOKI_KEEPALIVE_TIMEOUT_SECONDS", "30"))
LOKI_DEFAULT_TIME_RANGE_DAYS = int(os.getenv("LOKI_DEFAULT_TIME_RANGE_DAYS", "15"))
