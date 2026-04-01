# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clusters.models import Cluster
from app.projects.models import Project
from app.users.models import User
from app.utilities.exceptions import ForbiddenException
from app.utilities.security import (
    Roles,
    auth_token_claimset,
    create_logged_in_user_in_system,
    ensure_platform_administrator,
    ensure_user_can_view_cluster,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    is_user_in_role,
    track_user_activity_from_token,
    validate_and_get_project_from_query,
)


@patch("app.utilities.security.KEYCLOAK_OPENID.decode_token", autospec=True)
def test_auth_token_claimset_valid_token(mock_decode_token):
    mock_decode_token.return_value = {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}
    authorization = "Bearer valid_token"
    result = auth_token_claimset(authorization)
    assert result == {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}


def test_auth_token_claimset_invalid_scheme():
    authorization = "InvalidScheme token"
    with pytest.raises(HTTPException) as exc_info:
        auth_token_claimset(authorization)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        exc_info.value.detail
        == "Validation of token failed: 401: Invalid token scheme. Please include Bearer in Authorization header."
    )


@patch("app.utilities.security.KEYCLOAK_OPENID.decode_token", autospec=True)
def test_auth_token_claimset_invalid_token(mock_decode_token):
    mock_decode_token.side_effect = Exception("Invalid token")
    authorization = "Bearer invalid_token"
    with pytest.raises(HTTPException) as exc_info:
        auth_token_claimset(authorization)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Validation of token failed: Invalid token"


def test_ensure_platform_administrator_valid_role():
    claimset = {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}
    ensure_platform_administrator(claimset)


def test_ensure_platform_administrator_missing_role():
    claimset = {"realm_access": {"roles": []}}
    with pytest.raises(HTTPException) as exc_info:
        ensure_platform_administrator(claimset)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Missing required role: Platform Administrator"


def test_is_user_in_role():
    claimset = {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}
    assert is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR)


def test_get_user_email_retrieves_user_from_token():
    claimset = {"email": "test_user@email.com"}
    result = get_user_email(claimset)
    assert result == "test_user@email.com"


def test_get_user_email_raises_exception_if_no_user_name_in_token():
    claimset = {}
    with pytest.raises(HTTPException) as exc_info:
        get_user_email(claimset)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "No user email in token"


@pytest.mark.asyncio
async def test_creates_user_if_not_exists() -> None:
    claimset = {"email": "test@example.com", "sub": "user-id"}
    session = MagicMock()
    kc_admin = MagicMock()
    with (
        patch("app.utilities.security.get_user_by_email", return_value=None),
        patch("app.utilities.security.get_keycloak_user", return_value={"id": "user-id"}),
        patch("app.utilities.security.create_user") as mock_create_user,
    ):
        await create_logged_in_user_in_system(kc_admin, claimset, session)
    mock_create_user.assert_called_once_with(session, "test@example.com", "user-id", "federated")


@pytest.mark.asyncio
async def test_does_nothing_if_user_exists() -> None:
    claimset = {"email": "test@example.com", "sub": "user-id"}
    session = MagicMock()
    kc_admin = MagicMock()
    user = User(email="user1@test.com", keycloak_user_id="keycloak_id")

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.create_user") as mock_create_user,
    ):
        await create_logged_in_user_in_system(kc_admin, claimset, session)

    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_updates_last_active_timestamp_if_not_set() -> None:
    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "iat": 1234567890,
    }
    session = MagicMock()
    user = User(email="user1@test.com", keycloak_user_id="keycloak_id", last_active_at=None)

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await track_user_activity_from_token(claimset, session)

    iat_value: Any = claimset.get("iat", 0)
    mock_update_last_active_at.assert_called_once_with(session, user, datetime.fromtimestamp(float(iat_value), tz=UTC))


@pytest.mark.asyncio
async def test_updates_last_active_timestamp_if_outdated() -> None:
    iat_unix = 1609459200  # 2021-01-01T00:00:00Z

    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "iat": iat_unix,
    }
    session = MagicMock()
    user = User(email="user1@test.com", keycloak_user_id="keycloak_id", last_active_at=datetime(2020, 1, 1, tzinfo=UTC))

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await track_user_activity_from_token(claimset, session)

    iat_value: Any = claimset.get("iat", 0)
    mock_update_last_active_at.assert_called_once_with(session, user, datetime.fromtimestamp(float(iat_value), tz=UTC))


@pytest.mark.asyncio
async def test_does_not_update_newer_last_active_timestamp() -> None:
    iat_unix = 1546300800  # 2019-01-01T00:00:00Z

    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "iat": iat_unix,
    }
    session = MagicMock()
    user = User(email="user1@test.com", keycloak_user_id="keycloak_id", last_active_at=datetime(2020, 1, 1, tzinfo=UTC))

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.create_user") as mock_create_user,
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await track_user_activity_from_token(claimset, session)

    mock_create_user.assert_not_called()
    mock_update_last_active_at.assert_not_called()


@pytest.mark.asyncio
async def test_does_nothing_if_no_email() -> None:
    claimset = {"sub": "user-id", "iat": 1234567890}
    session = MagicMock()
    kc_admin = MagicMock()

    with patch("app.utilities.security.create_user", autospec=True) as mock_create_user:
        await create_logged_in_user_in_system(kc_admin, claimset, session)

    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_does_nothing_if_keycloak_user_not_found() -> None:
    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "iat": 1234567890,
    }
    session = MagicMock()
    kc_admin = MagicMock()
    with (
        patch("app.utilities.security.get_user_by_email", return_value=None),
        patch("app.utilities.security.get_keycloak_user", return_value=None),
        patch("app.utilities.security.create_user") as mock_create_user,
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await create_logged_in_user_in_system(kc_admin, claimset, session)
    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query() -> None:
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="test-project", cluster_id=uuid.uuid4())
    projects = [project]

    result = await validate_and_get_project_from_query(projects, project_id)
    assert result == project


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_fails_if_no_membership() -> None:
    project_id = uuid.uuid4()
    other_project = Project(id=uuid.uuid4(), name="other-project", cluster_id=uuid.uuid4())
    projects = [other_project]  # Project not in list

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_get_project_from_query(projects, project_id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "User is not a member of the project"


@pytest.mark.asyncio
async def test_get_user_fails_if_no_user() -> None:
    session = MagicMock()
    with pytest.raises(HTTPException) as exc_info, patch("app.utilities.security.get_user_by_email", return_value=None):
        await get_user("user1@test.com", session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "User not found in the system"


@pytest.mark.asyncio
async def test_get_user_succeeds() -> None:
    session = MagicMock()
    user = User(email="user1@test.com", keycloak_user_id="keycloak_id")
    with patch("app.utilities.security.get_user_by_email", return_value=user, autospec=True):
        assert await get_user("user1@test.com", session) is not None


@pytest.mark.asyncio
async def test_get_projects_accessible_to_user_with_valid_groups() -> None:
    """Test that user gets projects based on Keycloak group membership."""
    # User is member of these Keycloak group names
    claimset = {
        "groups": ["ProjectAlpha", "ProjectBeta", "SomeOtherGroup"],
    }
    session = MagicMock()

    # Mock projects that have matching names
    project1 = Project(id=uuid.uuid4(), name="ProjectAlpha")
    project2 = Project(id=uuid.uuid4(), name="ProjectBeta")
    with (
        patch("app.utilities.security.get_projects_by_names", return_value=[project1, project2]),
    ):
        result = await get_projects_accessible_to_user(claimset, session)

    assert len(result) == 2
    assert project1 in result
    assert project2 in result


@pytest.mark.asyncio
async def test_get_projects_accessible_to_user_no_groups() -> None:
    """Test that no projects are returned when user has no groups."""
    claimset: dict = {
        "groups": [],
    }
    session = MagicMock()

    result = await get_projects_accessible_to_user(claimset, session)

    assert result == []


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_success() -> None:
    """Test that validate_and_get_project_from_query returns project when user has access."""
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="Test Project")
    projects = [project]

    result = await validate_and_get_project_from_query(projects, project_id)

    assert result == project


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_access_denied() -> None:
    """Test that validate_and_get_project_from_query raises 403 when user has no access."""
    project_id = uuid.uuid4()
    other_project = Project(id=uuid.uuid4(), name="Other Project")
    projects = [other_project]

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_get_project_from_query(projects, project_id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "User is not a member of the project"


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_empty_projects() -> None:
    """Test that validate_and_get_project_from_query raises 403 when user has no projects."""
    project_id = uuid.uuid4()
    projects: list[Project] = []

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_get_project_from_query(projects, project_id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "User is not a member of the project"


@pytest.mark.asyncio
async def test_ensure_user_can_view_cluster_as_admin() -> None:
    """Test that platform admins can view any cluster."""
    cluster_id = uuid.uuid4()
    claimset: dict = {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}
    session = AsyncMock(spec=AsyncSession)

    mock_cluster = MagicMock(spec=Cluster)
    mock_cluster.id = cluster_id

    with patch("app.utilities.security.get_cluster_by_id", return_value=mock_cluster):
        await ensure_user_can_view_cluster(cluster_id, claimset, session)


@pytest.mark.asyncio
async def test_ensure_user_can_view_cluster_with_project_access() -> None:
    """Test that non-admin users can view clusters they have project access to."""
    cluster_id = uuid.uuid4()
    claimset: dict = {"realm_access": {"roles": []}}
    session = AsyncMock(spec=AsyncSession)

    mock_cluster = MagicMock(spec=Cluster)
    mock_cluster.id = cluster_id

    mock_project = MagicMock()
    mock_project.cluster_id = cluster_id

    with (
        patch("app.utilities.security.get_cluster_by_id", return_value=mock_cluster),
        patch("app.utilities.security.get_projects_accessible_to_user", return_value=[mock_project]),
    ):
        await ensure_user_can_view_cluster(cluster_id, claimset, session)


@pytest.mark.asyncio
async def test_ensure_user_can_view_cluster_no_access() -> None:
    """Test that non-admin users without project access get forbidden error."""
    cluster_id = uuid.uuid4()
    claimset: dict = {"realm_access": {"roles": []}}  # Not an admin
    session = AsyncMock(spec=AsyncSession)

    mock_cluster = MagicMock(spec=Cluster)
    mock_cluster.id = cluster_id
    with (
        patch("app.utilities.security.get_cluster_by_id", return_value=mock_cluster),
        patch("app.utilities.security.get_projects_accessible_to_user", return_value=[]),
    ):
        with pytest.raises(ForbiddenException) as exc_info:
            await ensure_user_can_view_cluster(cluster_id, claimset, session)

        assert "not accessible" in str(exc_info.value)
