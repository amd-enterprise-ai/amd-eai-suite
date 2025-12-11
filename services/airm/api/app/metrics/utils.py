# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import UTC, datetime, timedelta
from math import floor
from typing import Any

from prometheus_api_client import PrometheusConnect

from ..projects.models import Project
from ..projects.schemas import ProjectResponse
from .constants import MAX_DAYS_FOR_TIMESERIES, PROJECT_ID_METRIC_LABEL, PROMETHEUS_NAN_STRING
from .schemas import (
    Datapoint,
    DatapointMetadataBase,
    DatapointsWithMetadata,
    MetricsTimeseries,
    ProjectDatapointMetadata,
    TimeseriesRange,
)


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
    return {start + timedelta(seconds=i * step): None for i in range(floor((end - start).total_seconds() / step) + 1)}


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
            timestamp_dt = datetime.fromtimestamp(float(timestamp), tz=UTC)
            if timestamp_dt in default_datapoints and value != PROMETHEUS_NAN_STRING:
                default_datapoints[timestamp_dt] = 0

    for series in results:
        project_id = series["metric"].get(PROJECT_ID_METRIC_LABEL, None)
        project = projects_by_id.get(project_id)
        if project is None:
            continue
        datapoints = default_datapoints.copy()
        for timestamp, value in series["values"]:
            timestamp_dt = datetime.fromtimestamp(float(timestamp), tz=UTC)
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
            timestamp_dt = datetime.fromtimestamp(float(timestamp), tz=UTC)
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
