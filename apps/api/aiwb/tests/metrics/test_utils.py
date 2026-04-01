# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for metrics utility functions."""

from datetime import UTC, datetime, timedelta

import pytest

from api_common.exceptions import ValidationException
from app.metrics.constants import MAX_DAYS_FOR_TIMESERIES
from app.metrics.utils import (
    get_aggregation_lookback_for_metrics,
    get_step_for_range_query,
    validate_datetime_range,
)

# Lookback Time Calculation Tests


def test_lookback_for_one_minute_step_uses_2m() -> None:
    """Verify that 1 minute step uses 120s lookback (4x scrape interval)."""
    step = timedelta(minutes=1).total_seconds()
    lookback = get_aggregation_lookback_for_metrics(step)
    assert lookback == "120s", "1 minute step should use 120s lookback (4x30s scrape interval)"


def test_lookback_for_sub_minute_step_uses_2m() -> None:
    """Verify that steps less than minimum use 120s lookback."""
    step = timedelta(seconds=30).total_seconds()
    lookback = get_aggregation_lookback_for_metrics(step)
    assert lookback == "120s", "Sub-minute steps should use 120s lookback"


def test_lookback_for_none_step_uses_2m() -> None:
    """Verify that None step defaults to 120s lookback."""
    lookback = get_aggregation_lookback_for_metrics(None)
    assert lookback == "120s", "None step should default to 120s lookback"


def test_lookback_for_five_minute_step_uses_5m() -> None:
    """Verify that 5 minute step uses 5m lookback."""
    step = timedelta(minutes=5).total_seconds()
    lookback = get_aggregation_lookback_for_metrics(step)
    assert lookback == "5m", "5 minute step should use 5m lookback"


def test_lookback_for_hour_step_uses_1h() -> None:
    """Verify that 1 hour step uses 1h lookback."""
    step = timedelta(hours=1).total_seconds()
    lookback = get_aggregation_lookback_for_metrics(step)
    assert lookback == "1h", "1 hour step should use 1h lookback"


def test_lookback_boundaries() -> None:
    """Test boundary conditions for lookback calculation."""
    # Just under minimum threshold (120s)
    assert get_aggregation_lookback_for_metrics(59) == "120s"

    # Exactly at minimum threshold
    assert get_aggregation_lookback_for_metrics(120) == "120s"

    # Just over minimum threshold
    assert get_aggregation_lookback_for_metrics(121) == "5m"

    # Just under 1 hour
    assert get_aggregation_lookback_for_metrics(3599) == "5m"

    # Exactly 1 hour
    assert get_aggregation_lookback_for_metrics(3600) == "1h"

    # Over 1 hour
    assert get_aggregation_lookback_for_metrics(7200) == "1h"


# Step Calculation Tests


def test_step_for_one_hour_range() -> None:
    """Verify 1 hour range uses 1 minute step."""
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    step = get_step_for_range_query(start, end)
    assert step == 60.0, "1 hour range should use 1 minute step"


def test_step_for_24_hour_range() -> None:
    """Verify 24 hour range uses 5 minute step."""
    end = datetime.now(UTC)
    start = end - timedelta(hours=24)
    step = get_step_for_range_query(start, end)
    assert step == 300.0, "24 hour range should use 5 minute step"


def test_step_for_7_day_range() -> None:
    """Verify 7 day range uses 1 hour step."""
    end = datetime.now(UTC)
    start = end - timedelta(days=7)
    step = get_step_for_range_query(start, end)
    assert step == 3600.0, "7 day range should use 1 hour step"


def test_step_raises_for_too_large_range() -> None:
    """Verify error is raised for time ranges exceeding max days."""
    end = datetime.now(UTC)
    start = end - timedelta(days=MAX_DAYS_FOR_TIMESERIES + 1)

    with pytest.raises(ValueError, match="Time range is too large"):
        get_step_for_range_query(start, end)


# Datetime Range Validation Tests


def test_validates_start_before_end() -> None:
    """Verify validation fails when start is after end."""
    end = datetime.now(UTC)
    start = end + timedelta(hours=1)  # Start after end

    with pytest.raises(ValidationException, match="start time must be before end"):
        validate_datetime_range(start, end)


def test_validates_start_equals_end() -> None:
    """Verify validation fails when start equals end."""
    now = datetime.now(UTC)

    with pytest.raises(ValidationException, match="start time must be before end"):
        validate_datetime_range(now, now)


def test_validates_start_not_too_old() -> None:
    """Verify validation fails when start is beyond max days limit."""
    end = datetime.now(UTC)
    start = end - timedelta(days=MAX_DAYS_FOR_TIMESERIES + 1)

    with pytest.raises(ValidationException, match=f"must be within the last {MAX_DAYS_FOR_TIMESERIES} days"):
        validate_datetime_range(start, end)


def test_accepts_valid_range() -> None:
    """Verify validation passes for valid datetime range."""
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)

    # Should not raise
    validate_datetime_range(start, end)


def test_accepts_range_at_max_boundary() -> None:
    """Verify validation passes at the maximum allowed days boundary."""
    end = datetime.now(UTC)
    start = end - timedelta(days=MAX_DAYS_FOR_TIMESERIES) + timedelta(seconds=1)

    # Should not raise (just within boundary)
    validate_datetime_range(start, end)
