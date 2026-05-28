# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""FastAPI exception handlers specific to the AIWB API (Kubernetes client, etc.)."""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from kubernetes.client.exceptions import ApiException
from loguru import logger


def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
    """
    Handler for Kubernetes ApiException.
    Maps Kubernetes API errors to appropriate HTTP status codes.
    """
    status_code = exc.status if hasattr(exc, "status") else HTTPStatus.INTERNAL_SERVER_ERROR

    if status_code == 404:
        logger.debug(f"Kubernetes resource not found in request {request.url}: {exc.reason}")
    elif status_code < 500:
        logger.warning(f"Kubernetes API client error in request {request.url}: {exc.reason}")
    else:
        logger.error(f"Kubernetes API server error in request {request.url}: {exc.reason}")

    body = getattr(exc, "body", None)
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": f"Kubernetes API error: {exc.reason}",
            "additional_info": body,
        },
    )
