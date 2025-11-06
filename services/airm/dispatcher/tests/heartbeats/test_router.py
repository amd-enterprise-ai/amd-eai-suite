# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from airm.messaging.schemas import HeartbeatMessage
from app import app  # type: ignore
from app.config.app_config import AppConfig
from app.messaging.publisher import get_common_vhost_connection_and_channel

config = AppConfig()
config.set_config("test_org", "test_cluster")


@pytest.fixture
def mock_connection_dependency():
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()

    async def mock_get_connection():
        return (mock_connection, mock_channel)

    original_dependencies = app.dependency_overrides.copy()
    app.dependency_overrides[get_common_vhost_connection_and_channel] = mock_get_connection

    yield mock_connection, mock_channel

    app.dependency_overrides = original_dependencies


@pytest.mark.asyncio
async def test_send_heartbeat_success(mock_connection_dependency):
    mock_connection, mock_channel = mock_connection_dependency

    with patch("app.heartbeats.router.publish_heartbeat_message_to_queue") as mock_publish:
        mock_publish.return_value = HeartbeatMessage(
            message_type="heartbeat",
            last_heartbeat_at="2025-03-10T22:30:15.683777Z",
            cluster_name="test_cluster",
            organization_name="test_org",
        )

        with TestClient(app) as client:
            response = client.post("/v1/heartbeats")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {
        "message_type": "heartbeat",
        "last_heartbeat_at": "2025-03-10T22:30:15.683777Z",
        "cluster_name": "test_cluster",
        "organization_name": "test_org",
    }
    mock_publish.assert_called_once_with(mock_connection, mock_channel)


@pytest.mark.asyncio
async def test_send_heartbeat_exception(mock_connection_dependency):
    mock_connection, mock_channel = mock_connection_dependency
    with patch(
        "app.heartbeats.router.publish_heartbeat_message_to_queue",
        side_effect=HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR),
    ):
        with TestClient(app) as client:
            response = client.post("/v1/heartbeats")

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
