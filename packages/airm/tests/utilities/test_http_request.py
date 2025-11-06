# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from airm.utilities.http_request import delete_request, put_request


@pytest.mark.asyncio
async def test_create_rabbitmq_resource_success():
    async with httpx.AsyncClient() as client:
        resource_url = "http://test.com/api/"
        payload = {"key": "value"}

        request = httpx.Request("PUT", resource_url, json=payload)
        response = httpx.Response(201, request=request)

        with patch.object(client, "put", new=AsyncMock(return_value=response)) as mock_put:
            response = await put_request(client, resource_url, payload)
            mock_put.assert_called_once_with(resource_url, json=payload)
            assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_rabbitmq_resource_failure():
    async with httpx.AsyncClient() as client:
        resource_url = "http://test.com/api/"
        payload = {"key": "value"}

        request = httpx.Request("PUT", resource_url, json=payload)
        response = httpx.Response(400, request=request)

        with patch.object(client, "put", new=AsyncMock(return_value=response)) as mock_put:
            with pytest.raises(httpx.HTTPStatusError):
                await put_request(client, resource_url, payload)
            mock_put.assert_called_once_with(resource_url, json=payload)


@pytest.mark.asyncio
async def test_delete_request_successful_response():
    async with httpx.AsyncClient() as client:
        resource_url = "http://test.com/api/"
        request = httpx.Request("DELETE", resource_url)
        response = httpx.Response(200, request=request)
        with patch.object(client, "delete", new=AsyncMock(return_value=response)) as mock_delete:
            response = await delete_request(client, resource_url)
            mock_delete.assert_called_once_with(resource_url)
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_request_raises_http_exception_on_error():
    async with httpx.AsyncClient() as client:
        resource_url = "http://test.com/api/"
        request = httpx.Request("DELETE", resource_url)
        response = httpx.Response(404, request=request)
        with patch.object(client, "delete", new=AsyncMock(return_value=response)) as mock_delete:
            with pytest.raises(httpx.HTTPStatusError):
                await delete_request(client, resource_url)
            mock_delete.assert_called_once_with(resource_url)


@pytest.mark.asyncio
async def test_delete_request_raises_http_exception_allow_not_found_on_error():
    async with httpx.AsyncClient() as client:
        resource_url = "http://test.com/api/"
        request = httpx.Request("DELETE", resource_url)
        response = httpx.Response(httpx.codes.NOT_FOUND, request=request)
        with patch.object(client, "delete", new=AsyncMock(return_value=response)) as mock_delete:
            await delete_request(client, resource_url, allow_not_found=True)
            mock_delete.assert_called_once_with(resource_url)
            assert response.status_code == httpx.codes.NOT_FOUND
