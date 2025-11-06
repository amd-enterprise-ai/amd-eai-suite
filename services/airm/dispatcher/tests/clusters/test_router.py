# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app import app  # type: ignore
from app.messaging.publisher import get_common_vhost_connection_and_channel


@pytest.mark.asyncio
@patch("app.clusters.router.publish_cluster_nodes_message_to_queue")
async def test_send_cluster_nodes_to_queue_success(mock_publish):
    app.dependency_overrides[get_common_vhost_connection_and_channel] = lambda: (AsyncMock(), AsyncMock())
    with TestClient(app) as client:
        response = client.post("/v1/clusters/nodes")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_publish.assert_called_once()


@pytest.mark.asyncio
@patch("app.clusters.router.publish_cluster_nodes_message_to_queue")
async def test_send_heartbeat_exception(mock_publish):
    app.dependency_overrides[get_common_vhost_connection_and_channel] = lambda: (AsyncMock(), AsyncMock())
    mock_publish.side_effect = HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    with TestClient(app) as client:
        response = client.post("/v1/clusters/nodes")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
