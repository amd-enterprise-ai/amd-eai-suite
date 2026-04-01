# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Dependency override utilities and patterns for testing.

This module provides:
1. Utilities for managing FastAPI dependency overrides in tests
2. Reusable dependency override patterns for common test scenarios

Usage:
    from tests.dependency_overrides import override_dependencies, ADMIN_OVERRIDES

    @override_dependencies(ADMIN_OVERRIDES)
    async def test_admin_endpoint():
        # Test runs with admin dependencies
        pass
"""

import asyncio
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.users.models import User
from app.utilities.database import get_session
from app.utilities.keycloak_admin import get_kc_admin
from app.utilities.security import (
    BearerToken,
    auth_token_claimset,
    ensure_platform_administrator,
    ensure_user_can_view_cluster,
    ensure_user_can_view_project,
    ensure_user_can_view_workload,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    track_user_activity_from_token,
)


@contextmanager
def runtime_dependency_overrides(overrides: dict[Callable[..., Any], Callable[..., Any]]) -> Generator[None]:
    """Context manager for temporarily applying dependency overrides.

    Args:
        overrides: Dictionary mapping dependency functions to their override implementations.

    Yields:
        None

    Example:
        with runtime_dependency_overrides({get_session: lambda: mock_session}):
            # Test code that uses the overridden dependency
            pass
    """
    old_overrides = app.dependency_overrides.copy()
    # Preserve global overrides by not clearing them
    app.dependency_overrides.update(overrides)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)


def override_dependencies(overrides: dict[Callable[..., Any], Callable[..., Any]]) -> Callable:
    """Decorator to temporarily override FastAPI dependencies for a test function.

    Args:
        overrides: Dictionary mapping dependency functions to their override implementations.

    Returns:
        Decorated function with dependency overrides applied during execution.

    Example:
        @override_dependencies(ADMIN_OVERRIDES)
        async def test_admin_endpoint():
            # Test runs with admin dependencies
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with runtime_dependency_overrides(overrides):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with runtime_dependency_overrides(overrides):
                    return func(*args, **kwargs)

            return wrapper

    return decorator


# =============================================================================
# Reusable Override Patterns
# =============================================================================

# Base building blocks
MINIMAL_SESSION_OVERRIDES = {
    get_session: lambda: AsyncMock(spec=AsyncSession),
}

USER_EMAIL_OVERRIDES = {
    get_user_email: lambda: "test@example.com",
}

USER_EMAIL_WITH_SESSION_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **USER_EMAIL_OVERRIDES,
}

GET_USER_OVERRIDES = {
    get_user: lambda: MagicMock(spec_set=User),
}

# Authorization building blocks
ADMIN_AUTH_OVERRIDES = {
    ensure_platform_administrator: lambda: None,
}

ADMIN_EMAIL_OVERRIDES = {
    get_user_email: lambda: "admin@example.com",
}

ADMIN_FORBIDDEN_OVERRIDES = {
    ensure_platform_administrator: lambda: MagicMock(
        side_effect=HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    )(),
}

AUTH_TOKEN_CLAIMSET_OVERRIDES = {
    auth_token_claimset: lambda: MagicMock(spec_set=dict),
}

ADMIN_CLAIMSET_OVERRIDES = {
    auth_token_claimset: lambda: {"realm_access": {"roles": ["Platform Administrator"]}},
}

USER_PROJECT_VIEW_PERMISSION_OVERRIDES = {
    ensure_user_can_view_project: lambda: MagicMock(),
}

USER_PROJECT_VIEW_FORBIDDEN_OVERRIDES = {
    ensure_user_can_view_project: lambda: MagicMock(side_effect=HTTPException(status_code=status.HTTP_403_FORBIDDEN))(),
}

USER_CLUSTER_VIEW_PERMISSION_OVERRIDES = {
    ensure_user_can_view_cluster: lambda: MagicMock(),
}

USER_CLUSTER_VIEW_FORBIDDEN_OVERRIDES = {
    ensure_user_can_view_cluster: lambda: MagicMock(side_effect=HTTPException(status_code=status.HTTP_403_FORBIDDEN))(),
}

USER_WORKLOAD_VIEW_PERMISSION_OVERRIDES = {
    ensure_user_can_view_workload: lambda: None,
}

# Composed admin patterns
ADMIN_SESSION_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **ADMIN_AUTH_OVERRIDES,
}

ADMIN_OVERRIDES = {
    **USER_EMAIL_WITH_SESSION_OVERRIDES,
    **ADMIN_AUTH_OVERRIDES,
}

ADMIN_USER_OVERRIDES = {
    **ADMIN_SESSION_OVERRIDES,
    **GET_USER_OVERRIDES,
}

ADMIN_SESSION_FORBIDDEN_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **ADMIN_FORBIDDEN_OVERRIDES,
}

ADMIN_EMAIL_WITH_SESSION_OVERRIDES = {
    **ADMIN_SESSION_OVERRIDES,
    **ADMIN_EMAIL_OVERRIDES,
}

# Composed user view patterns
USER_PROJECT_SESSION_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **USER_PROJECT_VIEW_PERMISSION_OVERRIDES,
}

USER_PROJECT_VIEW_OVERRIDES = {
    **USER_PROJECT_SESSION_OVERRIDES,
    **GET_USER_OVERRIDES,
}

USER_PROJECT_VIEW_AUTH_OVERRIDES = {
    **USER_PROJECT_SESSION_OVERRIDES,
    **AUTH_TOKEN_CLAIMSET_OVERRIDES,
}


USER_CLUSTER_SESSION_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **USER_CLUSTER_VIEW_PERMISSION_OVERRIDES,
}

# Keycloak admin patterns
ADMIN_EMAIL_WITH_KC_ADMIN_OVERRIDES = {
    **ADMIN_EMAIL_WITH_SESSION_OVERRIDES,
    get_kc_admin: lambda: MagicMock(),
}

# Unauthorized/authentication failure patterns
USER_EMAIL_UNAUTHORIZED_OVERRIDES = {
    **ADMIN_SESSION_OVERRIDES,
    get_user_email: lambda: MagicMock(
        spec_set=str, side_effect=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    )(),
}

# User tracking patterns
ADMIN_WITH_USER_TRACKING_OVERRIDES = {
    **USER_EMAIL_OVERRIDES,
    **ADMIN_AUTH_OVERRIDES,
    track_user_activity_from_token: lambda: MagicMock(),
}

# User with specific attributes
USER_WITH_KEYCLOAK_ID_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **AUTH_TOKEN_CLAIMSET_OVERRIDES,
    get_user: lambda: User(email="user1@test.com", keycloak_user_id="keycloak_id"),
}

# Admin session with user mock
ADMIN_SESSION_WITH_USER_MOCK_OVERRIDES = {
    **ADMIN_SESSION_OVERRIDES,
    **GET_USER_OVERRIDES,
}

# Project access patterns
SUBMITTABLE_PROJECTS_UNAUTHORIZED_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **AUTH_TOKEN_CLAIMSET_OVERRIDES,
    get_projects_accessible_to_user: lambda: MagicMock(
        spec_set=str, side_effect=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    )(),
}

SUBMITTABLE_PROJECTS_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    get_projects_accessible_to_user: lambda: MagicMock(spec_set=[]),
}

# Workload override patterns
WORKLOAD_SUBMIT_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **USER_EMAIL_OVERRIDES,
    BearerToken: lambda: MagicMock(),
}

WORKLOAD_DELETE_OVERRIDES = {
    **SUBMITTABLE_PROJECTS_OVERRIDES,
    **USER_WITH_KEYCLOAK_ID_OVERRIDES,
}

WORKLOAD_READ_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    **USER_WORKLOAD_VIEW_PERMISSION_OVERRIDES,
}
