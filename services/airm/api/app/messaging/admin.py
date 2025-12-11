# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from secrets import token_hex
from uuid import UUID

import httpx
from loguru import logger

from airm.utilities.http_request import delete_request, put_request

from .config import RABBITMQ_ADMIN_PASSWORD, RABBITMQ_ADMIN_USER, RABBITMQ_AIRM_COMMON_VHOST, RABBITMQ_MANAGEMENT_URL


async def create_vhost_and_user(cluster_id: UUID) -> str:
    auth = httpx.BasicAuth(username=RABBITMQ_ADMIN_USER, password=RABBITMQ_ADMIN_PASSWORD)

    vhost_name = f"vh_{cluster_id}"
    queue_user = f"{cluster_id}"
    user_secret = token_hex(32)

    async with httpx.AsyncClient(auth=auth) as client:
        # Create vhost for outbound cluster queue
        await put_request(client, f"{RABBITMQ_MANAGEMENT_URL}/vhosts/{vhost_name}")

        # Create user
        user_data = {"password": user_secret, "tags": "management"}
        await put_request(client, f"{RABBITMQ_MANAGEMENT_URL}/users/{queue_user}", user_data)

        # Configure the dispatcher user's permissions on the queue to receive messages from AIRM.
        # Only reading allowed
        permissions_data = {"configure": ".*", "write": "^$", "read": ".*"}
        await put_request(client, f"{RABBITMQ_MANAGEMENT_URL}/permissions/{vhost_name}/{queue_user}", permissions_data)

        # Configure the dispatcher user's permissions on the queue to send messages to AIRM.
        # Only writing allowed
        permissions_data = {"configure": ".*", "write": ".*", "read": "^$"}
        await put_request(
            client, f"{RABBITMQ_MANAGEMENT_URL}/permissions/{RABBITMQ_AIRM_COMMON_VHOST}/{queue_user}", permissions_data
        )

    return user_secret


async def configure_inbound_vhost() -> None:
    auth = httpx.BasicAuth(username=RABBITMQ_ADMIN_USER, password=RABBITMQ_ADMIN_PASSWORD)

    async with httpx.AsyncClient(auth=auth) as client:
        # Create vhost for inbound cluster queue
        # This will be created once and subsequent requests will return 204.
        logger.info(f"Creating vhost {RABBITMQ_AIRM_COMMON_VHOST}")
        await put_request(client, f"{RABBITMQ_MANAGEMENT_URL}/vhosts/{RABBITMQ_AIRM_COMMON_VHOST}")
        logger.info(f"Vhost {RABBITMQ_AIRM_COMMON_VHOST} created successfully")


async def delete_vhost_and_user(cluster_id: UUID) -> None:
    auth = httpx.BasicAuth(username=RABBITMQ_ADMIN_USER, password=RABBITMQ_ADMIN_PASSWORD)

    vhost_name = f"vh_{cluster_id}"
    queue_user = f"{cluster_id}"

    async with httpx.AsyncClient(auth=auth) as client:
        await delete_request(client, f"{RABBITMQ_MANAGEMENT_URL}/users/{queue_user}", allow_not_found=True)
        await delete_request(client, f"{RABBITMQ_MANAGEMENT_URL}/vhosts/{vhost_name}", allow_not_found=True)
