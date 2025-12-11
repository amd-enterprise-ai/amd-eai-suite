# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from airm.messaging.schemas import HeartbeatMessage
from app.config.app_config import AppConfig
from app.heartbeats.service import publish_heartbeat_message_to_queue


@pytest.mark.asyncio
async def test_publish_heartbeat_message_to_queue() -> None:
    """Test that a heartbeat message is correctly created and published."""
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()

    config = AppConfig()
    config.set_config("test_org", "test_cluster")

    with patch("app.heartbeats.service.publish_to_common_feedback_queue") as mock_publish:
        message = await publish_heartbeat_message_to_queue(mock_connection, mock_channel)

        # Ensure the returned message is of correct type and has expected attributes
        assert isinstance(message, HeartbeatMessage)
        assert message.message_type == "heartbeat"
        assert isinstance(message.last_heartbeat_at, datetime)
        assert message.organization_name == "test_org"
        assert message.cluster_name == "test_cluster"

        # Ensure channel is correctly passed (mock it as None if not provided)
        expected_channel = mock_channel if mock_channel else None

        # Verify the message was published correctly
        mock_publish.assert_awaited_once_with(
            message=message,
            connection=mock_connection,
            channel=expected_channel,
        )
