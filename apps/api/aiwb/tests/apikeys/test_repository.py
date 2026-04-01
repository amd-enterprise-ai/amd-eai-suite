# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ConflictException
from app.apikeys.repository import create_api_key, delete_api_key, get_api_key_by_id, get_api_keys_for_namespace
from tests import factory


@pytest.mark.asyncio
async def test_create_api_key(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test creating an API key."""
    unique_suffix = str(uuid4())[:8]
    name = f"Test API Key {unique_suffix}"

    api_key = await create_api_key(
        session=db_session,
        name=name,
        truncated_key="aiwb_api_key_••••••••1234",
        cluster_auth_key_id="cluster-auth-key-id-123",
        namespace=test_namespace,
        creator=test_user,
    )

    assert api_key.name == name
    assert api_key.truncated_key == "aiwb_api_key_••••••••1234"
    assert api_key.cluster_auth_key_id == "cluster-auth-key-id-123"
    assert api_key.namespace == test_namespace
    assert api_key.created_by == test_user


@pytest.mark.asyncio
async def test_create_api_key_duplicate_name_raises_conflict(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test that creating a duplicate API key name raises ConflictException."""
    unique_suffix = str(uuid4())[:8]
    name = f"Duplicate Key {unique_suffix}"

    # Create first API key
    await create_api_key(
        session=db_session,
        name=name,
        truncated_key="aiwb_api_key_••••••••1234",
        cluster_auth_key_id="cluster-auth-key-id-123",
        namespace=test_namespace,
        creator=test_user,
    )

    # Try to create duplicate
    with pytest.raises(ConflictException) as exc_info:
        await create_api_key(
            session=db_session,
            name=name,
            truncated_key="aiwb_api_key_••••••••5678",
            cluster_auth_key_id="cluster-auth-key-id-456",
            namespace=test_namespace,
            creator=test_user,
        )

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_api_keys_for_namespace(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test retrieving all API keys for a namespace."""
    unique_suffix = str(uuid4())[:8]

    api_key1 = await factory.create_api_key(
        db_session, name=f"Key 1 {unique_suffix}", namespace=test_namespace, created_by=test_user
    )

    api_key2 = await factory.create_api_key(
        db_session, name=f"Key 2 {unique_suffix}", namespace=test_namespace, created_by=test_user
    )

    # Create key in different namespace
    await factory.create_api_key(
        db_session, name=f"Other NS Key {unique_suffix}", namespace="other-namespace", created_by=test_user
    )

    keys = await get_api_keys_for_namespace(db_session, test_namespace)

    assert len(keys) == 2
    key_ids = {k.id for k in keys}
    assert api_key1.id in key_ids
    assert api_key2.id in key_ids


@pytest.mark.asyncio
async def test_get_api_key_by_id(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test retrieving a specific API key by ID."""
    unique_suffix = str(uuid4())[:8]

    created_key = await factory.create_api_key(
        db_session,
        name=f"Specific Key {unique_suffix}",
        namespace=test_namespace,
        truncated_key="aiwb_api_key_••••••••9999",
        cluster_auth_key_id="specific-key-id",
        created_by=test_user,
    )

    retrieved_key = await get_api_key_by_id(db_session, created_key.id, test_namespace)

    assert retrieved_key is not None
    assert retrieved_key.id == created_key.id
    assert retrieved_key.name == f"Specific Key {unique_suffix}"


@pytest.mark.asyncio
async def test_get_api_key_by_id_wrong_namespace_returns_none(db_session: AsyncSession, test_user: str) -> None:
    """Test that getting an API key from wrong namespace returns None."""
    unique_suffix = str(uuid4())[:8]

    created_key = await factory.create_api_key(
        db_session,
        name=f"Namespace 1 Key {unique_suffix}",
        namespace="namespace-1",
        truncated_key="aiwb_api_key_••••••••8888",
        cluster_auth_key_id="ns1-key-id",
        created_by=test_user,
    )

    retrieved_key = await get_api_key_by_id(db_session, created_key.id, "namespace-2")

    assert retrieved_key is None


@pytest.mark.asyncio
async def test_delete_api_key(db_session: AsyncSession, test_namespace: str, test_user: str) -> None:
    """Test deleting an API key."""
    unique_suffix = str(uuid4())[:8]

    created_key = await factory.create_api_key(
        db_session,
        name=f"Key to Delete {unique_suffix}",
        namespace=test_namespace,
        truncated_key="aiwb_api_key_••••••••6666",
        cluster_auth_key_id="delete-key-id",
        created_by=test_user,
    )

    key_id = created_key.id

    await delete_api_key(db_session, created_key)

    # Verify it's deleted
    deleted_key = await get_api_key_by_id(db_session, key_id, test_namespace)
    assert deleted_key is None
