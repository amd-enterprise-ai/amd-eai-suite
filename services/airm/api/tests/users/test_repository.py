# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.repository import (
    create_user_in_organization,
    delete_user,
    get_user_by_email,
    get_user_in_organization,
    get_users_in_organization,
    get_users_in_organization_by_ids,
    update_last_active_at,
)
from app.utilities.exceptions import ConflictException
from tests import factory


@pytest.mark.asyncio
async def test_get_users_in_organization_by_ids(db_session: AsyncSession):
    """Test getting users by IDs within specific organization scope."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    users_org1 = await factory.create_multiple_users(db_session, org1, user_count=2, email_prefix="user_org1_")
    users_org2 = await factory.create_multiple_users(db_session, org2, user_count=1, email_prefix="user_org2_")

    # Test: Get users from org1 with all user IDs should return only org1 users
    all_user_ids = [user.id for user in users_org1 + users_org2]
    result_org1 = await get_users_in_organization_by_ids(db_session, org1.id, all_user_ids)
    assert len(result_org1) == 2

    # Test: Get specific users from org1
    specific_ids = [users_org1[0].id, users_org1[1].id]
    result_specific = await get_users_in_organization_by_ids(db_session, org1.id, specific_ids)
    assert len(result_specific) == 2

    # Test: Get org2 user from org1 should return empty
    result_cross_org = await get_users_in_organization_by_ids(db_session, org1.id, [users_org2[0].id])
    assert len(result_cross_org) == 0


@pytest.mark.asyncio
async def test_get_users_in_organization(db_session: AsyncSession):
    """Test getting all users in organization."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    await factory.create_multiple_users(db_session, org1, user_count=2)

    # Test: Org1 should have 2 users
    users_org1 = await get_users_in_organization(db_session, org1.id)
    assert len(users_org1) == 2

    # Test: Org2 should have no users
    users_org2 = await get_users_in_organization(db_session, org2.id)
    assert len(users_org2) == 0


@pytest.mark.asyncio
async def test_get_user_in_organization(db_session: AsyncSession):
    """Test getting specific user within organization scope."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, cluster1, project1 = environments[0]
    org2, cluster2, project2 = environments[1]

    user = await factory.create_user(db_session, org1, email="test@example.com")

    # Test: User should be found in correct organization
    found_user = await get_user_in_organization(db_session, org1.id, user.id)
    assert found_user is not None
    assert found_user.id == user.id

    # Test: User should NOT be found in different organization
    not_found = await get_user_in_organization(db_session, org2.id, user.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_get_user_by_email(db_session: AsyncSession):
    """Test getting user by email address."""
    env = await factory.create_basic_test_environment(db_session)
    organization = env.organization

    user = await factory.create_user(db_session, organization, email="test@example.com")

    # Test: Should find existing user
    found_user = await get_user_by_email(db_session, "test@example.com")
    assert found_user is not None
    assert found_user.id == user.id

    # Test: Should not find non-existent user
    not_found = await get_user_by_email(db_session, "nonexistent@example.com")
    assert not_found is None


@pytest.mark.asyncio
async def test_delete_user(db_session: AsyncSession):
    """Test user deletion from repository."""
    env = await factory.create_basic_test_environment(db_session)
    organization = env.organization

    user = await factory.create_user(db_session, organization, email="todelete@example.com")
    user_id = user.id

    found_user = await get_user_in_organization(db_session, organization.id, user_id)
    assert found_user is not None

    await delete_user(db_session, user_id)

    deleted_user = await get_user_in_organization(db_session, organization.id, user_id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_creates_user_in_organization(db_session: AsyncSession):
    """Test creating user in organization with repository function."""
    env = await factory.create_basic_test_environment(db_session)
    organization = env.organization

    email = "newuser@test.com"
    creator = "test_creator"
    keycloak_user_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    user = await create_user_in_organization(db_session, organization.id, email, keycloak_user_id, creator)

    assert user.email == email
    assert user.organization_id == organization.id
    assert user.created_by == creator
    assert user.updated_by == creator
    assert user.keycloak_user_id == keycloak_user_id


@pytest.mark.asyncio
async def test_creates_user_duplicate_email_raises_exception(db_session: AsyncSession):
    """Test that duplicate email raises integrity error."""
    env = await factory.create_basic_test_environment(db_session)
    organization = env.organization

    email = "duplicate@test.com"
    creator = "test_creator"
    keycloak_user_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    await create_user_in_organization(db_session, organization.id, email, keycloak_user_id, creator)

    # Try to create duplicate user (case-insensitive email should fail)
    with pytest.raises(ConflictException) as exc_info:
        duplicate_email = "Duplicate@Test.com"  # Different case
        await create_user_in_organization(db_session, organization.id, duplicate_email, keycloak_user_id, creator)
    assert "Keycloak ID" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_last_active_at_sets_timestamp_and_flushes(db_session: AsyncSession):
    """Test updating user's last active timestamp."""
    env = await factory.create_basic_test_environment(db_session)
    organization = env.organization
    user = await factory.create_user(db_session, organization, email="test@example.com")

    # Initially last_active_at should be set by factory
    assert user.last_active_at is not None
    original_timestamp = user.last_active_at

    new_timestamp = datetime(2024, 1, 1, tzinfo=UTC)

    await update_last_active_at(db_session, user, new_timestamp)

    assert user.last_active_at == new_timestamp
    assert user.last_active_at != original_timestamp
