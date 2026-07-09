# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import datetime
from textwrap import dedent

from prometheus_api_client import PrometheusConnect

from ..projects.crds import Namespace
from .constants import (
    AIM_SERVICE_ID_METRIC_LABEL,
    API_KEY_ID_METRIC_LABEL,
    EXTPROC_REQUEST_DURATION_COUNT_METRIC,
    EXTPROC_TOKEN_USAGE_METRIC,
    GEN_AI_TOKEN_TYPE_LABEL,
    GPU_POD_METRIC_LABEL,
    NAMESPACE_METRIC_LABEL,
    VLLM_POD_METRIC_LABEL,
    WORKLOAD_ID_METRIC_LABEL,
)
from .enums import MetricName, NamespaceMetricName
from .schemas import DateRange, MetricsScalar, MetricsScalarWithRange, MetricsTimeseries
from .utils import (
    a_custom_query,
    a_custom_query_range,
    convert_prometheus_string_to_float,
    get_aggregation_lookback_for_metrics,
    get_step_for_range_query,
    map_metrics_timeseries,
)


def _pod_selector(pod_name: str | None, label: str = VLLM_POD_METRIC_LABEL) -> str:
    """Returns an additional Prometheus label selector for a specific pod, or empty string."""
    return f', {label}="{pod_name}"' if pod_name else ""


def _escape_promql_label_value(value: str) -> str:
    """Escapes backslashes and double quotes to prevent PromQL label injection."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def get_gpu_device_utilization_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    step: float,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsTimeseries:
    query = dedent(f"""
        count(
            gpu_gfx_activity{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}
        )
    """)
    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(int(step))
    )
    return map_metrics_timeseries(results, start, end, int(step), MetricName.GPU_DEVICE_UTILIZATION.value)


async def get_gpu_memory_utilization_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    step: float,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsTimeseries:
    query = dedent(f"""
        sum(
            gpu_used_vram{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}
        )
    """)
    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(int(step))
    )
    return map_metrics_timeseries(results, start, end, int(step), MetricName.GPU_MEMORY_UTILIZATION.value)


async def get_requests_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    step: float,
    lookback: str,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsTimeseries:
    # Both series are gauges — use max_over_time to capture peaks within each step.
    running_query = (
        f'sum(max_over_time(vllm:num_requests_running{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))'
    )
    waiting_query = (
        f'sum(max_over_time(vllm:num_requests_waiting{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))'
    )

    running_res, waiting_res = await asyncio.gather(
        a_custom_query_range(
            client=prometheus_client, query=running_query, start_time=start, end_time=end, step=str(int(step))
        ),
        a_custom_query_range(
            client=prometheus_client, query=waiting_query, start_time=start, end_time=end, step=str(int(step))
        ),
    )

    running = map_metrics_timeseries(running_res, start, end, int(step), "running")
    waiting = map_metrics_timeseries(waiting_res, start, end, int(step), "waiting")

    return MetricsTimeseries(data=running.data + waiting.data, range=running.range)


async def get_ttft_latency_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    step: float,
    lookback: str,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsTimeseries:
    # vLLM engine metric
    query = dedent(f"""
        sum(rate(vllm:time_to_first_token_seconds_sum{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))
        /
        sum(rate(vllm:time_to_first_token_seconds_count{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))
    """)
    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(int(step))
    )
    return map_metrics_timeseries(results, start, end, int(step), MetricName.TIME_TO_FIRST_TOKEN.value)


async def get_inter_token_latency_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    step: float,
    lookback: str,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsTimeseries:
    # vLLM engine metric (renamed from time_per_output_token_seconds in newer vLLM versions)
    query = dedent(f"""
        sum(rate(vllm:inter_token_latency_seconds_sum{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))
        /
        sum(rate(vllm:inter_token_latency_seconds_count{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))
    """)
    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(int(step))
    )
    return map_metrics_timeseries(results, start, end, int(step), MetricName.INTER_TOKEN_LATENCY.value)


async def get_e2e_latency_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    step: float,
    lookback: str,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsTimeseries:
    # vLLM engine metric
    query = dedent(f"""
        sum(rate(vllm:e2e_request_latency_seconds_sum{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))
        /
        sum(rate(vllm:e2e_request_latency_seconds_count{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{lookback}]))
    """)
    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(int(step))
    )
    return map_metrics_timeseries(results, start, end, int(step), MetricName.E2E_LATENCY.value)


async def get_max_requests_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    # Peak concurrent requests (running + waiting) over the time range.
    # `or vector(0)` prevents an empty result when one series has no data points.
    query = (
        f'(sum(max_over_time(vllm:num_requests_running{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s])) or vector(0))'
        f' + (sum(max_over_time(vllm:num_requests_waiting{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s])) or vector(0))'
    )
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))


async def get_min_requests_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    query = (
        f'(sum(min_over_time(vllm:num_requests_running{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s])) or vector(0))'
        f' + (sum(min_over_time(vllm:num_requests_waiting{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s])) or vector(0))'
    )
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))


async def get_avg_requests_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    query = (
        f'(sum(avg_over_time(vllm:num_requests_running{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s])) or vector(0))'
        f' + (sum(avg_over_time(vllm:num_requests_waiting{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s])) or vector(0))'
    )
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))


async def get_total_requests_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    # Total completed requests over the time range
    query = f'sum(ceil(increase(vllm:request_success_total{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s])))'
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))


async def get_kv_cache_usage_metric(
    workload_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    query = (
        f'avg(avg_over_time(vllm:kv_cache_usage_perc{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}}[{seconds}s]))'
    )
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))


async def get_total_tokens_metric(
    workload_id: str,
    prometheus_client: PrometheusConnect,
    pod: str = "",
) -> MetricsScalar:
    # vLLM engine metric
    query = f'sum(vllm:generation_tokens_total{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"{pod}}})'
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalar(data=max(value, 0))


async def get_metric_by_workload_id(
    workload_id: str,
    metric: MetricName,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    pod_name: str | None = None,
) -> MetricsTimeseries | MetricsScalar | MetricsScalarWithRange:
    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)
    vllm_pod = _pod_selector(pod_name)
    gpu_pod = _pod_selector(pod_name, GPU_POD_METRIC_LABEL)

    match metric:
        case MetricName.GPU_DEVICE_UTILIZATION:
            return await get_gpu_device_utilization_metric(workload_id, start, end, step, prometheus_client, gpu_pod)
        case MetricName.GPU_MEMORY_UTILIZATION:
            return await get_gpu_memory_utilization_metric(workload_id, start, end, step, prometheus_client, gpu_pod)
        case MetricName.REQUESTS:
            return await get_requests_metric(workload_id, start, end, step, lookback, prometheus_client, vllm_pod)
        case MetricName.TIME_TO_FIRST_TOKEN:
            return await get_ttft_latency_metric(workload_id, start, end, step, lookback, prometheus_client, vllm_pod)
        case MetricName.INTER_TOKEN_LATENCY:
            return await get_inter_token_latency_metric(
                workload_id, start, end, step, lookback, prometheus_client, vllm_pod
            )
        case MetricName.E2E_LATENCY:
            return await get_e2e_latency_metric(workload_id, start, end, step, lookback, prometheus_client, vllm_pod)
        case MetricName.MAX_REQUESTS:
            return await get_max_requests_metric(workload_id, start, end, prometheus_client, vllm_pod)
        case MetricName.MIN_REQUESTS:
            return await get_min_requests_metric(workload_id, start, end, prometheus_client, vllm_pod)
        case MetricName.AVG_REQUESTS:
            return await get_avg_requests_metric(workload_id, start, end, prometheus_client, vllm_pod)
        case MetricName.TOTAL_REQUESTS:
            return await get_total_requests_metric(workload_id, start, end, prometheus_client, vllm_pod)
        case MetricName.KV_CACHE_USAGE:
            return await get_kv_cache_usage_metric(workload_id, start, end, prometheus_client, vllm_pod)
        case MetricName.TOTAL_TOKENS:
            return await get_total_tokens_metric(workload_id, prometheus_client, vllm_pod)
        case _:
            raise ValueError(f"Unsupported metric: {metric}")


async def get_gpu_device_utilization_for_namespace(
    namespace: Namespace,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
) -> MetricsTimeseries:
    step = get_step_for_range_query(start, end)

    query = dedent(f"""
        count(
            gpu_gfx_activity{{{NAMESPACE_METRIC_LABEL}="{namespace.name}"}}
        )
    """)

    results = await a_custom_query_range(
        client=prometheus_client,
        query=query,
        start_time=start,
        end_time=end,
        step=str(int(step)),
    )
    return map_metrics_timeseries(results, start, end, int(step), MetricName.GPU_DEVICE_UTILIZATION.value)


async def get_gpu_memory_utilization_for_namespace(
    namespace: Namespace,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
) -> MetricsTimeseries:
    step = get_step_for_range_query(start, end)

    query = dedent(f"""
        sum(
            gpu_used_vram{{{NAMESPACE_METRIC_LABEL}="{namespace.name}"}}
        )
    """)

    results = await a_custom_query_range(
        client=prometheus_client,
        query=query,
        start_time=start,
        end_time=end,
        step=str(int(step)),
    )
    return map_metrics_timeseries(results, start, end, int(step), MetricName.GPU_MEMORY_UTILIZATION.value)


async def get_gpu_utilization_by_workload_in_namespace(
    namespace: Namespace,
    prometheus_client: PrometheusConnect,
) -> dict[str, int]:
    query = dedent(f"""
        count by ({WORKLOAD_ID_METRIC_LABEL}) (
            gpu_gfx_activity{{{NAMESPACE_METRIC_LABEL}="{namespace.name}"}}
        )
    """)
    results = await a_custom_query(client=prometheus_client, query=query)

    workload_gpu_counts: dict[str, int] = {}
    for result in results:
        workload_id = result["metric"].get(WORKLOAD_ID_METRIC_LABEL)
        if workload_id:
            value = int(result["value"][1])
            workload_gpu_counts[workload_id] = value
    return workload_gpu_counts


async def get_gpu_vram_by_workload_in_namespace(
    namespace: Namespace,
    prometheus_client: PrometheusConnect,
) -> dict[str, float]:
    query = dedent(f"""
        sum by ({WORKLOAD_ID_METRIC_LABEL}) (
            gpu_used_vram{{{NAMESPACE_METRIC_LABEL}="{namespace.name}"}}
        )
    """)
    results = await a_custom_query(client=prometheus_client, query=query)

    workload_vram_usage: dict[str, float] = {}
    for result in results:
        workload_id = result["metric"].get(WORKLOAD_ID_METRIC_LABEL)
        if workload_id:
            value = convert_prometheus_string_to_float(result["value"][1])
            workload_vram_usage[workload_id] = value
    return workload_vram_usage


async def get_metric_by_namespace(
    namespace: Namespace,
    metric: NamespaceMetricName,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
) -> MetricsTimeseries:
    match metric:
        case NamespaceMetricName.GPU_DEVICE_UTILIZATION:
            return await get_gpu_device_utilization_for_namespace(namespace, start, end, prometheus_client)
        case NamespaceMetricName.GPU_MEMORY_UTILIZATION:
            return await get_gpu_memory_utilization_for_namespace(namespace, start, end, prometheus_client)


async def get_input_tokens_by_api_key(
    api_key_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    aim_service_id: str | None = None,
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    safe_key = _escape_promql_label_value(api_key_id)
    service_selector = (
        f', {AIM_SERVICE_ID_METRIC_LABEL}="{_escape_promql_label_value(aim_service_id)}"' if aim_service_id else ""
    )
    query = (
        f"sum(increase({EXTPROC_TOKEN_USAGE_METRIC}{{"
        f'{GEN_AI_TOKEN_TYPE_LABEL}="input", {API_KEY_ID_METRIC_LABEL}="{safe_key}"{service_selector}'
        f"}}[{seconds}s]))"
    )
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))


async def get_output_tokens_by_api_key(
    api_key_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    aim_service_id: str | None = None,
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    safe_key = _escape_promql_label_value(api_key_id)
    service_selector = (
        f', {AIM_SERVICE_ID_METRIC_LABEL}="{_escape_promql_label_value(aim_service_id)}"' if aim_service_id else ""
    )
    query = (
        f"sum(increase({EXTPROC_TOKEN_USAGE_METRIC}{{"
        f'{GEN_AI_TOKEN_TYPE_LABEL}="output", {API_KEY_ID_METRIC_LABEL}="{safe_key}"{service_selector}'
        f"}}[{seconds}s]))"
    )
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))


async def get_requests_by_api_key(
    api_key_id: str,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
    aim_service_id: str | None = None,
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    safe_key = _escape_promql_label_value(api_key_id)
    service_selector = (
        f', {AIM_SERVICE_ID_METRIC_LABEL}="{_escape_promql_label_value(aim_service_id)}"' if aim_service_id else ""
    )
    query = (
        f"sum(ceil(increase({EXTPROC_REQUEST_DURATION_COUNT_METRIC}{{"
        f'{API_KEY_ID_METRIC_LABEL}="{safe_key}"{service_selector}'
        f"}}[{seconds}s])))"
    )
    res = await a_custom_query(client=prometheus_client, query=query)
    value = convert_prometheus_string_to_float(res[0]["value"][1]) if res else 0
    return MetricsScalarWithRange(data=max(value, 0), range=DateRange(start=start, end=end))
