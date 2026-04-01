# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from fastapi import APIRouter, status

from .schemas import HealthCheck

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
def get_health() -> HealthCheck:
    """
    Endpoint to perform a healthcheck on.
    Returns:
        HealthCheck: Returns a JSON response with the health status
    """
    return HealthCheck(status="OK")
