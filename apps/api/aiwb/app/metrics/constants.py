# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# Prometheus query label selectors
WORKLOAD_ID_METRIC_LABEL = "workload_id"
NAMESPACE_METRIC_LABEL = "namespace"
CLUSTER_NAME_METRIC_LABEL = "kube_cluster_name"
POD_NAME_METRIC_LABEL = "k8s_pod_name"

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
