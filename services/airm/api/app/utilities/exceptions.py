# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Domain-specific exceptions for the AIRM API.

This module defines exceptions that represent various domain-specific error conditions
that can occur in the application. These exceptions should be used in the service layer
instead of raising HTTP exceptions directly. The router layer is responsible for
translating these exceptions into appropriate HTTP responses.
"""

from typing import Any


class BaseAirmException(Exception):
    """Base exception for all AIRM domain exceptions."""

    def __init__(self, message: str, detail: str | dict[str, Any] | list[dict[str, Any]] | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundException(BaseAirmException):
    """Exception raised when a requested resource is not found."""

    pass


class ConflictException(BaseAirmException):
    """Exception raised when a resource cannot be created or updated due to a conflict."""

    pass


class DeletionConflictException(ConflictException):
    """Exception raised when an entity cannot be deleted due to existing dependencies or business rules."""

    pass


class ValidationException(BaseAirmException):
    """Exception raised when a resource fails validation."""

    pass


class UploadFailedException(BaseAirmException):
    """Exception raised when an upload operation fails."""

    pass


class ForbiddenException(BaseAirmException):
    """Exception raised when access to a resource is forbidden."""

    pass


class UnhealthyException(BaseAirmException):
    """Exception raised when a resource is in an unhealthy state."""

    pass


class NotReadyException(BaseAirmException):
    """Exception raised when a resource is not ready for the requested operation."""

    pass


class ExternalServiceError(BaseAirmException):
    """Exception raised when an external service (S3, Keycloak, RabbitMQ, etc.) fails."""

    pass


class InconsistentStateException(BaseAirmException):
    """Exception raised when the system is in an inconsistent state."""

    pass
