# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import UTC, datetime, timedelta
from math import floor, isfinite
from typing import Any

from prometheus_api_client import PrometheusConnect

from ..projects.models import Project
from ..projects.schemas import ProjectResponse
from .constants import (
    CLUSTER_NAME_METRIC_LABEL,
    DEFAULT_DEVICE_LOOKBACK,
    GPU_ID_METRIC_LABEL,
    GPU_TOTAL_VRAM_METRIC,
    GPU_USED_VRAM_METRIC,
    GPU_UUID_METRIC_LABEL,
    HOSTNAME_METRIC_LABEL,
    MAX_DAYS_FOR_TIMESERIES,
    PROJECT_ID_METRIC_LABEL,
    PROMETHEUS_INF_STRING,
    PROMETHEUS_MINUS_INF_STRING,
    PROMETHEUS_NAN_STRING,
    WORKLOAD_ID_METRIC_LABEL,
)
from .schemas import (
    Datapoint,
    DatapointMetadataBase,
    DatapointsWithMetadata,
    MetricsTimeseries,
    NodeGpuDevice,
    ProjectDatapointMetadata,
    TimeseriesRange,
)


def is_valid_metric_value(value: str | float | None) -> bool:
    """Return True if the value should be considered a valid metric (truthy and not NaN/Inf/-Inf)."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value) and value not in (
            PROMETHEUS_NAN_STRING,
            PROMETHEUS_INF_STRING,
            PROMETHEUS_MINUS_INF_STRING,
        )
    return isfinite(value)


def validate_datetime_range(start: datetime, end: datetime) -> None:
    if start >= end:
        raise ValueError("Start date must be before end time.")
    if start < datetime.now(UTC) - timedelta(days=MAX_DAYS_FOR_TIMESERIES):
        raise ValueError(f"Start date must be within the last {MAX_DAYS_FOR_TIMESERIES} days.")


def get_step_for_range_query(start_time: datetime, end_time: datetime) -> float:
    """
    Given a start and end time, how many datapoints should be returned for the range query.
    The step is the interval between each datapoint in seconds.
    """
    time_diff = end_time - start_time
    if time_diff <= timedelta(hours=1):
        return timedelta(minutes=1).total_seconds()
    elif time_diff <= timedelta(hours=24):
        return timedelta(minutes=5).total_seconds()
    elif time_diff <= timedelta(days=MAX_DAYS_FOR_TIMESERIES):
        return timedelta(hours=1).total_seconds()
    raise ValueError(f"Time range is too large. Please limit the range to {MAX_DAYS_FOR_TIMESERIES} days.")


def get_aggregation_lookback_for_metrics(step: float | None = None) -> str:
    """Given a step for the range query, for each datapoint, how many seconds/minutes worth of data should be
    considered, and aggregated over.
    """
    if not step or step <= timedelta(minutes=1).total_seconds():
        return "1m"
    elif timedelta(minutes=1).total_seconds() < step < timedelta(hours=1).total_seconds():
        return "5m"
    else:
        return "1h"


async def a_custom_query_range(
    client: PrometheusConnect,
    query: str,
    start_time: datetime,
    end_time: datetime,
    step: str,
    params: dict | None = None,
) -> list[dict[str, Any]]:
    """Async wrapper for custom_query_range."""
    return await asyncio.to_thread(
        lambda: client.custom_query_range(
            query=query, start_time=start_time, end_time=end_time, step=step, params=params
        )
    )


async def a_custom_query(client: PrometheusConnect, query: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Async wrapper for custom_query."""
    return await asyncio.to_thread(lambda: client.custom_query(query=query, params=params))


def __get_default_datapoints_for_range(start: datetime, end: datetime, step: float) -> dict[datetime, float | None]:
    normalized_start = start.replace(microsecond=0)
    return {
        normalized_start + timedelta(seconds=i * step): None
        for i in range(floor((end - normalized_start).total_seconds() / step) + 1)
    }


def map_timeseries_split_by_project(
    results: list[dict], projects: list[Project], start: datetime, end: datetime, step: float, series_label: str
) -> MetricsTimeseries:
    """
    Maps the timeseries data returned from Prometheus to a format that includes project metadata.
    Fills in missing datapoints with None values.
    """
    default_datapoints = __get_default_datapoints_for_range(start=start, end=end, step=step)

    projects_by_id = {str(project.id): project for project in projects}
    data: list[DatapointsWithMetadata] = []

    result_without_project = next(
        (result for result in results if PROJECT_ID_METRIC_LABEL not in result["metric"]), None
    )

    # Get the result without projects (every query is expected to have one,
    # by virtue of the "(vector(0) / {denominator})" as part of the query).
    # Use this to determine datapoints that have values on prometheus and set the defaults to 0
    if result_without_project:
        for timestamp, value in result_without_project["values"]:
            timestamp_dt = datetime.fromtimestamp(float(timestamp), tz=UTC).replace(microsecond=0)
            if timestamp_dt in default_datapoints and value != PROMETHEUS_NAN_STRING:
                default_datapoints[timestamp_dt] = 0

    for series in results:
        project_id = series["metric"].get(PROJECT_ID_METRIC_LABEL, None)
        project = projects_by_id.get(project_id)
        if project is None:
            continue
        datapoints = default_datapoints.copy()
        for timestamp, value in series["values"]:
            timestamp_dt = datetime.fromtimestamp(float(timestamp), tz=UTC).replace(microsecond=0)
            if timestamp_dt in datapoints and value != PROMETHEUS_NAN_STRING:
                datapoints[timestamp_dt] = float(value)

        data.append(
            DatapointsWithMetadata(
                metadata=ProjectDatapointMetadata(project=ProjectResponse.model_validate(project), label=series_label),
                values=[Datapoint(timestamp=key, value=datapoints[key]) for key in sorted(datapoints.keys())],
            )
        )

    timeseries_range = TimeseriesRange(
        start=start,
        end=end,
        interval_seconds=step,
        timestamps=sorted(default_datapoints.keys()),
    )

    return MetricsTimeseries(data=data, range=timeseries_range)


def map_metrics_timeseries(
    results: list[dict], project: Project | None, start: datetime, end: datetime, step: float, series_label: str
) -> MetricsTimeseries:
    """
    Maps the timeseries data returned from Prometheus.
    Fills in missing datapoints with None values.
    """
    datapoints = __get_default_datapoints_for_range(start=start, end=end, step=step)

    data: list[DatapointsWithMetadata] = []

    if project is not None:
        metadata = ProjectDatapointMetadata(
            project=ProjectResponse.model_validate(project),
            label=series_label,
        )
    else:
        metadata = DatapointMetadataBase(label=series_label)

    for series in results:
        for timestamp, value in series["values"]:
            timestamp_dt = datetime.fromtimestamp(float(timestamp), tz=UTC).replace(microsecond=0)
            if timestamp_dt in datapoints and value != PROMETHEUS_NAN_STRING:
                datapoints[timestamp_dt] = float(value)

    data.append(
        DatapointsWithMetadata(
            metadata=metadata,
            values=[Datapoint(timestamp=key, value=datapoints[key]) for key in sorted(datapoints.keys())],
        )
    )

    timeseries_range = TimeseriesRange(
        start=start,
        end=end,
        interval_seconds=step,
        timestamps=sorted(datapoints.keys()),
    )

    return MetricsTimeseries(data=data, range=timeseries_range)


def construct_timeseries_query_with_fallback_for_default_series(numerator: str, denominator: str) -> str:
    """
    Constructs a PromQL timeseries query that always returns a series with no labels, if the denominator is present.

    The assumption here is that the numerator has sparse data intentionally and the denominator
    is always present (unless of technical difficulties).

    This utility function is used to adjust the query so that the response with no label always has data if the denominator is present.
    This can be used to determine which datapoints actually had data scraped and set 0s for the sparse data.
    """

    return f"""
({numerator} /{denominator})
or
(vector(0) /{denominator})
"""


def convert_prometheus_string_to_float(value: str) -> float:
    return float(value if value != PROMETHEUS_NAN_STRING else 0)


def parse_per_device_results(results: list[dict]) -> dict[tuple[str, str], float]:
    """Extract {(gpu_uuid, hostname): value} from a Prometheus instant-query result set."""
    device_values: dict[tuple[str, str], float] = {}
    for result in results:
        gpu_uuid = result["metric"].get(GPU_UUID_METRIC_LABEL)
        hostname = result["metric"].get(HOSTNAME_METRIC_LABEL)
        if gpu_uuid is None or hostname is None:
            continue
        device_values[(gpu_uuid, hostname)] = convert_prometheus_string_to_float(result["value"][1])
    return device_values


DeviceKey = tuple[str, str, str]


def parse_device_range_timeseries(
    results: list[dict], start: datetime, end: datetime, step: float
) -> dict[DeviceKey, list[Datapoint]]:
    """
    Parse range-query results grouped by (gpu_id, gpu_uuid, hostname) into per-device
    Datapoint lists. Missing timestamps are filled with None.

    Returns ``{(gpu_uuid, hostname, gpu_id): [Datapoint, ...]}``.
    """
    default_datapoints = __get_default_datapoints_for_range(start=start, end=end, step=step)
    device_series: dict[DeviceKey, list[Datapoint]] = {}

    for series in results:
        gpu_uuid = series["metric"].get(GPU_UUID_METRIC_LABEL)
        hostname = series["metric"].get(HOSTNAME_METRIC_LABEL)
        if gpu_uuid is None or hostname is None:
            continue
        gpu_id = series["metric"].get(GPU_ID_METRIC_LABEL, "")
        datapoints = default_datapoints.copy()
        for timestamp, value in series["values"]:
            timestamp_dt = datetime.fromtimestamp(float(timestamp), tz=UTC).replace(microsecond=0)
            if timestamp_dt in datapoints and value != PROMETHEUS_NAN_STRING:
                datapoints[timestamp_dt] = float(value)

        device_series[(gpu_uuid, hostname, gpu_id)] = [
            Datapoint(timestamp=t, value=v) for t, v in sorted(datapoints.items())
        ]

    return device_series


def build_workload_device_query(
    workload_id: str,
    metric_name: str,
    aggregation: str,
    use_lookback: bool,
    lookback: str = DEFAULT_DEVICE_LOOKBACK,
) -> str:
    """Build a per-device PromQL query for a workload. aggregation in ('sum', 'avg')."""
    wid_filter = f'{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"'
    group_by = f"{GPU_ID_METRIC_LABEL}, {GPU_UUID_METRIC_LABEL}, {HOSTNAME_METRIC_LABEL}"
    if use_lookback:
        expr = f"avg_over_time({metric_name}{{{wid_filter}}}[{lookback}])"
    else:
        expr = f"{metric_name}{{{wid_filter}}}"
    return f"{aggregation} by ({group_by}) ({expr})"


def build_node_device_query(
    node_name: str,
    cluster_name: str,
    metric_name: str,
    aggregation: str,
    lookback: str,
    extra_filters: dict[str, str] | None = None,
) -> str:
    """Build a per-device PromQL query for a cluster node, filtered by hostname and cluster."""
    node_filter = f'{HOSTNAME_METRIC_LABEL}="{node_name}", {CLUSTER_NAME_METRIC_LABEL}="{cluster_name}"'
    if extra_filters:
        node_filter += ", " + ", ".join(f'{k}="{v}"' for k, v in extra_filters.items())
    group_by = f"{GPU_ID_METRIC_LABEL}, {GPU_UUID_METRIC_LABEL}, {HOSTNAME_METRIC_LABEL}"
    expr = f"avg_over_time({metric_name}{{{node_filter}}}[{lookback}])"
    return f"{aggregation} by ({group_by}) ({expr})"


def build_node_instant_query(node_name: str, cluster_name: str, metric_name: str) -> str:
    """Build a PromQL instant query for all GPU devices on a cluster node."""
    node_filter = f'{HOSTNAME_METRIC_LABEL}="{node_name}", {CLUSTER_NAME_METRIC_LABEL}="{cluster_name}"'
    return f"{metric_name}{{{node_filter}}}"


def build_node_vram_utilization_instant_query(node_name: str, cluster_name: str) -> str:
    """Build a PromQL instant query that computes VRAM utilization % per GPU on a cluster node."""
    node_filter = f'{HOSTNAME_METRIC_LABEL}="{node_name}", {CLUSTER_NAME_METRIC_LABEL}="{cluster_name}"'
    return f"{GPU_USED_VRAM_METRIC}{{{node_filter}}} / {GPU_TOTAL_VRAM_METRIC}{{{node_filter}}} * 100"


def _extract_by_gpu_id(results: list[dict]) -> dict[str, tuple[float, float]]:
    """Extract {gpu_id: (value, timestamp)} from instant-query results, skipping NaN/Inf."""
    by_id: dict[str, tuple[float, float]] = {}
    for result in results:
        gpu_id = result["metric"].get(GPU_ID_METRIC_LABEL)
        if gpu_id is None:
            continue
        raw_value = result["value"][1]
        if raw_value in (PROMETHEUS_NAN_STRING, PROMETHEUS_INF_STRING, PROMETHEUS_MINUS_INF_STRING):
            continue
        by_id[gpu_id] = (float(raw_value), float(result["value"][0]))
    return by_id


def _extract_gpu_uuid_map(*result_sets: list[dict]) -> dict[str, str]:
    """Extract {gpu_id: gpu_uuid} from one or more instant-query result sets."""
    uuid_map: dict[str, str] = {}
    for results in result_sets:
        for result in results:
            gpu_id = result["metric"].get(GPU_ID_METRIC_LABEL)
            gpu_uuid = result["metric"].get(GPU_UUID_METRIC_LABEL)
            if gpu_id is not None and gpu_uuid is not None:
                uuid_map.setdefault(gpu_id, gpu_uuid)
    return uuid_map


def map_results_to_node_gpu_devices(
    temp_results: list[dict],
    power_results: list[dict],
    vram_util_results: list[dict],
    gpu_product_name: str | None,
) -> list[NodeGpuDevice]:
    """Map raw Prometheus instant-query results into a list of NodeGpuDevice models."""
    temps = _extract_by_gpu_id(temp_results)
    powers = _extract_by_gpu_id(power_results)
    vram_utils = _extract_by_gpu_id(vram_util_results)
    uuid_map = _extract_gpu_uuid_map(temp_results, power_results, vram_util_results)

    all_gpu_ids = sorted(temps.keys() | powers.keys() | vram_utils.keys())

    gpu_devices: list[NodeGpuDevice] = []
    for gpu_id in all_gpu_ids:
        temp_val = temps.get(gpu_id)
        power_val = powers.get(gpu_id)
        vram_val = vram_utils.get(gpu_id)

        timestamps = [entry[1] for entry in [temp_val, power_val, vram_val] if entry is not None]
        latest_timestamp = datetime.fromtimestamp(max(timestamps), tz=UTC) if timestamps else None

        gpu_devices.append(
            NodeGpuDevice(
                gpu_uuid=uuid_map.get(gpu_id, f"unknown-{gpu_id}"),
                gpu_id=gpu_id,
                product_name=gpu_product_name,
                temperature=temp_val[0] if temp_val else None,
                power_consumption=power_val[0] if power_val else None,
                vram_utilization=vram_val[0] if vram_val else None,
                last_updated=latest_timestamp,
            )
        )

    return gpu_devices
