# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.users.models import User as UserModel
from app.users.schemas import InvitedUserWithProjects, UserWithProjects
from app.users.utils import (
    check_valid_email_domain,
    merge_invited_user_details_with_projects,
    merge_user_details,
    merge_user_details_with_projects,
)
from app.utilities.exceptions import ValidationException
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
