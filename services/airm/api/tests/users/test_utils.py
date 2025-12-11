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
from app.users.models import User as UserModel
from app.users.schemas import InvitedUserWithProjects, InviteUser, UserWithProjects
from app.users.utils import (
    check_valid_email_domain,
    create_user_in_keycloak,
    merge_invited_user_details_with_projects,
    merge_user_details,
    merge_user_details_with_projects,
)
from app.utilities.exceptions import ConflictException, PreconditionNotMetException, ValidationException
from app.utilities.security import Roles


def test_merge_user_details():
    keycloak_user = {"id": "398b1744-97dd-48f1-85cc-73f76caf98c0", "firstName": "John", "lastName": "Doe"}
    user = UserModel(
        id=uuid.UUID("398b1744-97dd-48f1-85cc-73f76caf98c0"),
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
    assert ret.id == user.id
    assert ret.role == Roles.PLATFORM_ADMINISTRATOR.value


@pytest.mark.asyncio
@patch("app.users.utils.get_organization_by_id_from_keycloak")
async def test_check_valid_email_domain_valid(get_organization_by_id_from_keycloak):
    get_organization_by_id_from_keycloak.return_value = {"domains": [{"name": "example.com", "verified": True}]}
    organization = AsyncMock()
    organization.keycloak_organization_id = "some-keycloak-id"
    kc_admin = AsyncMock()
    await check_valid_email_domain("test@example.com", organization, kc_admin)
    get_organization_by_id_from_keycloak.assert_called_once_with(kc_admin, organization.keycloak_organization_id)


@pytest.mark.asyncio
@patch("app.users.utils.get_organization_by_id_from_keycloak")
async def test_check_valid_email_domain_invalid(get_organization_by_id_from_keycloak):
    get_organization_by_id_from_keycloak.return_value = {"domains": [{"name": "example.com", "verified": True}]}
    organization = AsyncMock()
    organization.keycloak_organization_id = "some-keycloak-id"
    kc_admin = AsyncMock()
    with pytest.raises(
        ValidationException, match="User email domain 'invalid.com' is not in the organization's allowed domains"
    ):
        await check_valid_email_domain("test@invalid.com", organization, kc_admin)


def test_merge_user_details_with_projects_platform_admin():
    """Test merging user details with projects for a platform admin."""
    # Setup
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    keycloak_user = {
        "id": "kc-12345",
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
    }
    user = UserModel(
        id=user_id,
        email="jane.doe@example.com",
        keycloak_user_id="kc-12345",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-12345"}  # User is a platform admin

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

    # Execute
    result = merge_user_details_with_projects(keycloak_user, user, platform_admins, projects)

    # Assert
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
    # Setup
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    keycloak_user = {
        "id": "kc-67890",
        "firstName": "John",
        "lastName": "Smith",
        "email": "john.smith@example.com",
    }
    user = UserModel(
        id=user_id,
        email="john.smith@example.com",
        keycloak_user_id="kc-67890",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-12345"}  # User is not a platform admin

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

    # Execute
    result = merge_user_details_with_projects(keycloak_user, user, platform_admins, projects)

    # Assert
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
    # Setup
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    keycloak_user = {
        "id": "kc-12345",
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
    }
    user = UserModel(
        id=user_id,
        email="jane.doe@example.com",
        keycloak_user_id="kc-12345",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-12345"}

    # Execute - test with None
    result1 = merge_user_details_with_projects(keycloak_user, user, platform_admins, None)
    # Execute - test with empty list
    result2 = merge_user_details_with_projects(keycloak_user, user, platform_admins, [])

    # Assert
    assert isinstance(result1, UserWithProjects)
    assert len(result1.projects) == 0

    assert isinstance(result2, UserWithProjects)
    assert len(result2.projects) == 0


def test_merge_invited_user_details_with_projects_platform_admin():
    """Test merging invited user details with projects for a platform admin."""
    # Setup
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    user = UserModel(
        id=user_id,
        email="invited.admin@example.com",
        keycloak_user_id="kc-invite-admin",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        invited_at=datetime(2025, 2, 1, tzinfo=UTC),
        invited_by="admin@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-invite-admin"}  # User is a platform admin

    projects = [
        Project(
            id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
            name="projectx",
            description="projectx description",
            status=ProjectStatus.READY,
            cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_by="admin@example.com",
            updated_by="admin@example.com",
        ),
    ]

    # Execute
    result = merge_invited_user_details_with_projects(user, platform_admins, projects)

    # Assert
    assert isinstance(result, InvitedUserWithProjects)
    assert result.id == user_id
    assert result.email == "invited.admin@example.com"
    assert result.invited_at == datetime(2025, 2, 1, tzinfo=UTC)
    assert result.invited_by == "admin@example.com"
    assert result.role == Roles.PLATFORM_ADMINISTRATOR.value
    assert len(result.projects) == 1
    assert result.projects[0].name == "projectx"
    assert result.projects[0].description == "projectx description"


def test_merge_invited_user_details_with_projects_team_member():
    """Test merging invited user details with projects for a team member."""
    # Setup
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    user = UserModel(
        id=user_id,
        email="invited.member@example.com",
        keycloak_user_id="kc-invite-member",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        invited_at=datetime(2025, 3, 1, tzinfo=UTC),
        invited_by="admin@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-other-admin"}  # User is not a platform admin

    projects = [
        Project(
            id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
            name="projecty",
            description="projecty description",
            status=ProjectStatus.READY,
            cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_by="admin@example.com",
            updated_by="admin@example.com",
        ),
        Project(
            id=uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b"),
            name="projectz",
            description="projectz description",
            status=ProjectStatus.READY,
            cluster_id="1ab18e82-012c-45b7-a36e-dc3c0277974d",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_by="admin@example.com",
            updated_by="admin@example.com",
        ),
    ]

    # Execute
    result = merge_invited_user_details_with_projects(user, platform_admins, projects)

    # Assert
    assert isinstance(result, InvitedUserWithProjects)
    assert result.id == user_id
    assert result.email == "invited.member@example.com"
    assert result.invited_at == datetime(2025, 3, 1, tzinfo=UTC)
    assert result.invited_by == "admin@example.com"
    assert result.role == Roles.TEAM_MEMBER.value
    assert len(result.projects) == 2
    assert result.projects[0].name == "projecty"
    assert result.projects[1].name == "projectz"


def test_merge_invited_user_details_with_projects_no_projects():
    """Test merging invited user details with no projects."""
    # Setup
    user_id = uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b")
    user = UserModel(
        id=user_id,
        email="invited.user@example.com",
        keycloak_user_id="kc-invite-user",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        invited_at=datetime(2025, 4, 1, tzinfo=UTC),
        invited_by="admin@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-other-admin"}

    # Execute - test with None
    result1 = merge_invited_user_details_with_projects(user, platform_admins, None)
    # Execute - test with empty list
    result2 = merge_invited_user_details_with_projects(user, platform_admins, [])

    # Assert
    assert isinstance(result1, InvitedUserWithProjects)
    assert len(result1.projects) == 0

    assert isinstance(result2, InvitedUserWithProjects)
    assert len(result2.projects) == 0


@patch("app.users.utils.merge_user_details")
def test_merge_user_details_with_projects_calls_merge_user_details(mock_merge_user_details):
    """Test that merge_user_details_with_projects calls merge_user_details."""
    # Setup
    user = UserModel(
        id=uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b"),
        email="test@example.com",
        keycloak_user_id="kc-test",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    keycloak_user = {"id": "kc-test", "firstName": "Test", "lastName": "User"}
    platform_admins = {"kc-admin"}

    # Mock the return value of merge_user_details
    from app.users.schemas import UserResponse as UserSchema

    mock_merge_user_details.return_value = UserSchema(
        id=user.id,
        email=user.email,
        first_name="Test",
        last_name="User",
        role=Roles.TEAM_MEMBER.value,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )

    # Execute
    merge_user_details_with_projects(keycloak_user, user, platform_admins, [])

    # Assert
    mock_merge_user_details.assert_called_once_with(keycloak_user, user, platform_admins)


@patch("app.users.utils.merge_invited_user_details")
def test_merge_invited_user_details_with_projects_calls_merge_invited_user_details(mock_merge_invited_user_details):
    """Test that merge_invited_user_details_with_projects calls merge_invited_user_details."""
    # Setup
    user = UserModel(
        id=uuid.UUID("2c375428-1a9b-4e48-a025-8c4e81d2804b"),
        email="invited.test@example.com",
        keycloak_user_id="kc-invited-test",
        invited_at=datetime(2025, 5, 1, tzinfo=UTC),
        invited_by="admin@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-admin"}

    # Mock the return value of merge_invited_user_details
    from app.users.schemas import InvitedUser

    mock_merge_invited_user_details.return_value = InvitedUser(
        id=user.id,
        email=user.email,
        invited_at=user.invited_at,
        invited_by=user.invited_by,
        role=Roles.TEAM_MEMBER.value,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )

    # Execute
    merge_invited_user_details_with_projects(user, platform_admins, [])

    # Assert
    mock_merge_invited_user_details.assert_called_once_with(user, platform_admins)


def test_merge_invited_user_details_platform_admin():
    """Test merging invited user details for a platform admin."""
    user = UserModel(
        id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
        email="invited.admin@example.com",
        keycloak_user_id="kc-admin-123",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        invited_at=datetime(2025, 2, 1, tzinfo=UTC),
        invited_by="super@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="super@example.com",
        updated_by="super@example.com",
    )
    platform_admins = {"kc-admin-123"}

    from app.users.utils import merge_invited_user_details

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
    user = UserModel(
        id=uuid.UUID("1c375428-1a9b-4e48-a025-8c4e81d2804b"),
        email="invited.member@example.com",
        keycloak_user_id="kc-member-456",
        organization_id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        invited_at=datetime(2025, 3, 15, tzinfo=UTC),
        invited_by="admin@example.com",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    platform_admins = {"kc-other-admin"}  # User is not in platform admins

    from app.users.utils import merge_invited_user_details

    result = merge_invited_user_details(user, platform_admins)

    assert result.id == user.id
    assert result.email == "invited.member@example.com"
    assert result.invited_at == datetime(2025, 3, 15, tzinfo=UTC)
    assert result.invited_by == "admin@example.com"
    assert result.role == Roles.TEAM_MEMBER.value


def test_is_keycloak_user_active_with_complete_profile():
    """Test is_keycloak_user_active returns True when firstName and lastName are present."""
    from app.users.utils import is_keycloak_user_active

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
    from app.users.utils import is_keycloak_user_active

    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "lastName": "Doe",
    }

    assert is_keycloak_user_active(keycloak_user) is False


def test_is_keycloak_user_active_missing_last_name():
    """Test is_keycloak_user_active returns False when lastName is missing."""
    from app.users.utils import is_keycloak_user_active

    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "firstName": "John",
    }

    assert is_keycloak_user_active(keycloak_user) is False


def test_is_keycloak_user_active_missing_both_names():
    """Test is_keycloak_user_active returns False when both names are missing."""
    from app.users.utils import is_keycloak_user_active

    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
    }

    assert is_keycloak_user_active(keycloak_user) is False


def test_is_keycloak_user_active_empty_first_name():
    """Test is_keycloak_user_active returns True even with empty string firstName (key exists)."""
    from app.users.utils import is_keycloak_user_active

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
    from app.users.utils import is_keycloak_user_inactive

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
    from app.users.utils import is_keycloak_user_inactive

    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
    }

    assert is_keycloak_user_inactive(keycloak_user) is True


def test_is_keycloak_user_inactive_missing_first_name():
    """Test is_keycloak_user_inactive returns True when firstName is missing."""
    from app.users.utils import is_keycloak_user_inactive

    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "lastName": "Doe",
    }

    assert is_keycloak_user_inactive(keycloak_user) is True


def test_is_keycloak_user_inactive_missing_last_name():
    """Test is_keycloak_user_inactive returns True when lastName is missing."""
    from app.users.utils import is_keycloak_user_inactive

    keycloak_user = {
        "id": "kc-123",
        "username": "john.doe@example.com",
        "email": "john.doe@example.com",
        "firstName": "John",
    }

    assert is_keycloak_user_inactive(keycloak_user) is True


@pytest.mark.asyncio
@patch("app.users.utils.get_organization_by_id_from_keycloak")
async def test_check_valid_email_domain_no_domains_configured(get_organization_by_id_from_keycloak):
    """Test check_valid_email_domain when organization has no domains configured."""
    get_organization_by_id_from_keycloak.return_value = {"domains": []}
    organization = AsyncMock()
    organization.keycloak_organization_id = "some-keycloak-id"
    kc_admin = AsyncMock()

    # Should not raise exception when domains list is empty
    await check_valid_email_domain("test@anydomain.com", organization, kc_admin)


@pytest.mark.asyncio
@patch("app.users.utils.get_organization_by_id_from_keycloak")
async def test_check_valid_email_domain_multiple_domains_valid(get_organization_by_id_from_keycloak):
    """Test check_valid_email_domain with multiple allowed domains - valid email."""
    get_organization_by_id_from_keycloak.return_value = {
        "domains": [
            {"name": "example.com", "verified": True},
            {"name": "example.org", "verified": True},
            {"name": "test.com", "verified": True},
        ]
    }
    organization = AsyncMock()
    organization.keycloak_organization_id = "some-keycloak-id"
    kc_admin = AsyncMock()

    # Should not raise for domain in the list
    await check_valid_email_domain("user@example.org", organization, kc_admin)


@pytest.mark.asyncio
@patch("app.users.utils.get_organization_by_id_from_keycloak")
async def test_check_valid_email_domain_multiple_domains_invalid(get_organization_by_id_from_keycloak):
    """Test check_valid_email_domain with multiple allowed domains - invalid email."""
    get_organization_by_id_from_keycloak.return_value = {
        "domains": [
            {"name": "example.com", "verified": True},
            {"name": "example.org", "verified": True},
        ]
    }
    organization = AsyncMock()
    organization.keycloak_organization_id = "some-keycloak-id"
    kc_admin = AsyncMock()

    with pytest.raises(
        ValidationException, match="User email domain 'wrongdomain.com' is not in the organization's allowed domains"
    ):
        await check_valid_email_domain("user@wrongdomain.com", organization, kc_admin)


@pytest.mark.asyncio
@patch("app.users.utils.get_organization_by_id_from_keycloak")
async def test_check_valid_email_domain_org_not_found(get_organization_by_id_from_keycloak):
    """Test check_valid_email_domain when organization is not found in Keycloak."""
    from app.utilities.exceptions import ExternalServiceError

    get_organization_by_id_from_keycloak.return_value = None
    organization = AsyncMock()
    organization.keycloak_organization_id = "non-existent-id"
    kc_admin = AsyncMock()

    with pytest.raises(ExternalServiceError, match="Organization not found in Keycloak"):
        await check_valid_email_domain("test@example.com", organization, kc_admin)


@pytest.mark.asyncio
@patch("app.users.utils.get_organization_by_id_from_keycloak")
async def test_check_valid_email_domain_case_sensitivity(get_organization_by_id_from_keycloak):
    """Test that domain matching is case-sensitive (as per current implementation)."""
    get_organization_by_id_from_keycloak.return_value = {"domains": [{"name": "Example.com", "verified": True}]}
    organization = AsyncMock()
    organization.keycloak_organization_id = "some-keycloak-id"
    kc_admin = AsyncMock()

    # Current implementation is case-sensitive
    with pytest.raises(ValidationException):
        await check_valid_email_domain("user@example.com", organization, kc_admin)


@pytest.mark.asyncio
@patch("app.users.utils.set_temporary_password")
@patch("app.users.utils.create_user")
@patch("app.users.utils.enrich_organization_details")
async def test_create_user_in_keycloak_no_idp_no_smtp_with_temp_password(
    mock_enrich_org, mock_create_user, mock_set_temp_password
):
    """Test creating user in Keycloak when org has no IDP and no SMTP, with temp password."""
    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_enrich_org.return_value = OrganizationResponse(
        id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        name="Test Org",
        domains=["example.com"],
        idp_linked=False,
        smtp_enabled=False,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )

    mock_create_user.return_value = "new-user-kc-id"

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password="SecurePass123!")

    result = await create_user_in_keycloak(kc_admin, user_in, organization)

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
@patch("app.users.utils.enrich_organization_details")
async def test_create_user_in_keycloak_no_idp_no_smtp_no_temp_password(mock_enrich_org):
    """Test creating user in Keycloak when org has no IDP and no SMTP, without temp password."""
    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_enrich_org.return_value = OrganizationResponse(
        id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        name="Test Org",
        domains=["example.com"],
        idp_linked=False,
        smtp_enabled=False,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    # Execute and Assert
    from app.users.utils import create_user_in_keycloak

    with pytest.raises(ConflictException, match="Temporary password is required for user creation"):
        await create_user_in_keycloak(kc_admin, user_in, organization)


@pytest.mark.asyncio
@patch("app.users.utils.send_verify_email")
@patch("app.users.utils.create_user")
@patch("app.users.utils.enrich_organization_details")
async def test_create_user_in_keycloak_with_smtp_enabled(mock_enrich_org, mock_create_user, mock_send_verify_email):
    """Test creating user in Keycloak when SMTP is enabled."""
    from app.organizations.schemas import OrganizationResponse
    from app.users.schemas import InviteUser

    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_enrich_org.return_value = OrganizationResponse(
        id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        name="Test Org",
        domains=["example.com"],
        idp_linked=False,
        smtp_enabled=True,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    mock_create_user.return_value = "new-user-kc-id"

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    result = await create_user_in_keycloak(kc_admin, user_in, organization)

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
@patch("app.users.utils.enrich_organization_details")
async def test_create_user_in_keycloak_with_idp_linked(mock_enrich_org, mock_create_user, mock_send_verify_email):
    """Test creating user in Keycloak when IDP is linked and SMTP is enabled."""
    from app.organizations.schemas import OrganizationResponse
    from app.users.schemas import InviteUser

    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_enrich_org.return_value = OrganizationResponse(
        id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        name="Test Org",
        domains=["example.com"],
        idp_linked=True,
        smtp_enabled=True,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )
    mock_create_user.return_value = "new-user-kc-id"

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    # Execute
    from app.users.utils import create_user_in_keycloak

    result = await create_user_in_keycloak(kc_admin, user_in, organization)

    # Assert - should use SMTP flow even when IDP is linked
    assert result == "new-user-kc-id"
    mock_send_verify_email.assert_called_once()


@pytest.mark.asyncio
@patch("app.users.utils.enrich_organization_details")
async def test_create_user_in_keycloak_org_not_configured(mock_enrich_org):
    """Test creating user in Keycloak when organization is not properly configured."""
    from app.organizations.schemas import OrganizationResponse
    from app.users.schemas import InviteUser

    # Setup
    kc_admin = AsyncMock()
    organization = AsyncMock()
    organization.keycloak_organization_id = "org-123"

    mock_enrich_org.return_value = OrganizationResponse(
        id=uuid.UUID("8c375428-1a9b-4e48-a025-8c4e81d2804b"),
        name="Test Org",
        domains=["example.com"],
        idp_linked=True,
        smtp_enabled=False,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )

    user_in = InviteUser(email="newuser@example.com", roles=[], temporary_password=None)

    # Execute and Assert
    from app.users.utils import create_user_in_keycloak

    with pytest.raises(PreconditionNotMetException, match="Organization is not configured for user creation"):
        await create_user_in_keycloak(kc_admin, user_in, organization)
