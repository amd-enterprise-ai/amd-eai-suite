# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# Prometheus query label selectors
WORKLOAD_ID_METRIC_LABEL = "workload_id"
NAMESPACE_METRIC_LABEL = "namespace"
CLUSTER_NAME_METRIC_LABEL = "kube_cluster_name"
VLLM_POD_METRIC_LABEL = "service_instance_id"
GPU_POD_METRIC_LABEL = "pod"

# API key metric label selectors — sourced from ext-proc metricsRequestHeaderAttributes
API_KEY_ID_METRIC_LABEL = "api_key_id"
AIM_SERVICE_ID_METRIC_LABEL = "aim_service_id"

# ext-proc Prometheus metric names (OTel Semantic Conventions for Generative AI)
EXTPROC_TOKEN_USAGE_METRIC = (
    "gen_ai_client_token_usage_sum"  # `_sum`: cumulative-sum series; increase() gives the period delta
)
EXTPROC_REQUEST_DURATION_COUNT_METRIC = "gen_ai_server_request_duration_seconds_count"
GEN_AI_TOKEN_TYPE_LABEL = "gen_ai_token_type"

MAX_DAYS_FOR_TIMESERIES = 8
MAX_DAYS_FOR_METRICS = 30

# OTel collector scrape interval — drives minimum lookback window
SCRAPE_INTERVAL_SECONDS = 30

PROMETHEUS_NAN_STRING = "NaN"
PROMETHEUS_INF_STRING = "Inf"
PROMETHEUS_MINUS_INF_STRING = "-Inf"

# FastAPI Query parameter documentation
METRICS_START_TIME_DOC = (
    "Start time for metrics range (ISO 8601 with timezone, e.g. UTC: ...Z or +00:00). Prometheus expects UTC."
)
METRICS_END_TIME_DOC = (
    "End time for metrics range (ISO 8601 with timezone, e.g. UTC: ...Z or +00:00). Prometheus expects UTC."
)
