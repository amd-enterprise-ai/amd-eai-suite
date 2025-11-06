# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from aio_pika import abc
from aio_pika.exceptions import AMQPConnectionError
from pamqp.exceptions import AMQPInternalError

from airm.messaging.connector import (
    __cluster_connections,
    get_connection_to_cluster_vhost,
    get_connection_to_common_vhost,
    init_connection,
)


@pytest.mark.asyncio
async def test_rabbitmq_connection_successful(rabbitmq_service):
    docker_ip, port = rabbitmq_service
    connection = None
    channel = None

    try:
        connection, channel = await init_connection(
            host=docker_ip, port=port, vhost="vh_airm_common", username="guest", password="guest"
        )

        assert connection is not None
        assert not connection.is_closed
        assert channel is not None
        assert not channel.is_closed

    finally:
        # Cleanup
        if channel and not channel.is_closed:
            await channel.close()
        if connection and not connection.is_closed:
            await connection.close()


@pytest.mark.asyncio
async def test_rabbitmq_connection_invalid_host():
    connection = None
    channel = None

    try:
        with pytest.raises((ConnectionError, AMQPConnectionError)) as exc_info:
            connection, channel = await init_connection(
                host="non_existent_host", port=5672, vhost="vh_airm_common", username="guest", password="guest"
            )
        error_msg = str(exc_info.value).lower()
        assert any(
            x in error_msg
            for x in [
                "nodename nor servname provided",
                "name or service not known",
                "temporary failure in name resolution",
                "no address associated with hostname",
            ]
        )
        assert connection is None
        assert channel is None
    finally:
        if channel and not channel.is_closed:
            await channel.close()
        if connection and not connection.is_closed:
            await connection.close()


@pytest.mark.asyncio
async def test_rabbitmq_connection_invalid_port(rabbitmq_service):
    docker_ip, _ = rabbitmq_service
    connection = None
    channel = None

    try:
        with pytest.raises((ConnectionError, AMQPConnectionError)) as exc_info:
            connection, channel = await init_connection(
                host=docker_ip, port=9999, vhost="vh_airm_common", username="guest", password="guest"
            )
        error_msg = str(exc_info.value).lower()
        assert any(x in error_msg for x in ["connect call failed", "connection refused", "errno"])
        assert connection is None
        assert channel is None
    finally:
        if channel and not channel.is_closed:
            await channel.close()
        if connection and not connection.is_closed:
            await connection.close()


@pytest.mark.asyncio
async def test_rabbitmq_connection_invalid_creds(rabbitmq_service):
    docker_ip, port = rabbitmq_service
    connection = None
    channel = None

    try:
        with pytest.raises(AMQPConnectionError) as exc_info:
            connection, channel = await init_connection(
                host=docker_ip, port=port, vhost="vh_airm_common", username="invalid_user", password="invalid_password"
            )
        assert "ACCESS_REFUSED" in str(exc_info.value)
        assert connection is None
        assert channel is None
    finally:
        if channel and not channel.is_closed:
            await channel.close()
        if connection and not connection.is_closed:
            await connection.close()


@pytest.mark.asyncio
async def test_rabbitmq_connection_invalid_vhost(rabbitmq_service):
    """Test connection fails with invalid vhost."""
    docker_ip, port = rabbitmq_service
    connection = None
    channel = None

    try:
        with pytest.raises((AMQPConnectionError, AMQPInternalError)) as exc_info:
            connection, channel = await init_connection(
                host=docker_ip, port=port, vhost="invalid_vhost", username="guest", password="guest"
            )
        # Either exception message is acceptable
        assert any(msg in str(exc_info.value) for msg in ["NOT_FOUND", "Connection.OpenOk"])
        assert connection is None
        assert channel is None
    finally:
        if channel and not channel.is_closed:
            await channel.close()
        if connection and not connection.is_closed:
            await connection.close()


@pytest.mark.asyncio
@patch("airm.messaging.connector.init_connection")
async def test_get_connection_to_cluster_vhost(mock_init_connection):
    cluster_id = uuid4()
    mock_connection = AsyncMock(spec=abc.AbstractConnection)
    mock_channel = AsyncMock(spec=abc.AbstractChannel)
    mock_init_connection.return_value = (mock_connection, mock_channel)

    connection, channel = await get_connection_to_cluster_vhost(
        cluster_id, host="localhost", port=5672, username="guest", password="guest"
    )

    assert connection == mock_connection
    assert channel == mock_channel
    mock_init_connection.assert_called_once()
    assert cluster_id in __cluster_connections
    assert __cluster_connections[cluster_id] == (mock_connection, mock_channel)


@pytest.mark.asyncio
@patch("airm.messaging.connector.init_connection")
async def test_get_connection_to_common_vhost(mock_init_connection):
    cluster_id = uuid4()
    mock_connection = AsyncMock(spec=abc.AbstractConnection)
    mock_channel = AsyncMock(spec=abc.AbstractChannel)
    mock_init_connection.return_value = (mock_connection, mock_channel)

    connection, channel = await get_connection_to_common_vhost(
        host="localhost", port=5672, vhost=f"vh_{cluster_id}", username="guest", password="guest"
    )

    mock_init_connection.assert_called_once()


@pytest.mark.asyncio
@patch("airm.messaging.connector.init_connection")
async def test_reuse_existing_connection(mock_init_connection):
    cluster_id = uuid4()
    mock_connection = AsyncMock(spec=abc.AbstractConnection)
    mock_channel = AsyncMock(spec=abc.AbstractChannel)
    mock_init_connection.return_value = (mock_connection, mock_channel)

    connection1, channel1 = await get_connection_to_cluster_vhost(
        cluster_id, host="localhost", port=5672, username="guest", password="guest"
    )
    assert connection1 == mock_connection
    assert channel1 == mock_channel
    mock_init_connection.assert_called_once()

    mock_connection.is_closed = False
    mock_channel.is_closed = False

    connection2, channel2 = await get_connection_to_cluster_vhost(
        cluster_id, host="localhost", port=5672, username="guest", password="guest"
    )
    assert connection2 == connection1
    assert channel2 == channel1
    mock_init_connection.assert_called_once()  # Ensure init_connection is not called again

    assert cluster_id in __cluster_connections
    assert __cluster_connections[cluster_id] == (mock_connection, mock_channel)
