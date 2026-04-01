# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Shared fixtures for logs tests."""

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def default_time_range():
    """Default time range for tests."""
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(hours=1)
    return start_date, end_date
