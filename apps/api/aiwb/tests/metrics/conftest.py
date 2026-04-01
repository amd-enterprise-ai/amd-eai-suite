# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Fixtures for metrics tests - kept minimal, use factory functions instead."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from prometheus_api_client import PrometheusConnect


@pytest.fixture
def mock_prometheus_client() -> Mock:
    """Create a mock Prometheus client for metrics testing.

    Note: Uses Mock (not AsyncMock) because PrometheusConnect methods are synchronous
    and wrapped with asyncio.to_thread() in the service layer.
    """
    return Mock(spec=PrometheusConnect)


@pytest.fixture
def time_range() -> tuple[datetime, datetime]:
    """Provide a standard 1-hour time range for metrics testing."""
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    return start, end
