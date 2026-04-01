# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import UTC, datetime, timedelta
from math import floor
from typing import Any

from prometheus_api_client import PrometheusConnect

from api_common.exceptions import ValidationException

from .constants import MAX_DAYS_FOR_TIMESERIES, PROMETHEUS_NAN_STRING, SCRAPE_INTERVAL_SECONDS
from .schemas import Datapoint, DatapointMetadataBase, DatapointsWithMetadata, MetricsTimeseries, TimeseriesRange


def validate_datetime_range(start: datetime, end: datetime) -> None:
    """Validate datetime range for metrics queries.

    Raises:
        ValidationException: If start is not before end or range is invalid
    """
    if start >= end:
        raise ValidationException("start time must be before end time")

    if start < datetime.now(UTC) - timedelta(days=MAX_DAYS_FOR_TIMESERIES):
        raise ValidationException(f"start time must be within the last {MAX_DAYS_FOR_TIMESERIES} days")


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
    """Given a step for the range query, return the lookback window for aggregation.

    The minimum lookback is 4x the scrape interval to guarantee enough data points
    for both rate() (needs >=2 points) and *_over_time() queries, accounting for
    possible missed scrapes and boundary alignment.
    """
    min_lookback = SCRAPE_INTERVAL_SECONDS * 4

    if not step or step <= min_lookback:
        return f"{min_lookback}s"
    elif step < timedelta(hours=1).total_seconds():
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
        for i in range(floor((end - start).total_seconds() / step) + 1)
    }


def map_metrics_timeseries(
    results: list[dict], start: datetime, end: datetime, step: float, series_label: str
) -> MetricsTimeseries:
    """
    Maps the timeseries data returned from Prometheus.
    Fills in missing datapoints with None values.
    """
    datapoints = __get_default_datapoints_for_range(start=start, end=end, step=step)

    data: list[DatapointsWithMetadata] = []

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
        interval_seconds=int(step),
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
