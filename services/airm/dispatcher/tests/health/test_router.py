# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from airm.health.schemas import HealthCheck
from app import app  # type: ignore


@pytest.mark.asyncio
async def test_healthcheck_healthy():
    with patch("app.health.router.all_watchers_healthy", new=AsyncMock(return_value=True)):
        with TestClient(app) as client:
            response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == HealthCheck(status="OK").dict()


@pytest.mark.asyncio
async def test_healthcheck_unhealthy():
    with patch("app.health.router.all_watchers_healthy", new=AsyncMock(return_value=False)):
        with TestClient(app) as client:
            response = client.get("/v1/health")

    assert response.status_code == 500
    assert response.json() == {"detail": "One or more watchers are unhealthy."}
