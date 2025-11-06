# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from airm.health.schemas import HealthCheck

from ..kubernetes.watcher_health import all_watchers_healthy, watcher_status_map

router = APIRouter(tags=["Health"])


"""Entrypoint to invoke the FastAPI application service with."""


@router.get(
    "/health",
    operation_id="healthcheck",
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
async def get_health() -> HealthCheck:
    """
    Endpoint to perform a healthcheck.
    Returns:
        HealthCheck or 500 if any watcher is unhealthy.
    """
    if not await all_watchers_healthy():
        now = datetime.now()
        for name, last_attempt in watcher_status_map.items():
            age = now - last_attempt
            if age < timedelta(minutes=5):
                logger.info(f"HEALTHY {name}: last attempted {age.total_seconds() / 60:.2f} minutes ago")
            else:
                logger.error(f"UNHEALTHY {name}: last attempted {age.total_seconds() / 60:.2f} minutes ago")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="One or more watchers are unhealthy."
        )

    return HealthCheck(status="OK")
