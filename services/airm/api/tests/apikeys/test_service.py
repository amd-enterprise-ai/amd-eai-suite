# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.apikeys.cluster_auth_client import ClusterAuthClient
from app.apikeys.repository import get_api_key_by_id
from app.apikeys.schemas import ApiKeyCreate
from app.apikeys.service import (
    _bind_api_key_to_aim_groups,
    bind_api_key_to_group_in_cluster_auth,
    create_api_key_with_cluster_auth,
    create_group_in_cluster_auth,
    delete_api_key_from_cluster_auth,
    delete_group_from_cluster_auth,
    get_api_key_details_from_cluster_auth,
    list_api_keys_for_project,
    renew_api_key_in_cluster_auth,
    truncate_api_key,
    unbind_api_key_from_group_in_cluster_auth,
    update_api_key_bindings_with_cluster_auth,
)
from app.managed_workloads.enums import WorkloadStatus
from app.utilities.exceptions import ConflictException, NotFoundException
from app.workloads.enums import WorkloadType
from tests import factory
from tests.factory import create_aim, create_aim_workload


def test_truncate_api_key():
    # Test prefixed key
    full_key = "amd_aim_api_key_hvs.CAESIJlWWvb3r_abc123def456"
    truncated = truncate_api_key(full_key)
    assert truncated == "amd_aim_api_key_••••••••f456"

    # Test that keys without prefix raise an error
    invalid_key = "7a3f9b2e1d4c8a6f5e9b2d1c3a7f4e8b"
    with pytest.raises(ValueError, match="API key must start with"):
        truncate_api_key(invalid_key)


@pytest.mark.asyncio
async def test_create_api_key_with_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Test Production Key {unique_suffix}",
        ttl="24h",
        renewable=True,
        num_uses=0,
        meta={"environment": "production"},
    )

    result = await create_api_key_with_cluster_auth(
        session=db_session,
        organization=env.organization,
        project=env.project,
        api_key_in=api_key_in,
        user=user,
        cluster_auth_client=mock_cluster_auth_client,
    )

    assert result.name == f"Test Production Key {unique_suffix}"
    assert len(result.full_key) > 0  # Just check that a key was generated
    assert result.full_key.startswith("amd_aim_api_key_")  # Check for prefix
    assert result.truncated_key.startswith("amd_aim_api_key_••••••••")  # Check truncated format
    assert result.ttl == "24h"
    assert result.renewable is True
    assert result.num_uses == 0
    assert result.project_id == env.project.id


@pytest.mark.asyncio
async def test_list_api_keys_for_project(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in1 = ApiKeyCreate(
        name=f"Key 1 {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )
    api_key_in2 = ApiKeyCreate(
        name=f"Key 2 {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in1, user, mock_cluster_auth_client
    )
    await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in2, user, mock_cluster_auth_client
    )

    keys = await list_api_keys_for_project(db_session, env.organization, env.project)

    assert len(keys) == 2
    assert keys[0].name in [f"Key 1 {unique_suffix}", f"Key 2 {unique_suffix}"]
    assert keys[1].name in [f"Key 1 {unique_suffix}", f"Key 2 {unique_suffix}"]


@pytest.mark.asyncio
async def test_get_api_key_details_from_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Detailed Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={"purpose": "testing"},
    )

    created = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    details = await get_api_key_details_from_cluster_auth(
        db_session, env.organization, env.project, created.id, mock_cluster_auth_client
    )

    assert details.name == f"Detailed Key {unique_suffix}"
    assert details.groups == []
    assert details.entity_id is not None
    assert details.meta == {"purpose": "testing"}


@pytest.mark.asyncio
async def test_get_api_key_details_not_found(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    non_existent_id = uuid4()
    with pytest.raises(NotFoundException):
        await get_api_key_details_from_cluster_auth(
            db_session, env.organization, env.project, non_existent_id, mock_cluster_auth_client
        )


@pytest.mark.asyncio
async def test_get_api_key_details_orphaned_record(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that orphaned DB records (not in Cluster Auth) are cleaned up automatically."""
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Orphaned Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    created = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    db_api_key = await get_api_key_by_id(db_session, created.id, env.project.id)
    assert db_api_key is not None

    # Simulate external deletion by making lookup fail (KeyError)
    original_lookup = mock_cluster_auth_client.lookup_api_key

    def failing_lookup(key_id: str):
        if key_id == db_api_key.cluster_auth_key_id:
            raise KeyError(f"API key {key_id} not found")
        return original_lookup(key_id)

    mock_cluster_auth_client.lookup_api_key = failing_lookup

    with pytest.raises(NotFoundException) as exc_info:
        await get_api_key_details_from_cluster_auth(
            db_session, env.organization, env.project, created.id, mock_cluster_auth_client
        )

    assert "orphaned database record has been cleaned up" in str(exc_info.value)

    # Verify the key was deleted from DB
    deleted_key = await get_api_key_by_id(db_session, created.id, env.project.id)
    assert deleted_key is None

    with pytest.raises(NotFoundException):
        await get_api_key_details_from_cluster_auth(
            db_session, env.organization, env.project, created.id, mock_cluster_auth_client
        )


@pytest.mark.asyncio
async def test_delete_api_key_from_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Key to Delete {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    created = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    await delete_api_key_from_cluster_auth(
        db_session, env.organization, env.project, created.id, mock_cluster_auth_client
    )

    with pytest.raises(NotFoundException):
        await get_api_key_details_from_cluster_auth(
            db_session, env.organization, env.project, created.id, mock_cluster_auth_client
        )


@pytest.mark.asyncio
async def test_renew_api_key_in_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Renewable Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    created = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    result = await renew_api_key_in_cluster_auth(
        db_session, env.organization, env.project, created.id, mock_cluster_auth_client, "2h"
    )

    assert "lease_duration" in result
    assert result["lease_duration"] == 7200


@pytest.mark.asyncio
async def test_bind_api_key_to_group_in_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Group Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    group = await mock_cluster_auth_client.create_group(f"test-group-{unique_suffix}")
    created = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    result = await bind_api_key_to_group_in_cluster_auth(
        db_session, env.organization, env.project, created.id, group["id"], mock_cluster_auth_client
    )

    assert "groups" in result
    assert group["id"] in result["groups"]


@pytest.mark.asyncio
async def test_unbind_api_key_from_group_in_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Unbind Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    group = await mock_cluster_auth_client.create_group(f"test-group-{unique_suffix}")
    created = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    await bind_api_key_to_group_in_cluster_auth(
        db_session, env.organization, env.project, created.id, group["id"], mock_cluster_auth_client
    )

    result = await unbind_api_key_from_group_in_cluster_auth(
        db_session, env.organization, env.project, created.id, group["id"], mock_cluster_auth_client
    )

    assert "groups" in result
    assert group["id"] not in result["groups"]


@pytest.mark.asyncio
async def test_create_api_key_db_insert_failure_revokes_cluster_auth_key(
    db_session: AsyncSession, mock_cluster_auth_client
):
    """Test that if DB insert fails, the Cluster Auth key is revoked to prevent orphaning."""
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Duplicate Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    # Create first key successfully
    first_key = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )
    # Commit the first key so it persists
    await db_session.commit()
    # Refresh project to avoid expired object issues
    await db_session.refresh(env.project)
    project_id = env.project.id  # Store ID before second attempt

    # Try to create duplicate key - should fail with ConflictException
    # The DB insert will fail due to unique constraint, and the cluster-auth key will be revoked
    with pytest.raises(ConflictException) as exc_info:
        await create_api_key_with_cluster_auth(
            db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
        )

    assert "already exists" in str(exc_info.value)

    # Rollback the session after the exception to clear the pending rollback state
    await db_session.rollback()
    # Refresh project again after rollback
    await db_session.refresh(env.project)

    # Verify that only one key remains active in Cluster Auth (second was revoked)
    # We need to check by looking up keys through the API
    # Since we can't enumerate all keys, we'll verify the second key creation was revoked
    # by checking the first key still exists and is valid
    keys = await list_api_keys_for_project(db_session, env.organization, env.project)
    assert len(keys) == 1


@pytest.mark.asyncio
async def test_create_api_key_cluster_auth_lookup_failure_revokes_key(
    db_session: AsyncSession, mock_cluster_auth_client
):
    """Test that if Cluster Auth lookup fails after creation, the key is revoked."""
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Lookup Failure Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    # Track the key_id that gets created
    created_key_id_container = {"key_id": None}

    # Patch lookup_api_key to fail after creation succeeds
    original_lookup = mock_cluster_auth_client.lookup_api_key
    original_create = mock_cluster_auth_client.create_api_key

    async def create_and_track(*args, **kwargs):
        result = await original_create(*args, **kwargs)
        created_key_id_container["key_id"] = result["key_id"]
        return result

    def failing_lookup(key_id: str):
        # Simulate lookup failure only for the key we're creating
        if key_id == created_key_id_container["key_id"]:
            raise KeyError(f"Simulated lookup failure for {key_id}")
        return original_lookup(key_id)

    mock_cluster_auth_client.create_api_key = create_and_track
    mock_cluster_auth_client.lookup_api_key = failing_lookup

    with pytest.raises(KeyError) as exc_info:
        await create_api_key_with_cluster_auth(
            db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
        )

    assert "Simulated lookup failure" in str(exc_info.value)

    # Verify that the key was revoked in Cluster Auth
    # Restore original lookup to check
    mock_cluster_auth_client.lookup_api_key = original_lookup
    # The key should be revoked - check by looking it up and verifying it's revoked
    # In the mock service, revoked keys still exist but are marked as revoked
    key_data = await mock_cluster_auth_client.lookup_api_key(created_key_id_container["key_id"])
    assert key_data.get("revoked") is True, "Key should be revoked"

    # Verify no key was created in DB since the whole operation failed
    # The DB insert happens before lookup, but the exception causes a rollback
    # So the key should not be in the DB
    # Use a fresh query to ensure we're not seeing cached data
    await db_session.rollback()
    keys = await list_api_keys_for_project(db_session, env.organization, env.project)
    # There might be other keys from previous tests, so we can't assert len == 0
    # Instead, verify our key name is not in the list
    key_names = [k.name for k in keys]
    assert f"Lookup Failure Key {unique_suffix}" not in key_names


@pytest.mark.asyncio
async def test_create_api_key_revocation_failure_still_propagates_error(
    db_session: AsyncSession, mock_cluster_auth_client
):
    """Test that if revocation fails, the original exception still propagates."""
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Revocation Failure Key {unique_suffix}",
        ttl="1h",
        renewable=True,
        num_uses=0,
        meta={},
    )

    # Patch both lookup_api_key and revoke_api_key to fail
    def failing_lookup(key_id: str):
        raise KeyError("Simulated lookup failure")

    def failing_revoke(key_id: str):
        raise Exception("Simulated revocation failure")

    mock_cluster_auth_client.lookup_api_key = failing_lookup
    mock_cluster_auth_client.revoke_api_key = failing_revoke

    # Should get the original KeyError, not the revocation error
    with pytest.raises(KeyError) as exc_info:
        await create_api_key_with_cluster_auth(
            db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
        )

    assert "Simulated lookup failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_group_in_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    """Test creating a group in Cluster Auth."""
    env = await factory.create_basic_test_environment(db_session)

    unique_suffix = str(uuid4())[:8]
    result = await create_group_in_cluster_auth(
        session=db_session,
        organization=env.organization,
        project=env.project,
        cluster_auth_client=mock_cluster_auth_client,
        name=f"Test Group {unique_suffix}",
        group_id=None,
    )

    assert result.name == f"Test Group {unique_suffix}"
    assert result.id is not None


@pytest.mark.asyncio
async def test_create_group_with_custom_id(db_session: AsyncSession, mock_cluster_auth_client):
    """Test creating a group with a custom ID."""
    env = await factory.create_basic_test_environment(db_session)

    custom_group_id = str(uuid4())
    unique_suffix = str(uuid4())[:8]
    result = await create_group_in_cluster_auth(
        session=db_session,
        organization=env.organization,
        project=env.project,
        cluster_auth_client=mock_cluster_auth_client,
        name=f"Custom ID Group {unique_suffix}",
        group_id=custom_group_id,
    )

    assert result.name == f"Custom ID Group {unique_suffix}"
    assert result.id == custom_group_id


@pytest.mark.asyncio
async def test_delete_group_from_cluster_auth(db_session: AsyncSession, mock_cluster_auth_client):
    """Test deleting a group from Cluster Auth."""
    env = await factory.create_basic_test_environment(db_session)

    unique_suffix = str(uuid4())[:8]
    group = await create_group_in_cluster_auth(
        session=db_session,
        organization=env.organization,
        project=env.project,
        cluster_auth_client=mock_cluster_auth_client,
        name=f"Group to Delete {unique_suffix}",
        group_id=None,
    )

    await delete_group_from_cluster_auth(
        session=db_session,
        organization=env.organization,
        project=env.project,
        group_id=group.id,
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify group is deleted by trying to delete again
    with pytest.raises(NotFoundException):
        await delete_group_from_cluster_auth(
            session=db_session,
            organization=env.organization,
            project=env.project,
            group_id=group.id,
            cluster_auth_client=mock_cluster_auth_client,
        )


@pytest.mark.asyncio
async def test_delete_group_not_found(db_session: AsyncSession, mock_cluster_auth_client):
    """Test deleting a non-existent group raises NotFoundException."""
    env = await factory.create_basic_test_environment(db_session)

    non_existent_group_id = str(uuid4())
    with pytest.raises(NotFoundException) as exc_info:
        await delete_group_from_cluster_auth(
            session=db_session,
            organization=env.organization,
            project=env.project,
            group_id=non_existent_group_id,
            cluster_auth_client=mock_cluster_auth_client,
        )

    assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_bind_api_key_to_aim_groups_success(db_session: AsyncSession, mock_cluster_auth_client):
    """Test successfully binding API key to AIM groups."""
    env = await factory.create_basic_test_environment(db_session)
    # Create AIMs and workloads with cluster-auth groups
    aim1 = await create_aim(db_session, resource_name="llama-v1", image_reference="docker.io/test/llama:v1")
    aim2 = await create_aim(db_session, resource_name="gpt-v2", image_reference="docker.io/test/gpt:v2")

    # Use UUIDs for group IDs to avoid collisions in parallel tests
    group_id_1 = str(uuid4())
    group_id_2 = str(uuid4())

    # Create workloads for the AIMs
    workload1 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim1,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=group_id_1,
    )
    workload2 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim2,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=group_id_2,
    )

    unique_suffix = str(uuid4())[:8]
    await mock_cluster_auth_client.create_group(name=f"test-group-1-{unique_suffix}", group_id=group_id_1)
    await mock_cluster_auth_client.create_group(name=f"test-group-2-{unique_suffix}", group_id=group_id_2)

    # Create an API key
    key_response = await mock_cluster_auth_client.create_api_key(ttl="1h")
    cluster_auth_key_id = key_response["key_id"]

    # Bind API key to AIM groups
    await _bind_api_key_to_aim_groups(
        session=db_session,
        project=env.project,
        cluster_auth_key_id=cluster_auth_key_id,
        aim_ids=[aim1.id, aim2.id],
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify the bindings
    key_details = await mock_cluster_auth_client.lookup_api_key(cluster_auth_key_id)
    assert group_id_1 in key_details["groups"]
    assert group_id_2 in key_details["groups"]


@pytest.mark.asyncio
async def test_bind_api_key_to_aim_groups_partial_failure(db_session: AsyncSession, mock_cluster_auth_client):
    """Test handling of partial failures when binding API key to AIM groups."""
    from app.apikeys.service import _bind_api_key_to_aim_groups
    from app.managed_workloads.enums import WorkloadStatus
    from app.workloads.enums import WorkloadType
    from tests.factory import create_aim, create_aim_workload

    env = await factory.create_basic_test_environment(db_session)

    # Use UUIDs for group IDs to avoid collisions in parallel tests
    group_id_success = str(uuid4())
    group_id_fail = str(uuid4())

    # Custom wrapper that fails on specific group bindings
    class PartialFailureClient:
        def __init__(self, client: ClusterAuthClient):
            self._client = client

        async def create_api_key(self, *args, **kwargs):
            return await self._client.create_api_key(*args, **kwargs)

        async def lookup_api_key(self, *args, **kwargs):
            return await self._client.lookup_api_key(*args, **kwargs)

        async def create_group(self, *args, **kwargs):
            return await self._client.create_group(*args, **kwargs)

        async def bind_api_key_to_group(self, key_id: str, group_id: str) -> dict:
            if group_id == group_id_fail:
                raise Exception("Simulated binding failure")
            return await self._client.bind_api_key_to_group(key_id, group_id)

    failing_client = PartialFailureClient(mock_cluster_auth_client)

    # Create AIMs and workloads
    aim1 = await create_aim(db_session, resource_name="llama-v1", image_reference="docker.io/test/llama:v1")
    aim2 = await create_aim(db_session, resource_name="gpt-v2", image_reference="docker.io/test/gpt:v2")

    workload1 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim1,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=group_id_success,
    )
    workload2 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim2,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=group_id_fail,
    )

    # Create groups
    unique_suffix = str(uuid4())[:8]
    await failing_client.create_group(name=f"success-group-{unique_suffix}", group_id=group_id_success)
    await failing_client.create_group(name=f"fail-group-{unique_suffix}", group_id=group_id_fail)

    # Create API key
    key_response = await failing_client.create_api_key(ttl="1h")
    cluster_auth_key_id = key_response["key_id"]

    # This should not raise an exception, but should continue with successful bindings
    await _bind_api_key_to_aim_groups(
        session=db_session,
        project=env.project,
        cluster_auth_key_id=cluster_auth_key_id,
        aim_ids=[aim1.id, aim2.id],
        cluster_auth_client=failing_client,
    )

    # Verify successful binding
    key_details = await failing_client.lookup_api_key(cluster_auth_key_id)
    assert group_id_success in key_details["groups"]
    # group_fail should not be bound due to the simulated failure
    assert group_id_fail not in key_details["groups"]


@pytest.mark.asyncio
async def test_bind_api_key_to_aim_groups_no_deployed_aims(db_session: AsyncSession, mock_cluster_auth_client):
    """Test binding when no AIMs are deployed or have cluster-auth groups."""
    env = await factory.create_basic_test_environment(db_session)
    # Create AIM but no workload (not deployed)
    aim = await create_aim(db_session, resource_name="llama-v1", image_reference="docker.io/test/llama:v1")

    # Create API key
    key_response = await mock_cluster_auth_client.create_api_key(ttl="1h")
    cluster_auth_key_id = key_response["key_id"]

    # Should not raise an exception even when no workloads exist
    await _bind_api_key_to_aim_groups(
        session=db_session,
        project=env.project,
        cluster_auth_key_id=cluster_auth_key_id,
        aim_ids=[aim.id],
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify no bindings were made
    key_details = await mock_cluster_auth_client.lookup_api_key(cluster_auth_key_id)
    assert len(key_details["groups"]) == 0


@pytest.mark.asyncio
async def test_create_api_key_with_aim_binding(db_session: AsyncSession, mock_cluster_auth_client):
    """Test creating API key with AIM binding integration."""
    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    # Use UUID for group ID to avoid collisions in parallel tests
    aim_group_id = str(uuid4())

    # Create AIM and deployed workload
    aim = await create_aim(db_session, resource_name="llama-v1", image_reference="docker.io/test/llama:v1")
    workload = await create_aim_workload(
        db_session,
        env.project,
        aim=aim,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id,
    )

    # Create group in mock client
    unique_suffix = str(uuid4())[:8]
    await mock_cluster_auth_client.create_group(name=f"aim-group-{unique_suffix}", group_id=aim_group_id)

    # Create API key with AIM binding
    unique_key_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(
        name=f"Test Key with AIM Binding {unique_key_suffix}",
        ttl="24h",
        renewable=True,
        num_uses=0,
        meta={"purpose": "testing"},
        aim_ids=[aim.id],
    )

    result = await create_api_key_with_cluster_auth(
        session=db_session,
        organization=env.organization,
        project=env.project,
        api_key_in=api_key_in,
        user=user,
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify API key was created
    assert result.name == f"Test Key with AIM Binding {unique_key_suffix}"
    assert result.project_id == env.project.id
    assert len(result.full_key) > 0

    # Verify the key was bound to the AIM group by checking lookup
    # We need to get the key_id from the result
    db_api_key = await get_api_key_by_id(db_session, result.id, env.project.id)
    key_details = await mock_cluster_auth_client.lookup_api_key(db_api_key.cluster_auth_key_id)
    assert aim_group_id in key_details["groups"]


@pytest.mark.asyncio
async def test_update_api_key_bindings_success(db_session: AsyncSession, mock_cluster_auth_client):
    """Test updating API key bindings with new AIM IDs"""
    from app.apikeys.schemas import ApiKeyUpdate
    from app.managed_workloads.enums import WorkloadStatus
    from app.workloads.enums import WorkloadType
    from tests.factory import create_aim, create_aim_workload

    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    # Use UUIDs for group IDs to avoid collisions in parallel tests
    aim_group_id_1 = str(uuid4())
    aim_group_id_2 = str(uuid4())

    # Create an API key
    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(name=f"Test Key {unique_suffix}", ttl="1h")

    created_key = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    # Create two AIMs with deployed workloads
    aim_1 = await create_aim(db_session, resource_name="model-1-v1", image_reference="docker.io/test/model-1:v1")
    aim_2 = await create_aim(db_session, resource_name="model-2-v1", image_reference="docker.io/test/model-2:v1")

    workload_1 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim_1,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id_1,
    )
    workload_2 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim_2,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id_2,
    )

    # Create groups in mock client
    group_suffix = str(uuid4())[:8]
    await mock_cluster_auth_client.create_group(name=f"aim-group-1-{group_suffix}", group_id=aim_group_id_1)
    await mock_cluster_auth_client.create_group(name=f"aim-group-2-{group_suffix}", group_id=aim_group_id_2)

    # Update bindings to include both AIMs
    update_data = ApiKeyUpdate(aim_ids=[aim_1.id, aim_2.id])

    result = await update_api_key_bindings_with_cluster_auth(
        db_session, env.organization, env.project, created_key.id, update_data, mock_cluster_auth_client
    )

    assert result.id == created_key.id
    assert aim_group_id_1 in result.groups
    assert aim_group_id_2 in result.groups


@pytest.mark.asyncio
async def test_update_api_key_bindings_removes_old_groups(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that updating API key bindings removes old groups"""
    from app.apikeys.schemas import ApiKeyUpdate
    from app.managed_workloads.enums import WorkloadStatus
    from app.workloads.enums import WorkloadType
    from tests.factory import create_aim, create_aim_workload

    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    # Use UUIDs for group IDs to avoid collisions in parallel tests
    aim_group_id_1 = str(uuid4())
    aim_group_id_2 = str(uuid4())

    # Create two AIMs with deployed workloads
    aim_1 = await create_aim(db_session, resource_name="model-1-v1", image_reference="docker.io/test/model-1:v1")
    aim_2 = await create_aim(db_session, resource_name="model-2-v1", image_reference="docker.io/test/model-2:v1")

    workload_1 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim_1,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id_1,
    )
    workload_2 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim_2,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id_2,
    )

    # Create groups in mock client
    group_suffix = str(uuid4())[:8]
    await mock_cluster_auth_client.create_group(name=f"aim-group-1-{group_suffix}", group_id=aim_group_id_1)
    await mock_cluster_auth_client.create_group(name=f"aim-group-2-{group_suffix}", group_id=aim_group_id_2)

    # Create API key with initial binding to aim_1
    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(name=f"Test Key {unique_suffix}", ttl="1h", aim_ids=[aim_1.id])

    created_key = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    # Verify initial binding
    details = await get_api_key_details_from_cluster_auth(
        db_session, env.organization, env.project, created_key.id, mock_cluster_auth_client
    )
    assert aim_group_id_1 in details.groups

    # Update to only bind to aim_2 (should remove aim-group-1)
    update_data = ApiKeyUpdate(aim_ids=[aim_2.id])

    result = await update_api_key_bindings_with_cluster_auth(
        db_session, env.organization, env.project, created_key.id, update_data, mock_cluster_auth_client
    )

    assert aim_group_id_1 not in result.groups
    assert aim_group_id_2 in result.groups


@pytest.mark.asyncio
async def test_update_api_key_bindings_empty_aim_ids(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that updating with empty aim_ids removes all bindings"""
    from app.apikeys.schemas import ApiKeyUpdate
    from app.managed_workloads.enums import WorkloadStatus
    from app.workloads.enums import WorkloadType
    from tests.factory import create_aim, create_aim_workload

    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    # Use UUID for group ID to avoid collisions in parallel tests
    aim_group_id = str(uuid4())

    # Create AIM with deployed workload
    aim = await create_aim(db_session, resource_name="model-v1", image_reference="docker.io/test/model:v1")
    workload = await create_aim_workload(
        db_session,
        env.project,
        aim=aim,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id,
    )

    # Create group in mock client
    group_suffix = str(uuid4())[:8]
    await mock_cluster_auth_client.create_group(name=f"aim-group-{group_suffix}", group_id=aim_group_id)

    # Create API key with initial binding
    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(name=f"Test Key {unique_suffix}", ttl="1h", aim_ids=[aim.id])

    created_key = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    # Update with empty aim_ids (should remove all groups)
    update_data = ApiKeyUpdate(aim_ids=[])

    result = await update_api_key_bindings_with_cluster_auth(
        db_session, env.organization, env.project, created_key.id, update_data, mock_cluster_auth_client
    )

    assert len(result.groups) == 0


@pytest.mark.asyncio
async def test_update_api_key_bindings_not_found(db_session: AsyncSession, mock_cluster_auth_client):
    """Test updating non-existent API key raises NotFoundException"""
    from app.apikeys.schemas import ApiKeyUpdate

    env = await factory.create_basic_test_environment(db_session)

    update_data = ApiKeyUpdate(aim_ids=[])
    non_existent_id = uuid4()

    with pytest.raises(NotFoundException):
        await update_api_key_bindings_with_cluster_auth(
            db_session, env.organization, env.project, non_existent_id, update_data, mock_cluster_auth_client
        )


@pytest.mark.asyncio
async def test_update_api_key_bindings_fails_on_binding_error(
    db_session: AsyncSession, mock_cluster_auth_client: ClusterAuthClient
):
    """Test that binding failures during update raise ExternalServiceError"""
    from app.apikeys.schemas import ApiKeyUpdate
    from app.managed_workloads.enums import WorkloadStatus
    from app.utilities.exceptions import ExternalServiceError
    from app.workloads.enums import WorkloadType
    from tests.factory import create_aim, create_aim_workload

    env = await factory.create_basic_test_environment(db_session)
    user = "test-user@example.com"

    # Use UUIDs for group IDs to avoid collisions in parallel tests
    aim_group_id_1 = str(uuid4())
    aim_group_id_2 = str(uuid4())

    # Custom client that fails on specific group bindings
    class FailingBindClient(ClusterAuthClient):
        async def bind_api_key_to_group(self, key_id: str, group_id: str) -> dict:
            if group_id == aim_group_id_2:
                raise Exception("Simulated binding failure")
            return await super().bind_api_key_to_group(key_id, group_id)

    # Create failing client with same connection as mock_cluster_auth_client
    failing_client = FailingBindClient(
        base_url=mock_cluster_auth_client.base_url, admin_token=mock_cluster_auth_client.admin_token
    )

    # Create two AIMs with deployed workloads
    aim_1 = await create_aim(db_session, resource_name="model-1-v1", image_reference="docker.io/test/model-1:v1")
    aim_2 = await create_aim(db_session, resource_name="model-2-v1", image_reference="docker.io/test/model-2:v1")

    workload_1 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim_1,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id_1,
    )
    workload_2 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim_2,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=aim_group_id_2,
    )

    # Create groups using the real mock client first
    group_suffix = str(uuid4())[:8]
    await mock_cluster_auth_client.create_group(name=f"aim-group-1-{group_suffix}", group_id=aim_group_id_1)
    await mock_cluster_auth_client.create_group(name=f"aim-group-2-{group_suffix}", group_id=aim_group_id_2)

    # Create API key with initial binding to aim_1 using real mock client
    unique_suffix = str(uuid4())[:8]
    api_key_in = ApiKeyCreate(name=f"Test Key {unique_suffix}", ttl="1h", aim_ids=[aim_1.id])
    created_key = await create_api_key_with_cluster_auth(
        db_session, env.organization, env.project, api_key_in, user, mock_cluster_auth_client
    )

    # Try to update bindings to include aim_2 using the failing client (which will fail)
    update_data = ApiKeyUpdate(aim_ids=[aim_1.id, aim_2.id])

    # Should raise ExternalServiceError due to binding failure
    try:
        with pytest.raises(ExternalServiceError) as exc_info:
            await update_api_key_bindings_with_cluster_auth(
                db_session, env.organization, env.project, created_key.id, update_data, failing_client
            )

        # Verify error message mentions the failure
        assert "Failed to bind to 1 group(s)" in str(exc_info.value)
    finally:
        # Clean up the custom client
        await failing_client.close()
