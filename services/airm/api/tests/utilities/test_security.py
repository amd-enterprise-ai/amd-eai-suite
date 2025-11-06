# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.organizations.models import Organization
from app.projects.models import Project
from app.users.models import User
from app.utilities.security import (
    Roles,
    __get_organization_id_from_claimset,
    auth_token_claimset,
    create_logged_in_user_in_system,
    ensure_platform_administrator,
    ensure_super_administrator,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    get_user_organization,
    is_user_in_role,
    track_user_activity_from_token,
    validate_and_get_project_from_query,
)


@patch("app.utilities.security.KEYCLOAK_PUBLIC_OPENID.decode_token", autospec=True)
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


@patch("app.utilities.security.KEYCLOAK_PUBLIC_OPENID.decode_token", autospec=True)
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


def test_ensure_super_administrator_valid_role():
    claimset = {"realm_access": {"roles": [Roles.SUPER_ADMINISTRATOR.value]}}
    ensure_super_administrator(claimset)


def test_ensure_super_administrator_missing_role():
    claimset = {"realm_access": {"roles": []}}
    with pytest.raises(HTTPException) as exc_info:
        ensure_super_administrator(claimset)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Missing required role: Super Administrator"


def test_is_user_in_role():
    claimset = {"realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]}}
    assert is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR)
    assert not is_user_in_role(claimset, Roles.SUPER_ADMINISTRATOR)


def test_get_organization_id_from_claimset():
    """Test extracting organization ID from valid claim"""
    claimset = {"organization": {"org_name": {"id": "1cc02d78-f78d-4b6e-98eb-315769a67f52"}}}
    result = __get_organization_id_from_claimset(claimset)
    assert result == "1cc02d78-f78d-4b6e-98eb-315769a67f52"


def test_get_organization_id_from_claimset_missing_or_invalid():
    """Test when organization claim is missing, empty, or invalid"""
    # No organization claim
    assert __get_organization_id_from_claimset({}) is None

    # Empty organization dict
    assert __get_organization_id_from_claimset({"organization": {}}) is None

    # Organization dict without ID
    assert __get_organization_id_from_claimset({"organization": {"org_name": {"name": "Org"}}}) is None

    # Non-dict organization claim
    assert __get_organization_id_from_claimset({"organization": "string"}) is None


@pytest.mark.asyncio
@patch(
    "app.utilities.security.get_organization_by_keycloak_org_id",
    return_value=Organization(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="org-id"
    ),
)
async def test_get_user_organization_returns_organization(_):
    claimset = {"organization": {"org": {"id": "org-id"}}}
    session = MagicMock()
    organization = await get_user_organization(claimset, session)
    assert organization.id == "0aa18e92-002c-45b7-a06e-dcdb0277974c"


@patch(
    "app.utilities.security.get_organization_by_keycloak_org_id",
    return_value=None,
)
@pytest.mark.asyncio
async def test_get_user_organization_raises_404_if_organization_not_found(_):
    claimset = {"organization": {"org": {"id": "org-id"}}}
    session = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_user_organization(claimset, session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Organization not found"


@pytest.mark.asyncio
async def test_get_user_organization_raises_403_if_no_organization_claim():
    claimset = {}
    session = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_user_organization(claimset, session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "No organization claim in token"


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
async def test_creates_user_if_not_exists():
    claimset = {"email": "test@example.com", "sub": "user-id", "organization": {"org_name": {"id": "org-id"}}}
    session = MagicMock()
    kc_admin = MagicMock()
    organization = Organization(id="db_org_id", name="Organization1", keycloak_organization_id="org-id")

    with (
        patch("app.utilities.security.get_user_by_email", return_value=None),
        patch("app.utilities.security.get_organization_by_keycloak_org_id", return_value=organization),
        patch("app.utilities.security.get_keycloak_user", return_value={"id": "user-id"}),
        patch("app.utilities.security.create_user_in_organization") as mock_create_user,
    ):
        await create_logged_in_user_in_system(kc_admin, claimset, session)
    mock_create_user.assert_called_once_with(session, "db_org_id", "test@example.com", "user-id", "federated")


@pytest.mark.asyncio
async def test_does_nothing_if_user_exists():
    claimset = {"email": "test@example.com", "sub": "user-id", "organization": {"org_name": {"id": "org-id"}}}
    session = MagicMock()
    kc_admin = MagicMock()
    user = User(email="user1@test.com", organization_id="org_id", keycloak_user_id="keycloak_id")

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.create_user_in_organization") as mock_create_user,
    ):
        await create_logged_in_user_in_system(kc_admin, claimset, session)

    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_updates_last_active_timestamp_if_not_set():
    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "organization": {"org_name": {"id": "org-id"}},
        "iat": 1234567890,
    }
    session = MagicMock()
    user = User(email="user1@test.com", organization_id="org_id", keycloak_user_id="keycloak_id", last_active_at=None)

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await track_user_activity_from_token(claimset, session)

    mock_update_last_active_at.assert_called_once_with(session, user, datetime.fromtimestamp(claimset["iat"], tz=UTC))


@pytest.mark.asyncio
async def test_updates_last_active_timestamp_if_outdated():
    iat_unix = 1609459200  # 2021-01-01T00:00:00Z

    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "organization": {"org_name": {"id": "org-id"}},
        "iat": iat_unix,
    }
    session = MagicMock()
    user = User(
        email="user1@test.com",
        organization_id="org_id",
        keycloak_user_id="keycloak_id",
        last_active_at=datetime(2020, 1, 1, tzinfo=UTC),
    )

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await track_user_activity_from_token(claimset, session)

    mock_update_last_active_at.assert_called_once_with(session, user, datetime.fromtimestamp(claimset["iat"], tz=UTC))


@pytest.mark.asyncio
async def test_does_not_update_newer_last_active_timestamp():
    iat_unix = 1546300800  # 2019-01-01T00:00:00Z

    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "organization": {"org_name": {"id": "org-id"}},
        "iat": iat_unix,
    }
    session = MagicMock()
    user = User(
        email="user1@test.com",
        organization_id="org_id",
        keycloak_user_id="keycloak_id",
        last_active_at=datetime(2020, 1, 1, tzinfo=UTC),
    )

    with (
        patch("app.utilities.security.get_user_by_email", return_value=user),
        patch("app.utilities.security.create_user_in_organization") as mock_create_user,
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await track_user_activity_from_token(claimset, session)

    mock_create_user.assert_not_called()
    mock_update_last_active_at.assert_not_called()


@pytest.mark.asyncio
async def test_does_nothing_if_no_organization_id():
    claimset = {"email": "test@example.com", "sub": "user-id", "organization": {}, "iat": 1234567890}
    session = MagicMock()
    kc_admin = MagicMock()

    with patch("app.utilities.security.create_user_in_organization", autospec=True) as mock_create_user:
        await create_logged_in_user_in_system(kc_admin, claimset, session)

    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_does_nothing_if_no_email():
    claimset = {"sub": "user-id", "organization": {"org_name": {"id": "org-id"}}, "iat": 1234567890}
    session = MagicMock()
    kc_admin = MagicMock()

    with patch("app.utilities.security.create_user_in_organization", autospec=True) as mock_create_user:
        await create_logged_in_user_in_system(kc_admin, claimset, session)

    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_does_nothing_if_organization_not_found():
    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "organization": {"org_name": {"id": "org-id"}},
        "iat": 1234567890,
    }
    session = MagicMock()
    kc_admin = MagicMock()

    with (
        patch("app.utilities.security.get_user_by_email", return_value=None),
        patch("app.utilities.security.get_organization_by_keycloak_org_id", return_value=None),
        patch("app.utilities.security.get_keycloak_user", return_value={"id": "user-id"}),
        patch("app.utilities.security.create_user_in_organization") as mock_create_user,
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await create_logged_in_user_in_system(kc_admin, claimset, session)
    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_does_nothing_if_keycloak_user_not_found():
    claimset = {
        "email": "test@example.com",
        "sub": "user-id",
        "organization": {"org_name": {"id": "org-id"}},
        "iat": 1234567890,
    }
    session = MagicMock()
    kc_admin = MagicMock()
    organization = Organization(id="org", name="Organization1", keycloak_organization_id="org-id")

    with (
        patch("app.utilities.security.get_user_by_email", return_value=None),
        patch("app.utilities.security.get_organization_by_keycloak_org_id", return_value=organization),
        patch("app.utilities.security.get_keycloak_user", return_value=None),
        patch("app.utilities.security.create_user_in_organization") as mock_create_user,
        patch("app.utilities.security.update_last_active_at") as mock_update_last_active_at,
    ):
        await create_logged_in_user_in_system(kc_admin, claimset, session)
    mock_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query():
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="test-project", cluster_id=uuid.uuid4(), organization_id="org_id")
    projects = [project]

    result = await validate_and_get_project_from_query(projects, project_id)
    assert result == project


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_fails_if_no_membership():
    project_id = uuid.uuid4()
    other_project = Project(id=uuid.uuid4(), name="other-project", cluster_id=uuid.uuid4(), organization_id="org_id")
    projects = [other_project]  # Project not in list

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_get_project_from_query(projects, project_id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "User is not a member of the project"


@pytest.mark.asyncio
async def test_get_user_fails_if_no_user():
    session = MagicMock()
    with pytest.raises(HTTPException) as exc_info, patch("app.utilities.security.get_user_by_email", return_value=None):
        await get_user("user1@test.com", session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "User not found in the system"


@pytest.mark.asyncio
async def test_get_user_succeeds():
    session = MagicMock()
    user = User(email="user1@test.com", organization_id="org_id", keycloak_user_id="keycloak_id")
    with patch("app.utilities.security.get_user_by_email", return_value=user, autospec=True):
        assert await get_user("user1@test.com", session) is not None


@pytest.mark.asyncio
async def test_get_projects_accessible_to_user_with_valid_groups():
    """Test that user gets projects based on Keycloak group membership."""
    # User is member of these Keycloak group names
    claimset = {
        "groups": ["ProjectAlpha", "ProjectBeta", "SomeOtherGroup"],
        "organization": {"TestOrg": {"id": "org-keycloak-id"}},
    }
    session = MagicMock()

    # Mock organization
    organization = Organization(id=uuid.uuid4(), keycloak_organization_id="org-keycloak-id", name="TestOrg")

    # Mock projects that have matching names
    project1 = Project(id=uuid.uuid4(), name="ProjectAlpha", organization_id=organization.id)
    project2 = Project(id=uuid.uuid4(), name="ProjectBeta", organization_id=organization.id)

    with (
        patch("app.utilities.security.get_organization_by_keycloak_org_id", return_value=organization),
        patch("app.utilities.security.get_projects_by_names_in_organization", return_value=[project1, project2]),
    ):
        result = await get_projects_accessible_to_user(claimset, session)

    assert len(result) == 2
    assert project1 in result
    assert project2 in result


@pytest.mark.asyncio
async def test_get_projects_accessible_to_user_no_organization():
    """Test that no projects are returned when organization is not found in token."""
    claimset = {
        "groups": ["ProjectAlpha", "ProjectBeta"],
        "organization": {},
    }
    session = MagicMock()

    result = await get_projects_accessible_to_user(claimset, session)

    assert result == []


@pytest.mark.asyncio
async def test_get_projects_accessible_to_user_no_groups():
    """Test that no projects are returned when user has no groups."""
    claimset = {
        "groups": [],
        "organization": {"TestOrg": {"id": "org-keycloak-id"}},
    }
    session = MagicMock()

    organization = Organization(id=uuid.uuid4(), keycloak_organization_id="org-keycloak-id", name="TestOrg")

    with patch("app.utilities.security.get_organization_by_keycloak_org_id", return_value=organization):
        result = await get_projects_accessible_to_user(claimset, session)

    assert result == []


@pytest.mark.asyncio
async def test_get_projects_accessible_to_user_organization_not_in_db():
    """Test that no projects are returned when organization exists in token but not in database."""
    claimset = {
        "groups": ["ProjectAlpha"],
        "organization": {"TestOrg": {"id": "nonexistent-org"}},
    }
    session = MagicMock()

    with patch("app.utilities.security.get_organization_by_keycloak_org_id", return_value=None):
        result = await get_projects_accessible_to_user(claimset, session)

    assert result == []


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_success():
    """Test that validate_and_get_project_from_query returns project when user has access."""
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="Test Project")
    projects = [project]

    result = await validate_and_get_project_from_query(projects, project_id)

    assert result == project


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_access_denied():
    """Test that validate_and_get_project_from_query raises 403 when user has no access."""
    project_id = uuid.uuid4()
    other_project = Project(id=uuid.uuid4(), name="Other Project")
    projects = [other_project]

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_get_project_from_query(projects, project_id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "User is not a member of the project"


@pytest.mark.asyncio
async def test_validate_and_get_project_from_query_empty_projects():
    """Test that validate_and_get_project_from_query raises 403 when user has no projects."""
    project_id = uuid.uuid4()
    projects = []

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_get_project_from_query(projects, project_id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "User is not a member of the project"
