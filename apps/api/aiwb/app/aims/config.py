# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration for AIM (AMD Inference Microservices)."""

import os

AIM_CLUSTER_RUNTIME_CONFIG_NAME = os.getenv("AIM_CLUSTER_RUNTIME_CONFIG_NAME", "default")
AIM_GATEWAY_NAMESPACE = os.getenv("AIM_GATEWAY_NAMESPACE", "kgateway-system")
AIM_GATEWAY_NAME = os.getenv("AIM_GATEWAY_NAME", "https")
