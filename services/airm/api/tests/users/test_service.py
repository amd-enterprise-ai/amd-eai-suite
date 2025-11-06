# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Users service tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakPostError
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.repository import get_user_by_email
from app.users.schemas import InviteUser, UserDetailsUpdate, UserRoleEnum, UserRolesUpdate
from app.users.schemas import UserResponse as UserSchema
from app.users.service import (
    POST_REGISTRATION_REDIRECT_URL,
    assign_roles_to_user,
    create_user_in_organization,
    delete_user,
    edit_user_details,
    get_invited_users_for_organization,
    get_user_details,
    get_users_for_organization,
    resend_invitation,
)
from app.utilities.exceptions import ConflictException, ExternalServiceError, NotFoundException
from app.utilities.security import Roles
from tests import factory


@pytest.mark.asyncio
async def test_get_user_details_handles_user_not_found_in_keycloak(db_session: AsyncSession):
    """Test handling when user exists in DB but not in Keycloak."""
    env = await factory.create_basic_test_environment(db_session)
    user = await factory.create_user(
        db_session,
        env.organization,
        email="user@example.com",
        keycloak_user_id="kc_user_id",
    )

    with (
        patch("app.users.service.get_user", return_value=None, autospec=True),
        patch("app.users.service.get_user_realm_roles", return_value=[], autospec=True),
        patch("app.users.service.get_user_groups", return_value=[], autospec=True),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        with pytest.raises(ExternalServiceError, match="User not found in Keycloak service"):
            await get_user_details(kc_admin, db_session, env.organization, user)


@pytest.mark.asyncio
async def test_get_user_details_handles_no_user_roles(db_session: AsyncSession):
    """Test user details retrieval when user has no roles."""
    env = await factory.create_basic_test_environment(db_session)
    user = await factory.create_user(
        db_session,
        env.organization,
        email="user@example.com",
        keycloak_user_id="kc_user_id",
    )

    # Create a test project that the user should have access to via groups
    test_project = await factory.create_project(
        db_session,
        env.organization,
        env.cluster,
        name="user-test-project",
    )

    keycloak_user = {
        "firstName": "test",
        "lastName": "Test",
        "email": "user@example.com",
    }
    user_roles: list[str] = []
    user_groups = [
        {"name": "user-test-project", "id": "group-id-123", "path": "/org/user-test-project"},
        {"name": "other-group", "id": "group-id-456", "path": "/org/other-group"},
    ]

    with (
        patch("app.users.service.get_user", return_value=keycloak_user, autospec=True),
        patch("app.users.service.get_user_realm_roles", return_value=user_roles, autospec=True),
        patch("app.users.service.get_user_groups", return_value=user_groups, autospec=True),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await get_user_details(kc_admin, db_session, env.organization, user)

    assert isinstance(result, UserSchema)
    assert result.email == "user@example.com"
    assert result.role == Roles.TEAM_MEMBER.value
    # Verify the user has access to the project matching the group name
    assert len(result.projects) == 1
    assert result.projects[0].name == "user-test-project"


@pytest.mark.asyncio
async def test_delete_user_success(db_session: AsyncSession):
    """Test successful user deletion from both DB and Keycloak."""
    env = await factory.create_basic_test_environment(db_session)
    user = await factory.create_user(
        db_session,
        env.organization,
        email="user1@test.com",
        keycloak_user_id="03890db1-9627-4663-ae0b-6a74ef1ff638",
    )

    with patch("app.users.service.delete_user_from_keycloak", return_value=None, autospec=True) as mock_delete_keycloak:
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        await delete_user(kc_admin, db_session, user)

    mock_delete_keycloak.assert_called_once()

    from app.users.repository import get_user_in_organization

    deleted_user = await get_user_in_organization(db_session, user.id, env.organization.id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_assign_roles_to_user_success(db_session: AsyncSession):
    """Test successful role assignment to user."""
    env = await factory.create_basic_test_environment(db_session)
    target_user = await factory.create_user(
        db_session,
        env.organization,
        email="user1@test.com",
        keycloak_user_id="03890db1-9627-4663-ae0b-6a74ef1ff638",
    )

    await factory.create_multiple_users(db_session, env.organization, user_count=2, email_prefix="other_user")

    user_role_request = UserRolesUpdate(roles=[UserRoleEnum.PLATFORM_ADMIN])

    keycloak_roles = [
        {"id": "role-id-1", "name": "Platform Administrator"},
        {"id": "role-id-2", "name": "Team Member"},
    ]

    with (
        patch("app.users.service.assign_roles_to_user_keycloak", return_value=None) as mock_assign_roles,
        patch("app.users.service.unassign_roles_to_user", return_value=None),
        patch(
            "app.users.service.get_assigned_roles_to_user",
            return_value={
                "realmMappings": [
                    {
                        "id": "f527862a-af68-4191-986a-cbcb25f15c24",
                        "name": "default-roles-airm",
                    }
                ]
            },
        ),
        patch("app.users.service.get_all_available_realm_roles", return_value=keycloak_roles),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        await assign_roles_to_user(kc_admin, target_user, user_role_request, "admin")

    mock_assign_roles.assert_called_once_with(
        kc_admin=kc_admin,
        user_id="03890db1-9627-4663-ae0b-6a74ef1ff638",
        roles=[{"id": "role-id-1", "name": "Platform Administrator"}],
    )


@pytest.mark.asyncio
async def test_create_user_in_organization_success(db_session: AsyncSession):
    """Test successful user creation with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    user_data = InviteUser(email="test@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
        patch("app.users.service.create_user_in_keycloak", return_value="keycloak_user_id"),
        patch("app.users.service.assign_user_to_organization_in_keycloak"),
        patch("app.users.service.assign_roles_to_user"),
        patch("app.users.service.send_verify_email"),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)

    assert result.email == "test@example.com"
    assert result.organization_id == env.organization.id
    assert result.created_by == creator

    db_user = await get_user_by_email(db_session, "test@example.com")
    assert db_user is not None
    assert db_user.email == "test@example.com"
    assert db_user.organization_id == env.organization.id


@pytest.mark.asyncio
async def test_create_user_in_organization_with_projects_success(db_session: AsyncSession):
    """Test successful user creation with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    user_data = InviteUser(email="test@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN], project_ids=[env.project.id])
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
        patch("app.users.service.create_user_in_keycloak", return_value="keycloak_user_id"),
        patch("app.users.service.assign_user_to_organization_in_keycloak"),
        patch("app.users.service.assign_roles_to_user"),
        patch("app.users.service.send_verify_email"),
        patch("app.users.service.assign_users_to_group") as mock_assign_users_to_group,
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)

    assert result.email == "test@example.com"
    assert result.organization_id == env.organization.id
    assert result.created_by == creator

    mock_assign_users_to_group.assert_called_once()

    db_user = await get_user_by_email(db_session, "test@example.com")
    assert db_user is not None
    assert db_user.email == "test@example.com"
    assert db_user.organization_id == env.organization.id


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises_conflict(db_session: AsyncSession):
    """Test that creating user with existing email raises ConflictException."""
    env = await factory.create_basic_test_environment(db_session)

    _ = await factory.create_user(db_session, env.organization, email="existing@example.com")

    user_data = InviteUser(email="existing@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)

        with pytest.raises(ConflictException, match="User is already a member of this organization"):
            await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)


@pytest.mark.asyncio
async def test_get_users_for_organization_with_real_data(db_session: AsyncSession):
    """Test retrieving users for organization with real database data."""
    env = await factory.create_basic_test_environment(db_session)

    users = await factory.create_multiple_users(db_session, env.organization, user_count=3)

    keycloak_users = [
        {
            "id": users[0].keycloak_user_id,
            "email": users[0].email,
            "firstName": "User",
            "lastName": "One",
            "enabled": True,
        },
        {
            "id": users[1].keycloak_user_id,
            "email": users[1].email,
            "firstName": "User",
            "lastName": "Two",
            "enabled": True,
        },
        {
            "id": users[2].keycloak_user_id,
            "email": users[2].email,
            "firstName": "User",
            "lastName": "Three",
            "enabled": False,
        },
    ]

    with (
        patch("app.users.service.get_users_in_organization_from_keycloak", return_value=keycloak_users),
        patch("app.users.service.get_user_realm_roles", return_value=[]),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await get_users_for_organization(kc_admin, db_session, env.organization)

    assert len(result) == 3
    emails = [user.email for user in result]
    assert users[0].email in emails
    assert users[1].email in emails
    assert users[2].email in emails


@pytest.mark.asyncio
async def test_create_user_in_organization_with_no_roles(db_session: AsyncSession):
    """Test successful user creation without roles."""
    env = await factory.create_basic_test_environment(db_session)

    user_data = InviteUser(email="test@example.com", roles=[])  # No roles
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
        patch("app.users.service.create_user_in_keycloak", return_value="keycloak_user_id"),
        patch("app.users.service.assign_user_to_organization_in_keycloak"),
        patch("app.users.service.assign_roles_to_user") as mock_assign_roles,
        patch("app.users.service.send_verify_email"),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)

    assert result.email == "test@example.com"
    assert result.organization_id == env.organization.id
    mock_assign_roles.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_in_organization_keycloak_error(db_session: AsyncSession):
    """Test user creation when Keycloak user creation fails."""
    env = await factory.create_basic_test_environment(db_session)

    user_data = InviteUser(email="test@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
        patch("app.users.service.create_user_in_keycloak", side_effect=KeycloakPostError("Keycloak error")),
        patch("app.users.service.assign_user_to_organization_in_keycloak"),
        patch("app.users.service.assign_roles_to_user"),
        patch("app.users.service.send_verify_email"),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)

        with pytest.raises(KeycloakPostError, match="Keycloak error"):
            await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)

    from app.users.repository import get_user_by_email

    db_user = await get_user_by_email(db_session, "test@example.com")
    assert db_user is None


@pytest.mark.asyncio
async def test_create_user_existing_user_no_organization(db_session: AsyncSession):
    """Test adding existing Keycloak user to new organization."""
    env = await factory.create_basic_test_environment(db_session)

    user_data = InviteUser(email="existing@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value={"id": "existing-kc-id"}),
        patch("app.users.service.create_user_in_keycloak"),
        patch("app.users.service.assign_user_to_organization_in_keycloak"),
        patch("app.users.service.assign_roles_to_user"),
        patch("app.users.service.send_verify_email") as mock_send_email,
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)

    assert result.email == "existing@example.com"
    assert result.organization_id == env.organization.id
    mock_send_email.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_with_invalid_project_ids(db_session: AsyncSession):
    """Test user creation fails with invalid project IDs."""
    env = await factory.create_basic_test_environment(db_session)

    valid_project = env.project

    invalid_project_id = uuid4()

    user_data = InviteUser(
        email="test@example.com",
        roles=[UserRoleEnum.PLATFORM_ADMIN],
        project_ids=[valid_project.id, invalid_project_id],  # Mix of valid and invalid
    )
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)

        with pytest.raises(NotFoundException, match="Projects not found in organization"):
            await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)


@pytest.mark.asyncio
async def test_create_user_with_project_memberships(db_session: AsyncSession):
    """Test user creation with project membership assignment."""
    env = await factory.create_basic_test_environment(db_session)

    project1 = env.project
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="Project 2")

    user_data = InviteUser(
        email="test@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN], project_ids=[project1.id, project2.id]
    )
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
        patch("app.users.service.create_user_in_keycloak", return_value="keycloak_user_id"),
        patch("app.users.service.assign_user_to_organization_in_keycloak"),
        patch("app.users.service.assign_roles_to_user"),
        patch("app.users.service.send_verify_email"),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await create_user_in_organization(kc_admin, db_session, env.organization, user_data, creator)

    assert result.email == "test@example.com"
    assert result.organization_id == env.organization.id


@pytest.mark.asyncio
async def test_create_user_part_of_different_organization(db_session: AsyncSession):
    """Test user creation when user is already in different organization."""
    # Create two organizations
    org1 = await factory.create_organization(db_session, name="Org 1", keycloak_organization_id="org1-id")
    org2 = await factory.create_organization(db_session, name="Org 2", keycloak_organization_id="org2-id")

    existing_user = await factory.create_user(db_session, org1, email="existing@example.com")

    user_data = InviteUser(email="existing@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])
    creator = "test_creator"

    with (
        patch("app.users.service.check_valid_email_domain"),
        patch("app.users.service.get_user_by_username_from_keycloak", return_value=None),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)

        with pytest.raises(ConflictException, match="User is already part of another organization"):
            await create_user_in_organization(kc_admin, db_session, org2, user_data, creator)


@pytest.mark.asyncio
async def test_assign_roles_to_user_remove_platform_admin_role(db_session: AsyncSession):
    """Test successful removal of Platform Administrator role when other admins exist."""
    env = await factory.create_basic_test_environment(db_session)

    target_user = await factory.create_user(
        db_session,
        env.organization,
        email="admin1@test.com",
        keycloak_user_id="admin1-id",
    )
    other_admin = await factory.create_user(
        db_session,
        env.organization,
        email="admin2@test.com",
        keycloak_user_id="admin2-id",
    )

    user_role_request = UserRolesUpdate(roles=[])  # Remove all roles

    # Mock Keycloak responses showing multiple users have PA role
    keycloak_roles = [
        {"id": "role-id-1", "name": "Platform Administrator"},
        {"id": "role-id-2", "name": "Team Member"},
    ]

    with (
        patch("app.users.service.assign_roles_to_user_keycloak", return_value=None),
        patch("app.users.service.unassign_roles_to_user", return_value=None) as mock_unassign,
        patch(
            "app.users.service.get_assigned_roles_to_user",
            return_value={
                "realmMappings": [
                    {
                        "id": "role-id-1",
                        "name": "Platform Administrator",
                    }
                ]
            },
        ),
        patch("app.users.service.get_all_available_realm_roles", return_value=keycloak_roles),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        await assign_roles_to_user(kc_admin, target_user, user_role_request, "admin")

    mock_unassign.assert_called_once()


@pytest.mark.asyncio
async def test_edit_user_details(db_session: AsyncSession):
    """Test updating user profile details."""
    env = await factory.create_basic_test_environment(db_session)
    user = await factory.create_user(
        db_session,
        env.organization,
        email="user@example.com",
        keycloak_user_id="user-kc-id",
    )

    user_details = UserDetailsUpdate(
        first_name="NewFirstName",
        last_name="NewLastName",
    )
    new_user_details = {
        "firstName": "NewFirstName",
        "lastName": "NewLastName",
    }

    with patch("app.users.service.update_user_details", return_value=None) as mock_update:
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        await edit_user_details(kc_admin, user, user_details, "updater")

    mock_update.assert_called_once_with(kc_admin=kc_admin, user_id=user.keycloak_user_id, user_details=new_user_details)
    assert user.updated_by == "updater"


@pytest.mark.asyncio
async def test_resend_invitation_success(db_session: AsyncSession):
    """Test successful invitation resend."""
    env = await factory.create_basic_test_environment(db_session)
    user = await factory.create_user(
        db_session,
        env.organization,
        email="user@example.com",
        keycloak_user_id="user-kc-id",
    )

    logged_in_user = "admin@example.com"
    keycloak_user = {
        "id": "user-kc-id",
        "email": "user@example.com",
    }

    with (
        patch("app.users.service.get_user", return_value=keycloak_user) as mock_get_user,
        patch("app.users.service.is_keycloak_user_inactive", return_value=True) as mock_is_inactive,
        patch("app.users.service.send_verify_email") as mock_send_email,
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        await resend_invitation(kc_admin, user, logged_in_user)

    mock_get_user.assert_called_once_with(kc_admin=kc_admin, user_id="user-kc-id")
    mock_is_inactive.assert_called_once_with(keycloak_user)
    mock_send_email.assert_called_once_with(
        kc_admin=kc_admin, keycloak_user_id="user-kc-id", redirect_uri=POST_REGISTRATION_REDIRECT_URL
    )
    assert user.invited_by == logged_in_user
    assert user.invited_at is not None


@pytest.mark.asyncio
async def test_resend_invitation_user_not_found_keycloak(db_session: AsyncSession):
    """Test resend invitation when user not found in Keycloak."""
    env = await factory.create_basic_test_environment(db_session)
    user = await factory.create_user(
        db_session,
        env.organization,
        email="user@example.com",
        keycloak_user_id="user-kc-id",
    )

    logged_in_user = "admin@example.com"

    with (
        patch("app.users.service.get_user", return_value=None),
        patch("app.users.service.is_keycloak_user_inactive", return_value=True),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        with pytest.raises(ExternalServiceError, match="User lookup failed"):
            await resend_invitation(kc_admin, user, logged_in_user)


@pytest.mark.asyncio
async def test_resend_invitation_user_already_active(db_session: AsyncSession):
    """Test resend invitation when user is already active."""
    env = await factory.create_basic_test_environment(db_session)
    user = await factory.create_user(
        db_session,
        env.organization,
        email="user@example.com",
        keycloak_user_id="user-kc-id",
    )

    logged_in_user = "admin@example.com"
    keycloak_user = {
        "id": "user-kc-id",
        "email": "user@example.com",
        "firstName": "Test",
        "lastName": "User",
    }

    with (
        patch("app.users.service.get_user", return_value=keycloak_user),
        patch("app.users.service.is_keycloak_user_inactive", return_value=False),
        patch("app.users.service.send_verify_email"),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        with pytest.raises(ConflictException, match="User is already active"):
            await resend_invitation(kc_admin, user, logged_in_user)


@pytest.mark.asyncio
async def test_get_invited_users_for_organization(db_session: AsyncSession):
    """Test getting invited users for organization."""
    env = await factory.create_basic_test_environment(db_session)

    users = await factory.create_multiple_users(db_session, env.organization, user_count=2)

    users[0].invited_at = datetime(2025, 1, 1, tzinfo=UTC)
    users[0].invited_by = "admin@example.com"
    users[1].invited_at = datetime(2025, 2, 1, tzinfo=UTC)
    users[1].invited_by = "admin@example.com"

    keycloak_users = [
        {"id": users[0].keycloak_user_id, "email": users[0].email},
        {"id": users[1].keycloak_user_id, "email": users[1].email},
    ]

    with (
        patch("app.users.service.get_users_in_role", return_value=[{"id": users[0].keycloak_user_id}]),
        patch("app.users.service.get_users_in_organization_from_keycloak", return_value=keycloak_users),
        patch("app.users.service.is_keycloak_user_active", side_effect=lambda u: False),
        patch("app.users.service.is_keycloak_user_inactive", side_effect=lambda u: True),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        result = await get_invited_users_for_organization(kc_admin, db_session, env.organization)

    assert len(result) == 2
    assert result[0].email == users[0].email
    assert result[0].invited_at == datetime(2025, 1, 1, tzinfo=UTC)
    assert result[1].email == users[1].email
