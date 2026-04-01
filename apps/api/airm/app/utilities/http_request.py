# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import httpx


async def put_request(
    client: httpx.AsyncClient,
    url: str,
    payload: dict | None = None,
) -> httpx.Response:
    response = await client.put(url, json=payload)
    response.raise_for_status()

    return response


async def delete_request(client: httpx.AsyncClient, url: str, allow_not_found: bool = False) -> httpx.Response:
    response = await client.delete(url)
    if not (allow_not_found and response.status_code == httpx.codes.NOT_FOUND):
        response.raise_for_status()

    return response
