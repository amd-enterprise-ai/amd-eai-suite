# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for metrics service functions."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from app.metrics.service import (
    get_e2e_latency_metric,
    get_gpu_device_utilization_metric,
    get_gpu_memory_utilization_metric,
    get_inter_token_latency_metric,
    get_kv_cache_usage_metric,
    get_max_requests_metric,
    get_total_tokens_metric,
    get_ttft_latency_metric,
)


@pytest.mark.asyncio
async def test_max_requests_metric_returns_peak_value(
    mock_prometheus_client: Mock, time_range: tuple[datetime, datetime]
) -> None:
    """Verify MAX_REQUESTS metric calculates peak concurrent requests correctly."""
    start, end = time_range
    workload_id = "test-workload-456"

    # Mock Prometheus response with peak concurrent requests value
    mock_prometheus_client.custom_query = Mock(return_value=[{"metric": {}, "value": [end.timestamp(), "42"]}])

    result = await get_max_requests_metric(
        workload_id=workload_id,
        start=start,
        end=end,
        prometheus_client=mock_prometheus_client,
    )

    # Verify the metric returns the expected peak value
    assert result.data == 42.0
    assert result.range.start == start
    assert result.range.end == end


@pytest.mark.asyncio
async def test_max_requests_metric_handles_no_data(
    mock_prometheus_client: Mock, time_range: tuple[datetime, datetime]
) -> None:
    """Verify MAX_REQUESTS metric returns 0 when no data available."""
    start, end = time_range
    workload_id = "test-workload-empty"

    # Mock empty Prometheus response
    mock_prometheus_client.custom_query = Mock(return_value=[])

    result = await get_max_requests_metric(
        workload_id=workload_id,
        start=start,
        end=end,
        prometheus_client=mock_prometheus_client,
    )

    # Should return 0 when no data
    assert result.data == 0
    assert result.range.start == start
    assert result.range.end == end


@pytest.mark.asyncio
async def test_max_requests_query_uses_correct_lookback(
    mock_prometheus_client: Mock, time_range: tuple[datetime, datetime]
) -> None:
    """Verify MAX_REQUESTS uses the correct lookback window."""
    start, end = time_range
    workload_id = "test-workload-789"

    mock_prometheus_client.custom_query = Mock(return_value=[{"metric": {}, "value": [end.timestamp(), "10"]}])

    await get_max_requests_metric(
        workload_id=workload_id,
        start=start,
        end=end,
        prometheus_client=mock_prometheus_client,
    )

    # Verify the query was called
    mock_prometheus_client.custom_query.assert_called_once()
    call_args = mock_prometheus_client.custom_query.call_args

    # Extract the query string
    query = call_args.kwargs["query"]

    # Verify the query includes the workload_id and uses max_over_time
    assert f'workload_id="{workload_id}"' in query
    assert "max_over_time" in query
    assert "vllm:num_requests_running" in query
    assert "vllm:num_requests_waiting" in query


@pytest.mark.asyncio
async def test_gpu_metrics_use_simple_queries(
    mock_prometheus_client: Mock, time_range: tuple[datetime, datetime]
) -> None:
    """Verify GPU metrics use simple count/sum without avg_over_time wrapping."""
    start, end = time_range
    workload_id = "test-workload-simple"
    step = 60.0

    mock_prometheus_client.custom_query_range = Mock(
        return_value=[
            {
                "metric": {},
                "values": [[start.timestamp(), "50"]],
            }
        ]
    )

    await get_gpu_device_utilization_metric(
        workload_id=workload_id,
        start=start,
        end=end,
        step=step,
        prometheus_client=mock_prometheus_client,
    )

    call_args = mock_prometheus_client.custom_query_range.call_args
    query = call_args.kwargs["query"]

    assert "count" in query
    assert "gpu_gfx_activity" in query
    assert "avg_over_time" not in query
    assert "max_over_time" not in query


@pytest.mark.asyncio
async def test_all_timeseries_metrics_return_valid_structure(
    mock_prometheus_client: Mock, time_range: tuple[datetime, datetime]
) -> None:
    """Verify all timeseries metrics return the expected structure."""
    start, end = time_range
    workload_id = "test-workload-integrity"
    step = 60.0
    lookback = "2m"

    # Mock response for timeseries metrics
    mock_response = [
        {
            "metric": {},
            "values": [
                [start.timestamp(), "100"],
                [end.timestamp(), "150"],
            ],
        }
    ]

    gpu_metrics = [
        get_gpu_device_utilization_metric,
        get_gpu_memory_utilization_metric,
    ]
    lookback_metrics = [
        get_ttft_latency_metric,
        get_inter_token_latency_metric,
        get_e2e_latency_metric,
    ]

    for metric_func in gpu_metrics:
        mock_prometheus_client.custom_query_range = Mock(return_value=mock_response)

        result = await metric_func(
            workload_id=workload_id,
            start=start,
            end=end,
            step=step,
            prometheus_client=mock_prometheus_client,
        )

        assert hasattr(result, "data"), f"{metric_func.__name__} should have data"
        assert hasattr(result, "range"), f"{metric_func.__name__} should have range"
        assert len(result.data) > 0, f"{metric_func.__name__} should return data"

    for metric_func in lookback_metrics:
        mock_prometheus_client.custom_query_range = Mock(return_value=mock_response)

        result = await metric_func(
            workload_id=workload_id,
            start=start,
            end=end,
            step=step,
            lookback=lookback,
            prometheus_client=mock_prometheus_client,
        )

        # Verify structure
        assert hasattr(result, "data"), f"{metric_func.__name__} should have data"
        assert hasattr(result, "range"), f"{metric_func.__name__} should have range"
        assert len(result.data) > 0, f"{metric_func.__name__} should return data"


@pytest.mark.asyncio
async def test_scalar_metrics_return_valid_structure(
    mock_prometheus_client: Mock, time_range: tuple[datetime, datetime]
) -> None:
    """Verify scalar metrics return the expected structure."""
    start, end = time_range
    workload_id = "test-workload-scalar"

    # Test KV cache (scalar with range)
    mock_prometheus_client.custom_query = Mock(return_value=[{"metric": {}, "value": [end.timestamp(), "85.5"]}])

    kv_result = await get_kv_cache_usage_metric(
        workload_id=workload_id,
        start=start,
        end=end,
        prometheus_client=mock_prometheus_client,
    )

    assert hasattr(kv_result, "data")
    assert hasattr(kv_result, "range")
    assert isinstance(kv_result.data, (int, float))

    # Test total tokens (scalar without range)
    mock_prometheus_client.custom_query = Mock(return_value=[{"metric": {}, "value": [end.timestamp(), "1234"]}])

    tokens_result = await get_total_tokens_metric(
        workload_id=workload_id,
        prometheus_client=mock_prometheus_client,
    )

    assert hasattr(tokens_result, "data")
    assert isinstance(tokens_result.data, (int, float))
