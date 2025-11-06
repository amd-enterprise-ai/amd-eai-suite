# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

PROJECT_ID_METRIC_LABEL = "project_id"
WORKLOAD_ID_METRIC_LABEL = "workload_id"
ORGANIZATION_NAME_METRIC_LABEL = "org_name"
CLUSTER_NAME_METRIC_LABEL = "kube_cluster_name"

MAX_DAYS_FOR_TIMESERIES = 8

ALLOCATED_GPUS_SERIES_LABEL = "allocated_gpus"
ALLOCATED_GPU_VRAM_SERIES_LABEL = "allocated_gpu_vram"
UTILIZED_GPUS_SERIES_LABEL = "utilized_gpus"
UTILIZED_GPU_VRAM_SERIES_LABEL = "utilized_gpu_vram"

VLLM_RUNNING_REQUESTS_LABEL = "running_requests"
VLLM_WAITING_REQUESTS_LABEL = "waiting_requests"
VLLM_TIME_TO_FIRST_TOKEN_LABEL = "time_to_first_token_seconds"
VLLM_INTER_TOKEN_LATENCY_LABEL = "inter_token_latency_seconds"
VLLM_END_TO_END_LATENCY_LABEL = "end_to_end_latency_seconds"

PROMETHEUS_NAN_STRING = "NaN"
PROMETHEUS_INF_STRING = "Inf"
PROMETHEUS_MINUS_INF_STRING = "-Inf"
