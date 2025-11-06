# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

GPU_CAPACITY_KEY = "amd.com/gpu"
GPU_PRODUCT_NAME_LABELS = ["amd.com/gpu.product-name", "beta.amd.com/gpu.product-name"]
GPU_DEVICE_ID_LABELS = ["amd.com/gpu.device-id", "beta.amd.com/gpu.device-id"]
GPU_VRAM_LABELS = ["amd.com/gpu.vram", "beta.amd.com/gpu.vram"]

PROBLEMATIC_NODE_CONDITIONS = {"DiskPressure", "MemoryPressure", "PIDPressure", "NetworkUnavailable"}
