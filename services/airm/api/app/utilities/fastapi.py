# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
FastAPI-specific utilities and exception handlers.

This module contains exception handlers and other utilities for the FastAPI framework.
"""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError

from .exceptions import (
    BaseAirmException,
    ConflictException,
    DeletionConflictException,
    ExternalServiceError,
    ForbiddenException,
    InconsistentStateException,
    NotFoundException,
    PreconditionNotMetException,
    UnhealthyException,
    UploadFailedException,
    ValidationException,
)


def not_found_exception_handler(request: Request, exc: NotFoundException) -> JSONResponse:
    """
    Handler for NotFoundException.
    Maps to 404 Not Found.
    """
    logger.debug(f"Resource not found in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.NOT_FOUND,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def conflict_exception_handler(request: Request, exc: ConflictException) -> JSONResponse:
    """
    Handler for ConflictException.
    Maps to 409 Conflict.
    """
    logger.debug(f"Conflict in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.CONFLICT,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Handler for IntegrityError.
    Maps to 409 Conflict.
    """
    logger.debug(f"IntegrityError in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.CONFLICT,
        content={
            "detail": "The requested operation failed due to constraints on the data.",
            "additional_info": str(exc.orig) if exc.orig else "No additional information available.",
        },
    )


def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """
    Handler for ValidationException.
    Maps to 400 Bad Request.
    """
    logger.debug(f"Validation error in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def forbidden_exception_handler(request: Request, exc: ForbiddenException) -> JSONResponse:
    """
    Handler for ForbiddenException.
    Maps to 403 Forbidden.
    """
    logger.debug(f"Access forbidden in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.FORBIDDEN,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def unhealthy_exception_handler(request: Request, exc: UnhealthyException) -> JSONResponse:
    """
    Handler for UnhealthyException.
    Maps to 503 Service Unavailable.
    """
    logger.warning(f"Resource unhealthy in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def precondition_not_met_exception_handler(request: Request, exc: PreconditionNotMetException) -> JSONResponse:
    """
    Handler for PreconditionNotMetException.
    Maps to 428 Precondition Required
    """
    logger.debug(f"Resource not ready in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.PRECONDITION_REQUIRED,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def external_service_error_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
    """
    Handler for ExternalServiceError.
    Maps to 502 Bad Gateway.
    """
    logger.error(f"External service error in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.BAD_GATEWAY,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def exception_group_handler(request: Request, exc: ExceptionGroup) -> JSONResponse:
    """
    Handler for ExceptionGroup - typically used for batch operations.
    Maps to appropriate HTTP status based on the types of exceptions in the group.
    """
    logger.warning(f"Exception group in request {request.url}: {str(exc)}")

    # Extract specific error details from the ExceptionGroup
    not_found_errors = []
    conflict_errors = []
    other_errors = []

    for exception in exc.exceptions:
        if isinstance(exception, NotFoundException):
            not_found_errors.append(str(exception))
        elif isinstance(exception, DeletionConflictException):
            conflict_errors.append(str(exception))
        else:
            other_errors.append(str(exception))

    # Determine the most appropriate HTTP status code and format message
    if not_found_errors and not conflict_errors and not other_errors:
        # All errors are 404 - models not found
        return JSONResponse(status_code=HTTPStatus.NOT_FOUND, content={"detail": "; ".join(not_found_errors)})
    elif conflict_errors and not not_found_errors and not other_errors:
        # All errors are 409 - deletion conflicts
        return JSONResponse(status_code=HTTPStatus.CONFLICT, content={"detail": "; ".join(conflict_errors)})
    else:
        # Mixed errors - provide detailed breakdown
        all_errors = not_found_errors + conflict_errors + other_errors
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content={"detail": f"Some models could not be deleted: {'; '.join(all_errors)}"},
        )


def inconsistent_state_exception_handler(request: Request, exc: InconsistentStateException) -> JSONResponse:
    """
    Handler for InconsistentStateException.
    Maps to 500 Internal Server Error.
    """
    logger.error(f"Inconsistent state in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def upload_failed_exception_handler(request: Request, exc: UploadFailedException) -> JSONResponse:
    """
    Handler for UploadFailedException.
    Maps to 500 Internal Server Error.
    """
    logger.error(f"Upload failed in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def base_airm_exception_handler(request: Request, exc: BaseAirmException) -> JSONResponse:
    """
    Handler for BaseAirmException.
    This handles any custom exception that doesn't have a more specific handler.
    Maps to 500 Internal Server Error by default, but can be overridden by subclasses.
    """
    logger.error(f"Application exception in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,  # Default status code
        content={
            "detail": exc.message,
            **({"additional_info": exc.detail} if exc.detail else {}),
        },
    )


def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.
    Logs the exception and returns a 500 Internal Server Error.
    """
    logger.exception(f"Unhandled exception in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Handler for ValueError exceptions.
    Converts them to 400 Bad Request responses.
    """
    logger.error(f"ValueError in request {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={"detail": str(exc)},
    )
