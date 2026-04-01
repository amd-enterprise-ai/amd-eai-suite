# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

PROJECT_ID_METRIC_LABEL = "project_id"
WORKLOAD_ID_METRIC_LABEL = "workload_id"
CLUSTER_NAME_METRIC_LABEL = "kube_cluster_name"
GPU_ID_METRIC_LABEL = "gpu_id"
GPU_UUID_METRIC_LABEL = "gpu_uuid"
HOSTNAME_METRIC_LABEL = "hostname"

DEFAULT_DEVICE_LOOKBACK = "5m"

MAX_DAYS_FOR_TIMESERIES = 8

GPU_GFX_ACTIVITY_METRIC = "gpu_gfx_activity"
GPU_JUNCTION_TEMPERATURE_METRIC = "gpu_junction_temperature"
GPU_MEMORY_TEMPERATURE_METRIC = "gpu_memory_temperature"
GPU_PACKAGE_POWER_METRIC = "gpu_package_power"
GPU_USED_VRAM_METRIC = "gpu_used_vram"
GPU_TOTAL_VRAM_METRIC = "gpu_total_vram"
GPU_CLOCK_METRIC = "gpu_clock"
GPU_CLOCK_TYPE_LABEL = "clock_type"
GPU_CLOCK_TYPE_SYSTEM = "GPU_CLOCK_TYPE_SYSTEM"

ALLOCATED_GPUS_SERIES_LABEL = "allocated_gpus"
ALLOCATED_GPU_VRAM_SERIES_LABEL = "allocated_gpu_vram"
UTILIZED_GPUS_SERIES_LABEL = "utilized_gpus"
UTILIZED_GPU_VRAM_SERIES_LABEL = "utilized_gpu_vram"

PCIe_BANDWIDTH_METRIC = "pcie_bandwidth"
PCIe_SPEED_METRIC = "pcie_speed"
PCIe_MAX_SPEED_METRIC = "pcie_max_speed"

PROMETHEUS_NAN_STRING = "NaN"
PROMETHEUS_INF_STRING = "Inf"
PROMETHEUS_MINUS_INF_STRING = "-Inf"
