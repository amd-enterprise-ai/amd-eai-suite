# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.apikeys.repository import (
    create_api_key,
    delete_api_key,
    get_api_key_by_id,
    get_api_keys_for_project,
)
from app.utilities.exceptions import ConflictException
from tests import factory


@pytest.mark.asyncio
async def test_create_api_key(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    api_key = await create_api_key(
        session=db_session,
        name="Test API Key",
        truncated_key="amd_aim_api_key_••••••••1234",
        cluster_auth_key_id="cluster-auth-key-id-123",
        project_id=env.project.id,
        creator=creator,
    )

    assert api_key.name == "Test API Key"
    assert api_key.truncated_key == "amd_aim_api_key_••••••••1234"
    assert api_key.cluster_auth_key_id == "cluster-auth-key-id-123"
    assert api_key.project_id == env.project.id
    assert api_key.created_by == creator


@pytest.mark.asyncio
async def test_create_api_key_duplicate_name_raises_conflict(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    await create_api_key(
        session=db_session,
        name="Duplicate Key",
        truncated_key="amd_aim_api_key_••••••••1234",
        cluster_auth_key_id="cluster-auth-key-id-123",
        project_id=env.project.id,
        creator=creator,
    )

    with pytest.raises(ConflictException) as exc_info:
        await create_api_key(
            session=db_session,
            name="Duplicate Key",
            truncated_key="amd_aim_api_key_••••••••5678",
            cluster_auth_key_id="cluster-auth-key-id-456",
            project_id=env.project.id,
            creator=creator,
        )

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_api_keys_for_project(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    api_key1 = await create_api_key(
        session=db_session,
        name="Key 1",
        truncated_key="amd_aim_api_key_••••••••1111",
        cluster_auth_key_id="key-id-1",
        project_id=env.project.id,
        creator=creator,
    )

    api_key2 = await create_api_key(
        session=db_session,
        name="Key 2",
        truncated_key="amd_aim_api_key_••••••••2222",
        cluster_auth_key_id="key-id-2",
        project_id=env.project.id,
        creator=creator,
    )

    keys = await get_api_keys_for_project(db_session, env.project.id)

    assert len(keys) == 2
    assert keys[0].id in [api_key1.id, api_key2.id]
    assert keys[1].id in [api_key1.id, api_key2.id]


@pytest.mark.asyncio
async def test_get_api_key_by_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    created_key = await create_api_key(
        session=db_session,
        name="Specific Key",
        truncated_key="amd_aim_api_key_••••••••9999",
        cluster_auth_key_id="specific-key-id",
        project_id=env.project.id,
        creator=creator,
    )

    retrieved_key = await get_api_key_by_id(db_session, created_key.id, env.project.id)

    assert retrieved_key is not None
    assert retrieved_key.id == created_key.id
    assert retrieved_key.name == "Specific Key"


@pytest.mark.asyncio
async def test_get_api_key_by_id_wrong_project_returns_none(db_session: AsyncSession):
    env1 = await factory.create_basic_test_environment(db_session)
    org2 = await factory.create_organization(
        db_session, name="Different Org For API Keys Test", creator="test@test.com"
    )
    project2 = await factory.create_project(
        db_session, cluster=env1.cluster, organization=org2, name="Different Project", creator="test@test.com"
    )
    creator = "test-user@example.com"

    created_key = await create_api_key(
        session=db_session,
        name="Project 1 Key",
        truncated_key="amd_aim_api_key_••••••••8888",
        cluster_auth_key_id="project1-key-id",
        project_id=env1.project.id,
        creator=creator,
    )

    retrieved_key = await get_api_key_by_id(db_session, created_key.id, project2.id)

    assert retrieved_key is None


@pytest.mark.asyncio
async def test_delete_api_key(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    created_key = await create_api_key(
        session=db_session,
        name="Key to Delete",
        truncated_key="amd_aim_api_key_••••••••6666",
        cluster_auth_key_id="delete-key-id",
        project_id=env.project.id,
        creator=creator,
    )

    await delete_api_key(db_session, created_key)

    deleted_key = await get_api_key_by_id(db_session, created_key.id, env.project.id)
    assert deleted_key is None
