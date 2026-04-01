# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for API key service layer."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ExternalServiceError, NotFoundException
from app.apikeys import service
from app.apikeys.repository import get_api_key_by_id
from app.apikeys.schemas import ApiKeyCreate, ApiKeyUpdate
from tests import factory


@pytest.mark.asyncio
async def test_truncate_api_key() -> None:
    """Test API key truncation preserves prefix and shows last 4 chars."""
    full_key = "amd_aim_api_key_hvs.abc123def456"
    truncated = service.truncate_api_key(full_key)

    assert truncated.startswith("amd_aim_api_key_")
    assert truncated.endswith("f456")  # Last 4 chars of the token part
    assert "••••••••" in truncated


@pytest.mark.asyncio
async def test_truncate_api_key_invalid_prefix() -> None:
    """Test truncation fails for keys without proper prefix."""
    with pytest.raises(ValueError, match="must start with"):
        service.truncate_api_key("invalid_key_123")


@pytest.mark.asyncio
async def test_create_api_key_with_cluster_auth(
    db_session: AsyncSession,
    test_namespace: str,
    test_user: str,
    mock_cluster_auth_client: AsyncMock,
    mock_kube_client: AsyncMock,
) -> None:
    """Test creating an API key with cluster-auth integration."""
    api_key_in = ApiKeyCreate(
        name="Test Key",
        ttl="24h",
        num_uses=0,
        renewable=True,
    )

    result = await service.create_api_key_with_cluster_auth(
        session=db_session,
        kube_client=mock_kube_client,
        namespace=test_namespace,
        api_key_in=api_key_in,
        user=test_user,
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify cluster-auth was called to create the key
    mock_cluster_auth_client.create_api_key.assert_called_once()

    # Verify cluster-auth was called to lookup key details
    mock_cluster_auth_client.lookup_api_key.assert_called_once()

    # Verify the response
    assert result.name == "Test Key"
    assert result.namespace == test_namespace
    assert result.full_key == "amd_aim_api_key_hvs.abc123def456"
    assert result.truncated_key.startswith("amd_aim_api_key_")
    assert result.created_by == test_user

    # CRITICAL: Verify the record was actually created in the database
    db_record = await get_api_key_by_id(db_session, result.id, test_namespace)
    assert db_record is not None
    assert db_record.name == "Test Key"
    assert db_record.cluster_auth_key_id == "test-key-id-123"
    assert db_record.created_by == test_user


@pytest.mark.asyncio
async def test_create_api_key_with_aim_bindings(
    db_session: AsyncSession,
    test_namespace: str,
    test_user: str,
    mock_cluster_auth_client: AsyncMock,
    mock_kube_client: AsyncMock,
) -> None:
    """Test creating an API key with AIM group bindings."""
    # Use valid UUIDs for AIM IDs
    aim_id_1 = str(uuid4())
    aim_id_2 = str(uuid4())

    api_key_in = ApiKeyCreate(
        name="Test Key with AIMs",
        ttl="24h",
        num_uses=0,
        renewable=True,
        aim_ids=[aim_id_1, aim_id_2],
    )

    # Configure mock to return groups after binding
    mock_cluster_auth_client.lookup_api_key.return_value = {
        "ttl": "24h",
        "expire_time": "2025-01-16T12:00:00Z",
        "renewable": True,
        "num_uses": 0,
        "groups": ["ca-group-1", "ca-group-2"],
        "entity_id": "test-entity",
        "meta": {},
    }

    # Mock get_aim_service to return AIMService resources with cluster-auth group annotations
    mock_aim_service_1 = MagicMock()
    mock_aim_service_1.spec.routing = {"annotations": {"cluster-auth/allowed-group": "ca-group-1"}}
    mock_aim_service_2 = MagicMock()
    mock_aim_service_2.spec.routing = {"annotations": {"cluster-auth/allowed-group": "ca-group-2"}}

    async def mock_get_aim_service(kube_client, namespace, aim_id):
        if str(aim_id) == aim_id_1:
            return mock_aim_service_1
        elif str(aim_id) == aim_id_2:
            return mock_aim_service_2
        raise NotFoundException(f"AIM {aim_id} not found")

    with patch("app.apikeys.service.get_aim_service", side_effect=mock_get_aim_service):
        result = await service.create_api_key_with_cluster_auth(
            session=db_session,
            kube_client=mock_kube_client,
            namespace=test_namespace,
            api_key_in=api_key_in,
            user=test_user,
            cluster_auth_client=mock_cluster_auth_client,
        )

    # Verify binding was called for each AIM group
    assert mock_cluster_auth_client.bind_api_key_to_group.call_count == 2

    # Verify lookup was called twice (once before binding, once after)
    assert mock_cluster_auth_client.lookup_api_key.call_count == 2

    assert result.name == "Test Key with AIMs"


@pytest.mark.asyncio
async def test_create_api_key_revokes_on_db_failure(
    db_session: AsyncSession,
    test_namespace: str,
    test_user: str,
    mock_cluster_auth_client: AsyncMock,
    mock_kube_client: AsyncMock,
) -> None:
    """Test that cluster-auth key is revoked if database insert fails."""
    # Create a key with duplicate cluster_auth_key_id to force DB error
    existing_key = await factory.create_api_key(
        db_session,
        name="Existing Key",
        namespace=test_namespace,
        cluster_auth_key_id="test-key-id-123",  # Will conflict with mock response
    )

    api_key_in = ApiKeyCreate(
        name="New Key",
        ttl="24h",
        num_uses=0,
        renewable=True,
    )

    # Attempt to create should fail and trigger revocation
    with pytest.raises(Exception):
        await service.create_api_key_with_cluster_auth(
            session=db_session,
            kube_client=mock_kube_client,
            namespace=test_namespace,
            api_key_in=api_key_in,
            user=test_user,
            cluster_auth_client=mock_cluster_auth_client,
        )

    # Verify revocation was called to prevent orphaned key
    mock_cluster_auth_client.revoke_api_key.assert_called_once_with("test-key-id-123")


@pytest.mark.asyncio
async def test_list_api_keys_for_namespace(
    db_session: AsyncSession,
    test_namespace: str,
) -> None:
    """Test listing API keys for a namespace."""
    # Create test keys
    key1 = await factory.create_api_key(db_session, name="Key 1", namespace=test_namespace)
    key2 = await factory.create_api_key(db_session, name="Key 2", namespace=test_namespace)

    # Create key in different namespace (should not be returned)
    await factory.create_api_key(db_session, name="Other Key", namespace="other-namespace")

    result = await service.list_api_keys_for_namespace(
        session=db_session,
        namespace=test_namespace,
    )

    assert len(result) == 2
    assert {r.name for r in result} == {"Key 1", "Key 2"}
    assert all(r.namespace == test_namespace for r in result)


@pytest.mark.asyncio
async def test_get_api_key_details_from_cluster_auth(
    db_session: AsyncSession,
    test_namespace: str,
    test_user: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test getting API key details with cluster-auth metadata."""
    api_key = await factory.create_api_key(
        db_session,
        name="Test Key",
        namespace=test_namespace,
    )

    result = await service.get_api_key_details_from_cluster_auth(
        session=db_session,
        namespace=test_namespace,
        api_key_id=api_key.id,
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify cluster-auth lookup was called
    mock_cluster_auth_client.lookup_api_key.assert_called_once()

    assert result.id == api_key.id
    assert result.name == "Test Key"
    assert result.ttl == "24h"
    assert result.renewable is True


@pytest.mark.asyncio
async def test_get_api_key_details_not_found(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test getting details for non-existent API key."""
    random_id = uuid4()

    with pytest.raises(NotFoundException, match="not found"):
        await service.get_api_key_details_from_cluster_auth(
            session=db_session,
            namespace=test_namespace,
            api_key_id=random_id,
            cluster_auth_client=mock_cluster_auth_client,
        )


@pytest.mark.asyncio
async def test_get_api_key_details_orphaned_record_cleanup(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test that orphaned DB records are cleaned up when cluster-auth key is missing."""
    # Create API key in DB
    api_key = await factory.create_api_key(
        db_session,
        name="Orphaned Key",
        namespace=test_namespace,
    )

    # Configure mock to raise KeyError (key not found in cluster-auth)
    mock_cluster_auth_client.lookup_api_key.side_effect = KeyError("not found")

    # Should raise NotFoundException and clean up DB record
    with pytest.raises(NotFoundException, match="orphaned database record has been cleaned up"):
        await service.get_api_key_details_from_cluster_auth(
            session=db_session,
            namespace=test_namespace,
            api_key_id=api_key.id,
            cluster_auth_client=mock_cluster_auth_client,
        )

    # Verify the record was deleted from database
    deleted_key = await get_api_key_by_id(db_session, api_key.id, test_namespace)
    assert deleted_key is None


@pytest.mark.asyncio
async def test_delete_api_key_from_cluster_auth(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test deleting an API key and revoking in cluster-auth."""
    api_key = await factory.create_api_key(
        db_session,
        name="Key to Delete",
        namespace=test_namespace,
    )

    await service.delete_api_key_from_cluster_auth(
        session=db_session,
        namespace=test_namespace,
        api_key_id=api_key.id,
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify revocation was called
    mock_cluster_auth_client.revoke_api_key.assert_called_once()

    # Verify deletion from database
    deleted_key = await get_api_key_by_id(db_session, api_key.id, test_namespace)
    assert deleted_key is None


@pytest.mark.asyncio
async def test_delete_api_key_proceeds_when_already_revoked(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test deletion proceeds even if cluster-auth key is already gone."""
    api_key = await factory.create_api_key(
        db_session,
        name="Already Revoked Key",
        namespace=test_namespace,
    )

    # Configure mock to raise KeyError (already revoked)
    mock_cluster_auth_client.revoke_api_key.side_effect = KeyError("not found")

    # Should still delete from database
    await service.delete_api_key_from_cluster_auth(
        session=db_session,
        namespace=test_namespace,
        api_key_id=api_key.id,
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify deletion from database still happened
    deleted_key = await get_api_key_by_id(db_session, api_key.id, test_namespace)
    assert deleted_key is None


@pytest.mark.asyncio
async def test_renew_api_key_in_cluster_auth(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test renewing an API key in cluster-auth."""
    api_key = await factory.create_api_key(
        db_session,
        name="Key to Renew",
        namespace=test_namespace,
    )

    result = await service.renew_api_key_in_cluster_auth(
        session=db_session,
        namespace=test_namespace,
        api_key_id=api_key.id,
        cluster_auth_client=mock_cluster_auth_client,
    )

    mock_cluster_auth_client.renew_api_key.assert_called_once_with(api_key.cluster_auth_key_id)

    assert "lease_duration" in result


@pytest.mark.asyncio
async def test_renew_api_key_not_found(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test renewing non-existent API key fails."""
    random_id = uuid4()

    with pytest.raises(NotFoundException):
        await service.renew_api_key_in_cluster_auth(
            session=db_session,
            namespace=test_namespace,
            api_key_id=random_id,
            cluster_auth_client=mock_cluster_auth_client,
        )


@pytest.mark.asyncio
async def test_update_api_key_bindings_with_cluster_auth(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
    mock_kube_client: AsyncMock,
) -> None:
    """Test updating API key group bindings."""
    api_key = await factory.create_api_key(
        db_session,
        name="Key to Update",
        namespace=test_namespace,
    )

    # Use valid UUID for AIM ID
    aim_id_new = str(uuid4())

    # Current state: bound to ca-group-1
    mock_cluster_auth_client.lookup_api_key.return_value = {
        "ttl": "24h",
        "expire_time": "2025-01-16T12:00:00Z",
        "renewable": True,
        "num_uses": 0,
        "groups": ["ca-group-1"],
        "entity_id": "test-entity",
        "meta": {},
    }

    # Update to bind to ca-group-2 (should unbind from ca-group-1, bind to ca-group-2)
    api_key_update = ApiKeyUpdate(aim_ids=[aim_id_new])

    # Mock get_aim_service to return AIMService with ca-group-2
    mock_aim_service = MagicMock()
    mock_aim_service.spec.routing = {"annotations": {"cluster-auth/allowed-group": "ca-group-2"}}

    async def mock_get_aim_service(kube_client, namespace, aim_id):
        if str(aim_id) == aim_id_new:
            return mock_aim_service
        raise NotFoundException(f"AIM {aim_id} not found")

    with patch("app.apikeys.service.get_aim_service", side_effect=mock_get_aim_service):
        result = await service.update_api_key_bindings_with_cluster_auth(
            session=db_session,
            kube_client=mock_kube_client,
            namespace=test_namespace,
            api_key_id=api_key.id,
            api_key_update=api_key_update,
            cluster_auth_client=mock_cluster_auth_client,
        )

    # Verify synchronization was performed
    assert mock_cluster_auth_client.unbind_api_key_from_group.call_count == 1
    assert mock_cluster_auth_client.bind_api_key_to_group.call_count == 1


@pytest.mark.asyncio
async def test_update_api_key_bindings_orphaned_record_cleanup(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
    mock_kube_client: AsyncMock,
) -> None:
    """Test updating bindings cleans up orphaned DB record."""
    api_key = await factory.create_api_key(
        db_session,
        name="Orphaned Key",
        namespace=test_namespace,
    )

    # Configure mock to raise KeyError (key not found in cluster-auth)
    mock_cluster_auth_client.lookup_api_key.side_effect = KeyError("not found")

    api_key_update = ApiKeyUpdate(aim_ids=["group-1"])

    with pytest.raises(NotFoundException, match="orphaned database record has been cleaned up"):
        await service.update_api_key_bindings_with_cluster_auth(
            session=db_session,
            kube_client=mock_kube_client,
            namespace=test_namespace,
            api_key_id=api_key.id,
            api_key_update=api_key_update,
            cluster_auth_client=mock_cluster_auth_client,
        )

    # Verify the record was deleted from database
    deleted_key = await get_api_key_by_id(db_session, api_key.id, test_namespace)
    assert deleted_key is None


@pytest.mark.asyncio
async def test_update_api_key_bindings_sync_failure(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
    mock_kube_client: AsyncMock,
) -> None:
    """Test that binding sync failures raise appropriate errors."""
    api_key = await factory.create_api_key(
        db_session,
        name="Key with Sync Failure",
        namespace=test_namespace,
    )

    # Use valid UUID for AIM ID
    aim_id = str(uuid4())

    # Current state: no groups
    mock_cluster_auth_client.lookup_api_key.return_value = {
        "ttl": "24h",
        "expire_time": "2025-01-16T12:00:00Z",
        "renewable": True,
        "num_uses": 0,
        "groups": [],
        "entity_id": "test-entity",
        "meta": {},
    }

    # Simulate binding failure
    mock_cluster_auth_client.bind_api_key_to_group.side_effect = Exception("Binding failed")

    api_key_update = ApiKeyUpdate(aim_ids=[aim_id])

    # Mock get_aim_service to return AIMService with a group
    mock_aim_service = MagicMock()
    mock_aim_service.spec.routing = {"annotations": {"cluster-auth/allowed-group": "ca-group-1"}}

    async def mock_get_aim_service(kube_client, namespace, aim_id_arg):
        if str(aim_id_arg) == aim_id:
            return mock_aim_service
        raise NotFoundException(f"AIM {aim_id_arg} not found")

    with patch("app.apikeys.service.get_aim_service", side_effect=mock_get_aim_service):
        with pytest.raises(ExternalServiceError, match="synchronization failed"):
            await service.update_api_key_bindings_with_cluster_auth(
                session=db_session,
                kube_client=mock_kube_client,
                namespace=test_namespace,
                api_key_id=api_key.id,
                api_key_update=api_key_update,
                cluster_auth_client=mock_cluster_auth_client,
            )


@pytest.mark.asyncio
async def test_bind_api_key_to_group_in_cluster_auth(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test binding an API key to a group."""
    api_key = await factory.create_api_key(
        db_session,
        name="Key to Bind",
        namespace=test_namespace,
    )

    result = await service.bind_api_key_to_group_in_cluster_auth(
        session=db_session,
        namespace=test_namespace,
        api_key_id=api_key.id,
        group_id="test-group",
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify binding was called
    mock_cluster_auth_client.bind_api_key_to_group.assert_called_once()

    assert "groups" in result


@pytest.mark.asyncio
async def test_unbind_api_key_from_group_in_cluster_auth(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test unbinding an API key from a group."""
    api_key = await factory.create_api_key(
        db_session,
        name="Key to Unbind",
        namespace=test_namespace,
    )

    result = await service.unbind_api_key_from_group_in_cluster_auth(
        session=db_session,
        namespace=test_namespace,
        api_key_id=api_key.id,
        group_id="test-group",
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify unbinding was called
    mock_cluster_auth_client.unbind_api_key_from_group.assert_called_once()

    assert "groups" in result


@pytest.mark.asyncio
async def test_unbind_api_key_not_found_404(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
) -> None:
    """Test unbinding handles 404 errors from cluster-auth."""
    api_key = await factory.create_api_key(
        db_session,
        name="Key with Missing Group",
        namespace=test_namespace,
    )

    # Simulate 404 error
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_cluster_auth_client.unbind_api_key_from_group.side_effect = httpx.HTTPStatusError(
        "Not found", request=AsyncMock(), response=mock_response
    )

    with pytest.raises(NotFoundException):
        await service.unbind_api_key_from_group_in_cluster_auth(
            session=db_session,
            namespace=test_namespace,
            api_key_id=api_key.id,
            group_id="nonexistent-group",
            cluster_auth_client=mock_cluster_auth_client,
        )


@pytest.mark.asyncio
async def test_create_group_in_cluster_auth(mock_cluster_auth_client: AsyncMock) -> None:
    """Test creating a group in cluster-auth."""
    result = await service.create_group_in_cluster_auth(
        cluster_auth_client=mock_cluster_auth_client,
        name="Test Group",
        group_id="test-group-123",
    )

    # Verify group creation was called
    mock_cluster_auth_client.create_group.assert_called_once()

    assert result.id == "test-group-id"
    assert result.name == "test-group"


@pytest.mark.asyncio
async def test_delete_group_from_cluster_auth(mock_cluster_auth_client: AsyncMock) -> None:
    """Test deleting a group from cluster-auth."""
    await service.delete_group_from_cluster_auth(
        group_id="test-group-123",
        cluster_auth_client=mock_cluster_auth_client,
    )

    # Verify group deletion was called
    mock_cluster_auth_client.delete_group.assert_called_once_with("test-group-123")


@pytest.mark.asyncio
async def test_delete_group_not_found(mock_cluster_auth_client: AsyncMock) -> None:
    """Test deleting non-existent group raises NotFoundException."""
    # Simulate 404 error
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_cluster_auth_client.delete_group.side_effect = httpx.HTTPStatusError(
        "Not found", request=AsyncMock(), response=mock_response
    )

    with pytest.raises(NotFoundException, match="not found"):
        await service.delete_group_from_cluster_auth(
            group_id="nonexistent-group",
            cluster_auth_client=mock_cluster_auth_client,
        )


@pytest.mark.asyncio
async def test_create_group_with_custom_id(mock_cluster_auth_client: AsyncMock) -> None:
    """Test creating a group with user-provided custom ID."""
    custom_id = "custom-group-id-123"
    group_name = "Custom Group"

    # Mock response with custom ID
    mock_cluster_auth_client.create_group.return_value = {
        "id": custom_id,
        "name": group_name,
    }

    result = await service.create_group_in_cluster_auth(
        cluster_auth_client=mock_cluster_auth_client,
        name=group_name,
        group_id=custom_id,
    )

    # Verify custom ID was used
    mock_cluster_auth_client.create_group.assert_called_once_with(name=group_name, group_id=custom_id)
    assert result.id == custom_id
    assert result.name == group_name


@pytest.mark.asyncio
async def test_update_api_key_bindings_not_found(
    db_session: AsyncSession,
    test_namespace: str,
    mock_cluster_auth_client: AsyncMock,
    mock_kube_client: MagicMock,
) -> None:
    """Test updating bindings for non-existent API key raises NotFoundException."""
    nonexistent_id = uuid4()
    api_key_update = ApiKeyUpdate(aim_ids=[str(uuid4())])

    with pytest.raises(NotFoundException, match="not found"):
        await service.update_api_key_bindings_with_cluster_auth(
            session=db_session,
            kube_client=mock_kube_client,
            namespace=test_namespace,
            api_key_id=nonexistent_id,
            api_key_update=api_key_update,
            cluster_auth_client=mock_cluster_auth_client,
        )
