# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.repository import (
    create_user,
    delete_user,
    get_user,
    get_user_by_email,
    get_users,
    get_users_by_ids,
    update_last_active_at,
)
from app.utilities.exceptions import ConflictException
from tests import factory  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_users_by_ids(db_session: AsyncSession) -> None:
    """Test getting users by IDs."""
    env = await factory.create_basic_test_environment(db_session)

    users = await factory.create_multiple_users(db_session, user_count=2, email_prefix="user_")

    user_ids = [user.id for user in users]
    results = await get_users_by_ids(db_session, user_ids)
    assert len(results) == 2

    # Test: Get specific users from org1
    specific_ids = [users[0].id, users[1].id]
    result_specific = await get_users_by_ids(db_session, specific_ids)
    assert len(result_specific) == 2


@pytest.mark.asyncio
async def test_get_users(db_session: AsyncSession) -> None:
    """Test getting all users."""
    _ = await factory.create_basic_test_environment(db_session)

    await factory.create_multiple_users(db_session, user_count=2)

    users = await get_users(db_session)
    assert len(users) == 2


@pytest.mark.asyncio
async def test_get_user(db_session: AsyncSession) -> None:
    """Test getting specific user."""
    user = await factory.create_user(db_session, email="test@example.com")

    found_user = await get_user(db_session, user.id)
    assert found_user is not None
    assert found_user.id == user.id


@pytest.mark.asyncio
async def test_get_user_by_email(db_session: AsyncSession) -> None:
    """Test getting user by email address."""
    user = await factory.create_user(db_session, email="test@example.com")

    # Test: Should find existing user
    found_user = await get_user_by_email(db_session, "test@example.com")
    assert found_user is not None
    assert found_user.id == user.id

    # Test: Should not find non-existent user
    not_found = await get_user_by_email(db_session, "nonexistent@example.com")
    assert not_found is None


@pytest.mark.asyncio
async def test_delete_user(db_session: AsyncSession) -> None:
    """Test user deletion from repository."""
    user = await factory.create_user(db_session, email="todelete@example.com")
    user_id = user.id

    found_user = await get_user(db_session, user_id)
    assert found_user is not None

    await delete_user(db_session, user_id)

    deleted_user = await get_user(db_session, user_id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_creates_user(db_session: AsyncSession) -> None:
    """Test creating user with repository function."""
    email = "newuser@test.com"
    creator = "test_creator"
    keycloak_user_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    user = await create_user(db_session, email, keycloak_user_id, creator)

    assert user.email == email
    assert user.created_by == creator
    assert user.updated_by == creator
    assert user.keycloak_user_id == keycloak_user_id


@pytest.mark.asyncio
async def test_creates_user_duplicate_email_raises_exception(db_session: AsyncSession) -> None:
    """Test that duplicate email raises integrity error."""
    email = "duplicate@test.com"
    creator = "test_creator"
    keycloak_user_id = "0aa18e92-002c-45b7-a06e-dcdb0277974c"

    await create_user(db_session, email, keycloak_user_id, creator)

    # Try to create duplicate user (case-insensitive email should fail)
    with pytest.raises(ConflictException) as exc_info:
        duplicate_email = "Duplicate@Test.com"  # Different case
        await create_user(db_session, duplicate_email, keycloak_user_id, creator)
    assert "Keycloak ID" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_last_active_at_sets_timestamp_and_flushes(db_session: AsyncSession) -> None:
    """Test updating user's last active timestamp."""
    user = await factory.create_user(db_session, email="test@example.com")

    # Initially last_active_at should be set by factory
    assert user.last_active_at is not None
    original_timestamp = user.last_active_at

    new_timestamp = datetime(2024, 1, 1, tzinfo=UTC)

    await update_last_active_at(db_session, user, new_timestamp)

    assert user.last_active_at == new_timestamp
    assert user.last_active_at != original_timestamp
