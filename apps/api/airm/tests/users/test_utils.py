# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.organizations.schemas import OrganizationResponse
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.users.models import User
from app.users.schemas import InviteUser, UserResponse, UserWithProjects
from app.users.utils import (
    create_user_in_keycloak,
    is_keycloak_user_active,
    is_keycloak_user_inactive,
    merge_invited_user_details,
    merge_user_details,
    merge_user_details_with_projects,
)
from app.utilities.exceptions import ConflictException, PreconditionNotMetException
from app.utilities.security import Roles


def test_merge_user_details():
    keycloak_user = {"id": "398b1744-97dd-48f1-85cc-73f76caf98c0", "firstName": "John", "lastName": "Doe"}
    user_id = uuid.UUID("398b1744-97dd-48f1-85cc-73f76caf98c0")
    user = User(
        id=user_id,
        keycloak_user_id=keycloak_user["id"],
        email="test@test.com",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    platform_admins = {keycloak_user["id"]}

    ret = merge_user_details(keycloak_user, user, platform_admins)
    assert ret.first_name == "John"
    assert ret.last_name == "Doe"
    assert ret.email == "test@test.com"
    assert ret.id == user_id
    assert ret.role == Roles.PLATFORM_ADMINISTRATOR.value


def test_merge_user_details_with_projects_platform_admin():
    """Test merging user details with projects for a platform admin."""
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    keycloak_user = {
        "id": "kc-12345",
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
    }
    user = User(
        id=user_id,
        email="jane.doe@example.com",
        keycloak_user_id="kc-12345",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-12345"}

    projects = [
        Project(
            id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
            name="project1",
            description="First project",
            status=ProjectStatus.READY,
            cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_by="admin@example.com",
            updated_by="admin@example.com",
        ),
        Project(
            id=uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b"),
            name="project2",
            description="Second project",
            status=ProjectStatus.READY,
            cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_by="admin@example.com",
            updated_by="admin@example.com",
        ),
    ]

    result = merge_user_details_with_projects(keycloak_user, user, platform_admins, projects)

    assert isinstance(result, UserWithProjects)
    assert result.id == user_id
    assert result.email == "jane.doe@example.com"
    assert result.first_name == "Jane"
    assert result.last_name == "Doe"
    assert result.created_at == datetime(2025, 1, 1, tzinfo=UTC)
    assert result.role == Roles.PLATFORM_ADMINISTRATOR.value
    assert len(result.projects) == 2
    assert result.projects[0].name == "project1"
    assert result.projects[1].name == "project2"
    assert result.projects[0].description == "First project"
    assert result.projects[1].description == "Second project"


def test_merge_user_details_with_projects_team_member():
    """Test merging user details with projects for a team member."""
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    keycloak_user = {
        "id": "kc-67890",
        "firstName": "John",
        "lastName": "Smith",
        "email": "john.smith@example.com",
    }
    user = User(
        id=user_id,
        email="john.smith@example.com",
        keycloak_user_id="kc-67890",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-12345"}

    projects = [
        Project(
            id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
            name="projecta",
            description="projecta",
            status=ProjectStatus.READY,
            cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_by="admin@example.com",
            updated_by="admin@example.com",
        ),
    ]

    result = merge_user_details_with_projects(keycloak_user, user, platform_admins, projects)

    assert isinstance(result, UserWithProjects)
    assert result.id == user_id
    assert result.email == "john.smith@example.com"
    assert result.first_name == "John"
    assert result.last_name == "Smith"
    assert result.created_at == datetime(2025, 1, 1, tzinfo=UTC)
    assert result.role == Roles.TEAM_MEMBER.value
    assert len(result.projects) == 1
    assert result.projects[0].name == "projecta"


def test_merge_user_details_with_projects_no_projects():
    """Test merging user details with no projects."""
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    keycloak_user = {
        "id": "kc-12345",
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
    }
    user = User(
        id=user_id,
        email="jane.doe@example.com",
        keycloak_user_id="kc-12345",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-12345"}

    result1 = merge_user_details_with_projects(keycloak_user, user, platform_admins, None)
    result2 = merge_user_details_with_projects(keycloak_user, user, platform_admins, [])

    assert isinstance(result1, UserWithProjects)
    assert len(result1.projects) == 0

    assert isinstance(result2, UserWithProjects)
    assert len(result2.projects) == 0


@patch("app.users.utils.merge_user_details")
def test_merge_user_details_with_projects_calls_merge_user_details(mock_merge_user_details):
    """Test that merge_user_details_with_projects calls merge_user_details."""
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    user = User(
        id=user_id,
        email="test@example.com",
        keycloak_user_id="kc-test",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    keycloak_user = {"id": "kc-test", "firstName": "Test", "lastName": "User"}
    platform_admins = {"kc-admin"}

    mock_merge_user_details.return_value = UserResponse(
        id=user_id,
        email=user.email,
        first_name="Test",
        last_name="User",
        role=Roles.TEAM_MEMBER.value,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )

    merge_user_details_with_projects(keycloak_user, user, platform_admins, [])

    mock_merge_user_details.assert_called_once_with(keycloak_user, user, platform_admins)


def test_merge_invited_user_details_platform_admin():
    """Test merging invited user details for a platform admin."""
    user = User(
        id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
        email="invited.admin@example.com",
        keycloak_user_id="kc-admin-123",
        invited_at=datetime(2025, 2, 1, tzinfo=UTC),
        invited_by="super@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="super@example.com",
        updated_by="super@example.com",
    )
    platform_admins = {"kc-admin-123"}

    result = merge_invited_user_details(user, platform_admins)

    assert result.id == user.id
    assert result.email == "invited.admin@example.com"
    assert result.invited_at == datetime(2025, 2, 1, tzinfo=UTC)
    assert result.invited_by == "super@example.com"
    assert result.role == Roles.PLATFORM_ADMINISTRATOR.value
    assert result.created_at == datetime(2025, 1, 1, tzinfo=UTC)
    assert result.updated_at == datetime(2025, 1, 1, tzinfo=UTC)


def test_merge_invited_user_details_team_member():
    """Test merging invited user details for a team member."""
    user = User(
        id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
        email="invited.member@example.com",
        keycloak_user_id="kc-member-456",
        invited_at=datetime(2025, 3, 15, tzinfo=UTC),
        invited_by="admin@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-other-admin"}

    result = merge_invited_user_details(user, platform_admins)

    assert result.id == user.id
    assert result.email == "invited.member@example.com"
    assert result.invited_at == datetime(2025, 3, 15, tzinfo=UTC)
    assert result.invited_by == "admin@example.com"
    assert result.role == Roles.TEAM_MEMBER.value


def test_is_keycloak_user_active_with_complete_profile():
    """Test is_keycloak_user_active returns True when firstName and lastName are present."""

    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "firstName": "John",
        "lastName": "Doe",
    }

    assert is_keycloak_user_active(keycloak_user) is True


def test_is_keycloak_user_active_missing_first_name():
    """Test is_keycloak_user_active returns False when firstName is missing."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "lastName": "Doe",
    }

    assert is_keycloak_user_active(keycloak_user) is False


def test_is_keycloak_user_active_missing_last_name():
    """Test is_keycloak_user_active returns False when lastName is missing."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "firstName": "John",
    }

    assert is_keycloak_user_active(keycloak_user) is False


def test_is_keycloak_user_active_missing_both_names():
    """Test is_keycloak_user_active returns False when both names are missing."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
    }

    assert is_keycloak_user_active(keycloak_user) is False


def test_is_keycloak_user_active_empty_first_name():
    """Test is_keycloak_user_active returns True even with empty string firstName (key exists)."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "firstName": "",
        "lastName": "Doe",
    }

    # Function only checks for key presence, not value
    assert is_keycloak_user_active(keycloak_user) is True


def test_is_keycloak_user_inactive_with_complete_profile():
    """Test is_keycloak_user_inactive returns False when firstName and lastName are present."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "firstName": "John",
        "lastName": "Doe",
    }

    assert is_keycloak_user_inactive(keycloak_user) is False


def test_is_keycloak_user_inactive_missing_names():
    """Test is_keycloak_user_inactive returns True when names are missing."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
    }

    assert is_keycloak_user_inactive(keycloak_user) is True


def test_is_keycloak_user_inactive_missing_first_name():
    """Test is_keycloak_user_inactive returns True when firstName is missing."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "lastName": "Doe",
    }

    assert is_keycloak_user_inactive(keycloak_user) is True


def test_is_keycloak_user_inactive_missing_last_name():
    """Test is_keycloak_user_inactive returns True when lastName is missing."""
    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "firstName": "John",
    }

    assert is_keycloak_user_inactive(keycloak_user) is True


@pytest.mark.asyncio
@patch("app.users.utils.set_temporary_password")
@patch("app.users.utils.create_user")
@patch("app.users.utils.get_realm_details")
async def test_create_user_in_keycloak_no_idp_no_smtp_with_temp_password(
    mock_realm_details, mock_create_user, mock_set_temp_password
):
    """Test creating user in Keycloak when org has no IDP and no SMTP, with temp password."""
    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_realm_details.return_value = OrganizationResponse(
        idp_linked=False,
        smtp_enabled=False,
    )

    mock_create_user.return_value = "new-user-kc-id"

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password="SecurePass123!")

    result = await create_user_in_keycloak(kc_admin, user_in)

    # Assert
    assert result == "new-user-kc-id"
    mock_create_user.assert_called_once()
    call_args = mock_create_user.call_args[1]
    assert call_args["user_data"]["username"] == "newuser@example.com"
    assert call_args["user_data"]["email"] == "newuser@example.com"
    assert call_args["user_data"]["emailVerified"] is True
    assert call_args["user_data"]["enabled"] is True
    assert "UPDATE_PASSWORD" in call_args["user_data"]["requiredActions"]
    assert "UPDATE_PROFILE" in call_args["user_data"]["requiredActions"]
    mock_set_temp_password.assert_called_once_with(
        kc_admin=kc_admin, user_id="new-user-kc-id", temp_password="SecurePass123!"
    )


@pytest.mark.asyncio
@patch("app.users.utils.get_realm_details")
async def test_create_user_in_keycloak_no_idp_no_smtp_no_temp_password(get_realm_details):
    """Test creating user in Keycloak when org has no IDP and no SMTP, without temp password."""
    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    get_realm_details.return_value = OrganizationResponse(
        idp_linked=False,
        smtp_enabled=False,
    )

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    with pytest.raises(ConflictException, match="Temporary password is required for user creation"):
        await create_user_in_keycloak(kc_admin, user_in)


@pytest.mark.asyncio
@patch("app.users.utils.send_verify_email")
@patch("app.users.utils.create_user")
@patch("app.users.utils.get_realm_details")
async def test_create_user_in_keycloak_with_smtp_enabled(mock_realm_details, mock_create_user, mock_send_verify_email):
    """Test creating user in Keycloak when SMTP is enabled."""
    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_realm_details.return_value = OrganizationResponse(
        idp_linked=False,
        smtp_enabled=True,
    )
    mock_create_user.return_value = "new-user-kc-id"

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    result = await create_user_in_keycloak(kc_admin, user_in)

    # Assert
    assert result == "new-user-kc-id"
    mock_create_user.assert_called_once()
    call_args = mock_create_user.call_args[1]
    assert call_args["user_data"]["username"] == "newuser@example.com"
    assert call_args["user_data"]["email"] == "newuser@example.com"
    assert call_args["user_data"]["emailVerified"] is False
    assert call_args["user_data"]["enabled"] is True
    assert "VERIFY_EMAIL" in call_args["user_data"]["requiredActions"]
    assert "UPDATE_PASSWORD" in call_args["user_data"]["requiredActions"]
    assert "UPDATE_PROFILE" in call_args["user_data"]["requiredActions"]
    mock_send_verify_email.assert_called_once()


@pytest.mark.asyncio
@patch("app.users.utils.send_verify_email")
@patch("app.users.utils.create_user")
@patch("app.users.utils.get_realm_details")
async def test_create_user_in_keycloak_with_idp_linked(mock_realm_details, mock_create_user, mock_send_verify_email):
    """Test creating user in Keycloak when IDP is linked and SMTP is enabled."""
    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_realm_details.return_value = OrganizationResponse(
        idp_linked=True,
        smtp_enabled=True,
    )
    mock_create_user.return_value = "new-user-kc-id"

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    result = await create_user_in_keycloak(kc_admin, user_in)

    # Assert - should use SMTP flow even when IDP is linked
    assert result == "new-user-kc-id"
    mock_send_verify_email.assert_called_once()


@pytest.mark.asyncio
@patch("app.users.utils.get_realm_details")
async def test_create_user_in_keycloak_org_not_configured(mock_realm_details):
    """Test creating user in Keycloak when organization is not properly configured."""

    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_realm_details.return_value = OrganizationResponse(
        idp_linked=True,
        smtp_enabled=False,
    )

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    with pytest.raises(PreconditionNotMetException, match="Organization is not configured for user creation"):
        await create_user_in_keycloak(kc_admin, user_in)
