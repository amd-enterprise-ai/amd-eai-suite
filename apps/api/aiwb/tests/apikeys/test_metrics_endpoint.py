# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app import app  # type: ignore[attr-defined]
from app.apikeys.schemas import (
    ApiKeyMetricsDataPoint,
    ApiKeyMetricsResponse,
    ApiKeyMetricsStats,
    ApiKeyRequestsTimeseries,
    ApiKeyTokensTimeseries,
)
from tests.dependency_overrides import PROMETHEUS_OVERRIDES, override_dependencies

_START = datetime.now(UTC) - timedelta(hours=1)
_END = datetime.now(UTC) - timedelta(seconds=30)
_API_KEY_ID = str(uuid4())
_PROJECT = "test-namespace"


def _make_metrics_response() -> ApiKeyMetricsResponse:
    dp: ApiKeyMetricsDataPoint = {"date": "2024-01-01T00:00:00Z", "svc": 1.0}
    return ApiKeyMetricsResponse(
        stats=ApiKeyMetricsStats(
            total_requests=5,
            successful_requests=4,
            failed_requests=1,
            total_tokens=300,
            linked_deployments=1,
        ),
        services=["svc"],
        requests_over_time=ApiKeyRequestsTimeseries(total=[dp], successful=[dp], failed=[dp]),
        tokens_over_time=ApiKeyTokensTimeseries(total=[dp], input=[dp], output=[dp]),
    )


@override_dependencies(PROMETHEUS_OVERRIDES)
def test_get_api_key_metrics_returns_200() -> None:
    expected = _make_metrics_response()

    with patch("app.apikeys.router.get_api_key_usage_metrics", new=AsyncMock(return_value=expected)):
        with TestClient(app) as client:
            response = client.get(
                f"/v1/projects/{_PROJECT}/api-keys/{_API_KEY_ID}/metrics",
                params={"start": _START.isoformat(), "end": _END.isoformat()},
            )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["stats"]["totalRequests"] == 5
    assert body["stats"]["successfulRequests"] == 4
    assert body["stats"]["failedRequests"] == 1
    assert body["stats"]["totalTokens"] == 300
    assert body["services"] == ["svc"]


@override_dependencies(PROMETHEUS_OVERRIDES)
def test_get_api_key_metrics_delegates_to_service() -> None:
    expected = _make_metrics_response()

    with patch("app.apikeys.router.get_api_key_usage_metrics", new=AsyncMock(return_value=expected)):
        with TestClient(app) as client:
            response = client.get(
                f"/v1/projects/{_PROJECT}/api-keys/{_API_KEY_ID}/metrics",
                params={"start": _START.isoformat(), "end": _END.isoformat()},
            )

    assert response.status_code == status.HTTP_200_OK


@override_dependencies(PROMETHEUS_OVERRIDES)
def test_get_api_key_metrics_invalid_time_range_returns_400() -> None:
    with TestClient(app) as client:
        response = client.get(
            f"/v1/projects/{_PROJECT}/api-keys/{_API_KEY_ID}/metrics",
            params={"start": _END.isoformat(), "end": _START.isoformat()},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
