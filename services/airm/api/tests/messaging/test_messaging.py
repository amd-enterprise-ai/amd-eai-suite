# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch
from uuid import UUID

import pytest

from app.messaging.admin import delete_vhost_and_user


@pytest.mark.asyncio
@patch("app.messaging.admin.delete_request", autospec=True)
@patch("app.messaging.admin.httpx.AsyncClient", autospec=True)
@patch.dict("os.environ", {"RABBITMQ_MANAGEMENT_URL": "http://localhost:15672/api"})
async def test_delete_vhost_and_user(mock_async_client, mock_delete_request):
    cluster_id = UUID("0bef7545-e5c2-444c-b514-4688149e5fe2")
    vhost_name = f"vh_{cluster_id}"
    queue_user = f"{cluster_id}"

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value

    await delete_vhost_and_user(cluster_id)

    mock_delete_request.assert_any_call(
        mock_client_instance, f"http://localhost:15672/api/users/{queue_user}", allow_not_found=True
    )
    mock_delete_request.assert_any_call(
        mock_client_instance, f"http://localhost:15672/api/vhosts/{vhost_name}", allow_not_found=True
    )

    assert mock_delete_request.call_count == 2
