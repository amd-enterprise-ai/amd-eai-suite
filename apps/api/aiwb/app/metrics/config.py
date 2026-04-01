# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration for metrics collection."""

import os

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
