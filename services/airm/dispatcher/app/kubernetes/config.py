# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

USE_LOCAL_KUBE_CONTEXT = os.getenv("USE_LOCAL_KUBE_CONTEXT", "false").lower() == "true"

METRICS_CONFIG_MAP_NAMESPACE = os.getenv("METRICS_CONFIG_MAP_NAMESPACE", "kube-amd-gpu")
METRICS_CONFIG_MAP_NAME = os.getenv("METRICS_CONFIG_MAP_NAME", "gpu-config")
