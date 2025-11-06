# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.metrics.constants import MAX_DAYS_FOR_TIMESERIES, PROJECT_ID_METRIC_LABEL, PROMETHEUS_NAN_STRING
from app.metrics.utils import (
    convert_prometheus_string_to_float,
    get_aggregation_lookback_for_metrics,
    get_step_for_range_query,
    map_metrics_timeseries,
    map_timeseries_split_by_project,
    validate_datetime_range,
)
from app.projects.enums import ProjectStatus
from app.projects.models import Project


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


def test_map_timeseries_split_by_project_without_default_timeseries():
    start = datetime.now(tz=UTC) - timedelta(hours=1)
    end = datetime.now(tz=UTC)
    step = 300.0

    projects = [
        Project(
            id=UUID("75a0e0cb-06b3-460e-80cc-54bb201ef4a3"),
            name="group1",
            description="Test Group 1",
            status=ProjectStatus.READY,
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        Project(
            id=UUID("36fae1b6-b65b-47b9-883d-7899ec05a27b"),
            name="group2",
            description="Test Group 2",
            status=ProjectStatus.READY,
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ]

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

    assert len(result.data) == 2
    assert len(result.data[0].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == start
    assert result.data[0].values[0].value == 0.1
    assert result.data[0].values[1].value == 0.3
    assert result.data[0].values[2].value == 0.5
    assert result.data[0].values[3].value is None
    assert result.data[0].metadata.project.id == projects[0].id
    assert result.data[0].metadata.label == "Test Series"

    assert len(result.data[1].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == start
    assert result.data[1].values[0].value == 0.3
    assert result.data[1].values[1].value == 0.2
    assert result.data[1].values[2].value is None
    assert result.data[1].metadata.project.id == projects[1].id
    assert result.data[1].metadata.label == "Test Series"

    assert result.range.start == start
    assert result.range.end == end
    assert result.range.interval_seconds == step


def test_map_timeseries_split_by_project_default_timeseries():
    start = datetime.now(tz=UTC) - timedelta(hours=1)
    end = datetime.now(tz=UTC)
    step = 300.0

    projects = [
        Project(
            id=UUID("75a0e0cb-06b3-460e-80cc-54bb201ef4a3"),
            name="group1",
            description="Test Group 1",
            status=ProjectStatus.READY,
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        Project(
            id=UUID("36fae1b6-b65b-47b9-883d-7899ec05a27b"),
            name="group2",
            description="Test Group 2",
            status=ProjectStatus.READY,
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ]

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

    assert len(result.data) == 2
    assert len(result.data[0].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == start
    assert result.data[0].values[0].value == 0.1
    assert result.data[0].values[1].value == 0.3
    assert result.data[0].values[2].value == 0.5
    assert result.data[0].values[3].value == 0.0
    assert result.data[0].metadata.project.id == projects[0].id
    assert result.data[0].metadata.label == "Test Series"

    assert len(result.data[1].values) == (end - start).total_seconds() // step + 1
    assert result.data[1].values[0].timestamp == start
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


@pytest.mark.parametrize(
    "project",
    [
        Project(
            id=uuid4(),
            name="test-project",
            description="Test Description",
            status=ProjectStatus.READY,
            cluster_id="b4884301-b87c-4e4a-89bc-e60f458f176d",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        None,
    ],
)
def test_validate_external_secret_manifest_invalid(project):
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
