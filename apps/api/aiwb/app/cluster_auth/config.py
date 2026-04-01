# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration for Cluster Auth service integration."""

import os

# ============================================================================
# Cluster Auth Service Configuration
# ============================================================================
CLUSTER_AUTH_URL = os.getenv("CLUSTER_AUTH_URL", "http://localhost:48012")
CLUSTER_AUTH_ADMIN_TOKEN = os.getenv("CLUSTER_AUTH_ADMIN_TOKEN", "")
