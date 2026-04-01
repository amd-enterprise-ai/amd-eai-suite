# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pydantic
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.constants import (
    MAX_DAYS_FOR_TIMESERIES,
    PROJECT_ID_METRIC_LABEL,
    PROMETHEUS_INF_STRING,
    PROMETHEUS_MINUS_INF_STRING,
    PROMETHEUS_NAN_STRING,
)
from app.metrics.schemas import MetricsTimeRange
from app.metrics.utils import (
    build_node_device_query,
    build_workload_device_query,
    convert_prometheus_string_to_float,
    get_aggregation_lookback_for_metrics,
    get_step_for_range_query,
    is_valid_metric_value,
    map_metrics_timeseries,
    map_timeseries_split_by_project,
    parse_device_range_timeseries,
    validate_datetime_range,
)
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from tests import factory  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "start_time_offset,end_time_offset,expected_step",
    [
        (0, 3600, 60),  # 1 hour range, step = 1 minute
        (0, 86400, 300),  # 24 hours range, step = 5 minutes
        (0, 604800, 3600),  # 1 week range, step = 1 hour
    ],
)
def test_get_step_for_range_query(start_time_offset, end_time_offset, expected_step):
    start_time = datetime.now(tz=UTC)
    end_time = start_time + timedelta(seconds=end_time_offset)
    result = get_step_for_range_query(start_time, end_time)
    assert result == expected_step


def test_get_step_for_range_query_raises_error_for_time_range_exceeding_max_days():
    start_time = datetime.now(tz=UTC)
    end_time = start_time + timedelta(days=MAX_DAYS_FOR_TIMESERIES + 1)
    with pytest.raises(ValueError, match=f"Time range is too large.*{MAX_DAYS_FOR_TIMESERIES} days"):
        get_step_for_range_query(start_time, end_time)


@pytest.mark.parametrize(
    "start_offset,end_offset,expected_exception,expected_message",
    [
        (0, -1, ValueError, "Start date must be before end time."),  # Start is after end
        (
            -MAX_DAYS_FOR_TIMESERIES - 1,
            -1,
            ValueError,
            f"Start date must be within the last {MAX_DAYS_FOR_TIMESERIES} days.",
        ),  # Start too far in the past
    ],
)
def test_validate_datetime_range_raises_error(start_offset, end_offset, expected_exception, expected_message):
    start = datetime.now(tz=UTC) + timedelta(days=start_offset)
    end = datetime.now(tz=UTC) + timedelta(days=end_offset)
    with pytest.raises(expected_exception, match=expected_message):
        validate_datetime_range(start, end)


def test_validate_datetime_range():
    start = datetime.now(tz=UTC) - timedelta(days=MAX_DAYS_FOR_TIMESERIES - 1)
    end = datetime.now(tz=UTC) - timedelta(hours=1)
    validate_datetime_range(start, end)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, False),
        ("", False),
        (PROMETHEUS_NAN_STRING, False),
        (PROMETHEUS_INF_STRING, False),
        (PROMETHEUS_MINUS_INF_STRING, False),
        ("42.5", True),
        ("0", True),
        ("100", True),
        (42.5, True),
        (0.0, True),
        (100.0, True),
    ],
)
def test_is_valid_metric_value_valid_and_invalid_strings(value, expected):
    assert is_valid_metric_value(value) is expected


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_is_valid_metric_value_rejects_non_finite_floats(value):
    assert is_valid_metric_value(value) is False


async def test_map_timeseries_split_by_project_without_default_timeseries(db_session: AsyncSession) -> None:
    start = datetime.now(tz=UTC) - timedelta(hours=1)
    end = datetime.now(tz=UTC)
    step = 300.0

    cluster = await factory.create_cluster(db_session, id=UUID("f33bf805-2a5f-4f01-8e3b-339fd8c9e092"))
    project1 = await factory.create_project(
        db_session,
        cluster,
        id=UUID("75a0e0cb-06b3-460e-80cc-54bb201ef4a3"),
        name="group1",
        description="Test Group 1",
        project_status=ProjectStatus.READY,
    )
    project2 = await factory.create_project(
        db_session,
        cluster,
        id=UUID("36fae1b6-b65b-47b9-883d-7899ec05a27b"),
        name="group2",
        description="Test Group 2",
        project_status=ProjectStatus.READY,
    )
    projects = [project1, project2]

    results = [
        {
            "metric": {PROJECT_ID_METRIC_LABEL: str(projects[0].id)},
            "values": [
                (start.timestamp(), 0.1),
                (start.timestamp() + step, 0.3),
                (start.timestamp() + 2 * step, 0.5),
            ],
        },
        {
            "metric": {PROJECT_ID_METRIC_LABEL: str(projects[1].id)},
            "values": [
                (start.timestamp(), 0.3),
                (start.timestamp() + step, 0.2),
            ],
        },
        {
            "metric": {PROJECT_ID_METRIC_LABEL: uuid4()},
            "values": [
                (start.timestamp(), 0.3),
            ],
        },
    ]

    result = map_timeseries_split_by_project(results, projects, start, end, step, "Test Series")

    normalized_start = start.replace(microsecond=0)
    assert len(result.data) == 2
    assert len(result.data[0].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == normalized_start
    assert result.data[0].values[0].value == 0.1
    assert result.data[0].values[1].value == 0.3
    assert result.data[0].values[2].value == 0.5
    assert result.data[0].values[3].value is None
    assert result.data[0].metadata.project.id == projects[0].id
    assert result.data[0].metadata.label == "Test Series"

    assert len(result.data[1].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == normalized_start
    assert result.data[1].values[0].value == 0.3
    assert result.data[1].values[1].value == 0.2
    assert result.data[1].values[2].value is None
    assert result.data[1].metadata.project.id == projects[1].id
    assert result.data[1].metadata.label == "Test Series"

    assert result.range.start == start
    assert result.range.end == end
    assert result.range.interval_seconds == step


async def test_map_timeseries_split_by_project_default_timeseries(db_session: AsyncSession) -> None:
    start = datetime.now(tz=UTC) - timedelta(hours=1)
    end = datetime.now(tz=UTC)
    step = 300.0

    cluster = await factory.create_cluster(db_session, id=UUID("f33bf805-2a5f-4f01-8e3b-339fd8c9e092"))
    project1 = await factory.create_project(
        db_session,
        cluster,
        id=UUID("75a0e0cb-06b3-460e-80cc-54bb201ef4a3"),
        name="group1",
        description="Test Group 1",
        project_status=ProjectStatus.READY,
    )
    project2 = await factory.create_project(
        db_session,
        cluster,
        id=UUID("36fae1b6-b65b-47b9-883d-7899ec05a27b"),
        name="group2",
        description="Test Group 2",
        project_status=ProjectStatus.READY,
    )
    projects = [project1, project2]

    results = [
        {
            "metric": {PROJECT_ID_METRIC_LABEL: str(projects[0].id)},
            "values": [
                (start.timestamp(), 0.1),
                (start.timestamp() + step, 0.3),
                (start.timestamp() + 2 * step, 0.5),
            ],
        },
        {
            "metric": {PROJECT_ID_METRIC_LABEL: str(projects[1].id)},
            "values": [
                (start.timestamp(), 0.3),
                (start.timestamp() + step, 0.2),
            ],
        },
        {
            "metric": {},
            "values": [
                (start.timestamp(), 0.1),
                (start.timestamp() + step, 0.3),
                (start.timestamp() + 2 * step, 0.5),
                (start.timestamp() + 3 * step, 0.5),
            ],
        },
    ]

    result = map_timeseries_split_by_project(results, projects, start, end, step, "Test Series")

    normalized_start = start.replace(microsecond=0)
    assert len(result.data) == 2
    assert len(result.data[0].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == normalized_start
    assert result.data[0].values[0].value == 0.1
    assert result.data[0].values[1].value == 0.3
    assert result.data[0].values[2].value == 0.5
    assert result.data[0].values[3].value == 0.0
    assert result.data[0].metadata.project.id == projects[0].id
    assert result.data[0].metadata.label == "Test Series"

    assert len(result.data[1].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == normalized_start
    assert result.data[1].values[0].value == 0.3
    assert result.data[1].values[1].value == 0.2
    assert result.data[1].values[2].value == 0.0
    assert result.data[1].values[3].value == 0.0
    assert result.data[1].metadata.project.id == projects[1].id
    assert result.data[1].metadata.label == "Test Series"

    assert result.range.start == start
    assert result.range.end == end
    assert result.range.interval_seconds == step


@pytest.mark.parametrize(
    "step,expected_lookback",
    [
        (timedelta(minutes=1).total_seconds(), "1m"),
        (timedelta(minutes=5).total_seconds(), "5m"),
        (timedelta(minutes=10).total_seconds(), "5m"),
        (timedelta(hours=1).total_seconds(), "1h"),
        (None, "1m"),  # Default 1m
    ],
)
def test_get_aggregation_lookback_for_metrics(step, expected_lookback):
    result = get_aggregation_lookback_for_metrics(step)
    assert result == expected_lookback


def test_get_aggregation_lookback_for_metrics_no_step():
    """Test that when no step is provided, defaults to 1m lookback."""
    assert get_aggregation_lookback_for_metrics() == "1m"
    assert get_aggregation_lookback_for_metrics(step=None) == "1m"


@pytest.mark.parametrize(
    "project",
    [
        Project(
            id=uuid4(),
            name="test-project",
            description="Test Description",
            status=ProjectStatus.READY,
            cluster_id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        None,
    ],
)
def test_map_metrics_timeseries_with_project(project):
    start = datetime.now(UTC)
    results = [
        {
            "values": [
                (start.timestamp(), "NaN"),
                (start.timestamp() + 60, "30"),
            ],
        }
    ]
    end = start + timedelta(minutes=2)
    step = 60
    series_label = "Test Series"

    timeseries = map_metrics_timeseries(results, project, start, end, step, series_label)

    assert len(timeseries.data) == 1
    assert len(timeseries.data[0].values) == 3
    assert timeseries.data[0].values[0].value is None
    assert timeseries.data[0].values[1].value == 30.0
    assert timeseries.data[0].values[2].value is None

    if project:
        assert timeseries.data[0].metadata.project.id == project.id
    else:
        assert "project" not in timeseries.data[0].metadata.__dict__


def test_convert_prometheus_string_to_float():
    # Test with regular numeric string
    assert convert_prometheus_string_to_float("123.45") == 123.45
    assert convert_prometheus_string_to_float("0") == 0.0
    assert convert_prometheus_string_to_float("-10.5") == -10.5
    assert convert_prometheus_string_to_float(PROMETHEUS_NAN_STRING) == 0.0


def test_convert_prometheus_string_to_float_with_invalid_input():
    # Test with invalid inputs - should raise ValueError
    with pytest.raises(ValueError):
        convert_prometheus_string_to_float("not-a-number")

    with pytest.raises(ValueError):
        convert_prometheus_string_to_float("")


def test_build_workload_device_query_with_lookback():
    query = build_workload_device_query("wid-123", "gpu_junction_temperature", "avg", use_lookback=True, lookback="5m")
    assert 'workload_id="wid-123"' in query
    assert "avg by (gpu_id, gpu_uuid, hostname)" in query
    assert "avg_over_time(gpu_junction_temperature" in query
    assert "[5m]" in query


def test_build_workload_device_query_without_lookback():
    query = build_workload_device_query("wid-456", "gpu_package_power", "sum", use_lookback=False)
    assert 'workload_id="wid-456"' in query
    assert "sum by (gpu_id, gpu_uuid, hostname)" in query
    assert "gpu_package_power" in query
    assert "avg_over_time" not in query


def test_parse_device_range_timeseries_single_device():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 2, 18, 0, 10, 0, tzinfo=UTC)
    step = 300.0

    results = [
        {
            "metric": {"gpu_uuid": "gpu-aaa", "hostname": "node-1", "gpu_id": "0"},
            "values": [
                (start.timestamp(), "42.5"),
                (start.timestamp() + step, "43.0"),
                (start.timestamp() + 2 * step, "44.0"),
            ],
        }
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    assert len(parsed) == 1
    key = ("gpu-aaa", "node-1", "0")
    assert key in parsed
    datapoints = parsed[key]
    assert len(datapoints) == 3
    assert datapoints[0].value == 42.5
    assert datapoints[1].value == 43.0
    assert datapoints[2].value == 44.0
    assert datapoints[0].timestamp == start


def test_parse_device_range_timeseries_fills_missing_with_none():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 2, 18, 0, 10, 0, tzinfo=UTC)
    step = 300.0

    results = [
        {
            "metric": {"gpu_uuid": "gpu-bbb", "hostname": "node-2", "gpu_id": "1"},
            "values": [
                (start.timestamp(), "10.0"),
            ],
        }
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    key = ("gpu-bbb", "node-2", "1")
    datapoints = parsed[key]
    assert len(datapoints) == 3
    assert datapoints[0].value == 10.0
    assert datapoints[1].value is None
    assert datapoints[2].value is None


def test_parse_device_range_timeseries_multiple_devices():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 2, 18, 0, 5, 0, tzinfo=UTC)
    step = 300.0

    results = [
        {
            "metric": {"gpu_uuid": "gpu-1", "hostname": "node-a", "gpu_id": "0"},
            "values": [(start.timestamp(), "1.0"), (start.timestamp() + step, "2.0")],
        },
        {
            "metric": {"gpu_uuid": "gpu-2", "hostname": "node-a", "gpu_id": "1"},
            "values": [(start.timestamp(), "3.0"), (start.timestamp() + step, "4.0")],
        },
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    assert len(parsed) == 2
    assert ("gpu-1", "node-a", "0") in parsed
    assert ("gpu-2", "node-a", "1") in parsed
    assert parsed[("gpu-1", "node-a", "0")][0].value == 1.0
    assert parsed[("gpu-2", "node-a", "1")][1].value == 4.0


def test_parse_device_range_timeseries_skips_nan():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 2, 18, 0, 5, 0, tzinfo=UTC)
    step = 300.0

    results = [
        {
            "metric": {"gpu_uuid": "gpu-x", "hostname": "node-y", "gpu_id": "0"},
            "values": [
                (start.timestamp(), "NaN"),
                (start.timestamp() + step, "50.0"),
            ],
        }
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    key = ("gpu-x", "node-y", "0")
    assert parsed[key][0].value is None
    assert parsed[key][1].value == 50.0


def test_parse_device_range_timeseries_skips_missing_labels():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 2, 18, 0, 5, 0, tzinfo=UTC)
    step = 300.0

    results = [
        {
            "metric": {"hostname": "node-1"},
            "values": [(start.timestamp(), "1.0")],
        },
        {
            "metric": {"gpu_uuid": "gpu-1"},
            "values": [(start.timestamp(), "2.0")],
        },
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)
    assert len(parsed) == 0


def test_parse_device_range_timeseries_defaults_gpu_id_to_empty():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 2, 18, 0, 5, 0, tzinfo=UTC)
    step = 300.0

    results = [
        {
            "metric": {"gpu_uuid": "gpu-no-id", "hostname": "node-z"},
            "values": [(start.timestamp(), "99.0")],
        }
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    key = ("gpu-no-id", "node-z", "")
    assert key in parsed
    assert parsed[key][0].value == 99.0


def test_build_node_device_query():
    query = build_node_device_query("worker-1", "my-cluster", "gpu_gfx_activity", "avg", "5m")
    assert 'hostname="worker-1"' in query
    assert 'kube_cluster_name="my-cluster"' in query
    assert "avg by (gpu_id, gpu_uuid, hostname)" in query
    assert "avg_over_time(gpu_gfx_activity" in query
    assert "[5m]" in query


def test_build_node_device_query_different_aggregation():
    query = build_node_device_query("node-2", "cluster-x", "gpu_gfx_activity", "sum", "1h")
    assert "sum by (gpu_id, gpu_uuid, hostname)" in query
    assert "[1h]" in query


# ── MetricsTimeRange.step validation ────────────────────────────────────────


def test_metrics_time_range_step_none_is_accepted():
    now = datetime.now(UTC)
    tr = MetricsTimeRange(start=now - timedelta(hours=1), end=now)
    assert tr.step is None


def test_metrics_time_range_step_valid():
    now = datetime.now(UTC)
    tr = MetricsTimeRange(start=now - timedelta(hours=1), end=now, step=300)
    assert tr.step == 300


def test_metrics_time_range_step_rejects_zero():
    now = datetime.now(UTC)
    with pytest.raises(pydantic.ValidationError, match="step"):
        MetricsTimeRange(start=now - timedelta(hours=1), end=now, step=0)


# ── parse_device_range_timeseries – simplified alignment ─────────────────────


def test_parse_device_range_timeseries_start_with_microseconds():
    """Start with sub-second precision is normalised; Prometheus timestamps align after .replace(microsecond=0)."""
    start = datetime(2026, 2, 18, 0, 0, 0, 500_000, tzinfo=UTC)  # 0.5s microseconds
    step = 60.0
    end = start + timedelta(seconds=step * 2)

    normalized_start = start.replace(microsecond=0)
    results = [
        {
            "metric": {"gpu_uuid": "gpu-aaa", "hostname": "node-1", "gpu_id": "0"},
            "values": [
                (normalized_start.timestamp(), "10.0"),
                ((normalized_start + timedelta(seconds=step)).timestamp(), "20.0"),
            ],
        }
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    key = ("gpu-aaa", "node-1", "0")
    assert key in parsed
    datapoints = parsed[key]
    assert datapoints[0].value == 10.0
    assert datapoints[1].value == 20.0
    assert datapoints[2].value is None


def test_parse_device_range_timeseries_empty_results():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    end = start + timedelta(minutes=5)

    parsed = parse_device_range_timeseries([], start, end, 300.0)

    assert parsed == {}


def test_parse_device_range_timeseries_all_nan_values_are_none():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    step = 300.0
    end = start + timedelta(seconds=step)

    results = [
        {
            "metric": {"gpu_uuid": "gpu-z", "hostname": "node-1", "gpu_id": "0"},
            "values": [
                (start.timestamp(), "NaN"),
                ((start + timedelta(seconds=step)).timestamp(), "NaN"),
            ],
        }
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    key = ("gpu-z", "node-1", "0")
    assert all(dp.value is None for dp in parsed[key])


def test_parse_device_range_timeseries_datapoints_are_sorted_by_timestamp():
    start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
    step = 300.0
    end = start + timedelta(seconds=step * 3)

    results = [
        {
            "metric": {"gpu_uuid": "gpu-s", "hostname": "node-1", "gpu_id": "0"},
            "values": [
                ((start + timedelta(seconds=step * 2)).timestamp(), "30.0"),
                (start.timestamp(), "10.0"),
                ((start + timedelta(seconds=step)).timestamp(), "20.0"),
            ],
        }
    ]

    parsed = parse_device_range_timeseries(results, start, end, step)

    key = ("gpu-s", "node-1", "0")
    timestamps = [dp.timestamp for dp in parsed[key]]
    assert timestamps == sorted(timestamps)
    assert parsed[key][0].value == 10.0
    assert parsed[key][1].value == 20.0
    assert parsed[key][2].value == 30.0


def test_build_node_device_query_with_extra_filters():
    query = build_node_device_query(
        "worker-1",
        "my-cluster",
        "gpu_clock",
        "avg",
        "5m",
        extra_filters={"clock_type": "GPU_CLOCK_TYPE_SYSTEM"},
    )
    assert 'hostname="worker-1"' in query
    assert 'kube_cluster_name="my-cluster"' in query
    assert 'clock_type="GPU_CLOCK_TYPE_SYSTEM"' in query
    assert "avg_over_time(gpu_clock" in query
    assert "[5m]" in query


def test_build_node_device_query_with_multiple_extra_filters():
    query = build_node_device_query(
        "node-1",
        "cluster-a",
        "gpu_clock",
        "avg",
        "1m",
        extra_filters={"clock_type": "GPU_CLOCK_TYPE_SYSTEM", "extra_label": "extra_value"},
    )
    assert 'clock_type="GPU_CLOCK_TYPE_SYSTEM"' in query
    assert 'extra_label="extra_value"' in query
    assert 'hostname="node-1"' in query


def test_build_node_device_query_no_extra_filters_unchanged():
    """Omitting extra_filters produces the same result as passing None."""
    query_default = build_node_device_query("worker-1", "my-cluster", "gpu_gfx_activity", "avg", "5m")
    query_explicit_none = build_node_device_query(
        "worker-1", "my-cluster", "gpu_gfx_activity", "avg", "5m", extra_filters=None
    )
    assert query_default == query_explicit_none
