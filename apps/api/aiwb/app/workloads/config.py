# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration for workloads management."""

import os

# Time in seconds before a workload with no CRD is marked as DELETED
WORKLOAD_UPDATE_GRACE_PERIOD = int(os.getenv("SYNCER_PENDING_TIMEOUT_SECONDS", "60"))

# Time in seconds to wait for chat responses
CHAT_TIMEOUT = float(os.environ.get("CHAT_TIMEOUT", 1800.0))

# Default chat path
DEFAULT_CHAT_PATH = os.environ.get("DEFAULT_CHAT_PATH", "/v1/chat/completions")
