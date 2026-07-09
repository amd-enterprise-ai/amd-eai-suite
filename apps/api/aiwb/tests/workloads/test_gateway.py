# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for workloads gateway layer - K8s interaction functions."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes.client import ApiException, V1DeleteOptions

from app.workloads.constants import WORKLOAD_RESOURCES
from app.workloads.gateway import delete_workload_resources


def _get_propagation_policy(body: object) -> str | None:
    """Extract propagation policy from either a V1DeleteOptions object or a dict."""
    if isinstance(body, V1DeleteOptions):
        return body.propagation_policy
    if isinstance(body, dict):
        return body.get("propagation_policy") or body.get("propagationPolicy")
    return None


@pytest.mark.asyncio
async def test_delete_workload_resources_requests_background_propagation() -> None:
    """Deletion must request Background propagation so dependents (e.g., Kueue Workload) cascade."""
    workload_id = str(uuid4())
    namespace = "test-namespace"

    mock_api_resource = MagicMock()
    mock_dynamic_client = MagicMock()
    mock_dynamic_client.resources.get.return_value = mock_api_resource

    with patch("app.workloads.gateway.get_dynamic_client", return_value=mock_dynamic_client):
        await delete_workload_resources(namespace=namespace, workload_id=workload_id)

    assert mock_api_resource.delete.call_count == len(WORKLOAD_RESOURCES)
    for call in mock_api_resource.delete.call_args_list:
        body = call.kwargs.get("body")
        assert body is not None, "delete must be called with a body to control propagation"
        assert _get_propagation_policy(body) == "Background"


@pytest.mark.asyncio
async def test_delete_workload_resources_continues_when_resource_not_found() -> None:
    """A 404 on one resource kind must not stop deletion of the remaining kinds."""
    workload_id = str(uuid4())
    namespace = "test-namespace"

    mock_api_resource = MagicMock()
    mock_api_resource.delete.side_effect = [ApiException(status=404)] + [None] * (len(WORKLOAD_RESOURCES) - 1)
    mock_dynamic_client = MagicMock()
    mock_dynamic_client.resources.get.return_value = mock_api_resource

    with patch("app.workloads.gateway.get_dynamic_client", return_value=mock_dynamic_client):
        await delete_workload_resources(namespace=namespace, workload_id=workload_id)

    assert mock_api_resource.delete.call_count == len(WORKLOAD_RESOURCES)


@pytest.mark.asyncio
async def test_delete_workload_resources_raises_on_non_404_api_error() -> None:
    """Non-404 API errors must surface as RuntimeError so the caller can react."""
    workload_id = str(uuid4())
    namespace = "test-namespace"

    mock_api_resource = MagicMock()
    mock_api_resource.delete.side_effect = ApiException(status=500, reason="Internal Server Error")
    mock_dynamic_client = MagicMock()
    mock_dynamic_client.resources.get.return_value = mock_api_resource

    with (
        patch("app.workloads.gateway.get_dynamic_client", return_value=mock_dynamic_client),
        pytest.raises(RuntimeError),
    ):
        await delete_workload_resources(namespace=namespace, workload_id=workload_id)
