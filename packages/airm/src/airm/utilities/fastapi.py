# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger


def value_error_handler(_: Request, exc: ValueError) -> None:
    logger.warning(f"Encountered ValueError: {str(exc)}")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Something went wrong: {str(exc)}"},
    )
