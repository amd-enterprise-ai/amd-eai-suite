# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Tests for API keys router endpoints.

Uses TestClient with dependency overrides for consistent HTTP-level testing.
"""

from unittest.mock import patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app import app  # type: ignore[attr-defined]
from app.apikeys.schemas import ApiKeyDetails, ApiKeyResponse, ApiKeyWithFullKey, GroupResponse
from tests.dependency_overrides import CLUSTER_AUTH_OVERRIDES, override_dependencies


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_get_api_keys_success() -> None:
    """Test listing API keys for a namespace."""
    expected_keys = [
        ApiKeyResponse(
            id=uuid4(),
            name="Production Key",
            truncated_key="amd_aim_api_key_••••••••1234",
            namespace="test-namespace",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            created_by="test@example.com",
            updated_by="test@example.com",
        )
    ]

    with patch("app.apikeys.router.list_api_keys_for_namespace") as mock_service:
        mock_service.return_value = expected_keys
        with TestClient(app) as client:
            response = client.get("/v1/namespaces/test-namespace/api-keys")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"][0]["name"] == "Production Key"


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_create_api_key_success() -> None:
    """Test creating a new API key."""
    expected_response = ApiKeyWithFullKey(
        id=uuid4(),
        name="New Key",
        truncated_key="amd_aim_api_key_••••••••5678",
        namespace="test-namespace",
        expires_at=None,
        renewable=True,
        num_uses=0,
        ttl="24h",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
        full_key="amd_aim_api_key_hvs.7a3f9b2e1d4c8a6f5e9b2d1c3a7f5678",
    )

    with patch("app.apikeys.router.create_api_key_with_cluster_auth") as mock_service:
        mock_service.return_value = expected_response
        with TestClient(app) as client:
            response = client.post(
                "/v1/namespaces/test-namespace/api-keys",
                json={"name": "New Key", "ttl": "24h", "renewable": True, "num_uses": 0, "meta": {}},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "New Key"


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_get_api_key_details_success() -> None:
    """Test getting detailed API key information."""
    api_key_id = uuid4()
    expected_details = ApiKeyDetails(
        id=api_key_id,
        name="Detailed Key",
        truncated_key="amd_aim_api_key_••••••••9999",
        namespace="test-namespace",
        expires_at=None,
        renewable=True,
        num_uses=0,
        ttl="1h",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
        groups=["group-1", "group-2"],
        entity_id="entity-123",
        meta={"environment": "production"},
    )

    with patch("app.apikeys.router.get_api_key_details_from_cluster_auth") as mock_service:
        mock_service.return_value = expected_details
        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/test-namespace/api-keys/{api_key_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Detailed Key"


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_delete_api_key_success() -> None:
    """Test deleting an API key."""
    with patch("app.apikeys.router.delete_api_key_from_cluster_auth") as mock_service:
        mock_service.return_value = None
        with TestClient(app) as client:
            response = client.delete(f"/v1/namespaces/test-namespace/api-keys/{uuid4()}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_renew_api_key_success() -> None:
    """Test renewing an API key's lease."""
    with patch("app.apikeys.router.renew_api_key_in_cluster_auth") as mock_service:
        mock_service.return_value = {"lease_duration": 3600}
        with TestClient(app) as client:
            response = client.post(f"/v1/namespaces/test-namespace/api-keys/{uuid4()}/renew")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["lease_duration"] == 3600


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_bind_api_key_to_group_success() -> None:
    """Test binding an API key to a Cluster Auth group."""
    group_id = "test-group-123"

    with patch("app.apikeys.router.bind_api_key_to_group_in_cluster_auth") as mock_service:
        mock_service.return_value = {"groups": [group_id]}
        with TestClient(app) as client:
            response = client.post(
                f"/v1/namespaces/test-namespace/api-keys/{uuid4()}/bind-group",
                json={"group_id": group_id},
            )

    assert response.status_code == status.HTTP_200_OK
    assert group_id in response.json()["groups"]


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_unbind_api_key_from_group_success() -> None:
    """Test unbinding an API key from a Cluster Auth group."""
    with patch("app.apikeys.router.unbind_api_key_from_group_in_cluster_auth") as mock_service:
        mock_service.return_value = {"groups": []}
        with TestClient(app) as client:
            response = client.post(
                f"/v1/namespaces/test-namespace/api-keys/{uuid4()}/unbind-group",
                json={"group_id": "test-group"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["groups"]) == 0


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_create_group_success() -> None:
    """Test creating a Cluster Auth group."""
    expected_group = GroupResponse(id="group-123", name="Test Group")

    with patch("app.apikeys.router.create_group_in_cluster_auth") as mock_service:
        mock_service.return_value = expected_group
        with TestClient(app) as client:
            response = client.post("/v1/api-keys/groups", json={"name": "Test Group", "id": "group-123"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == "group-123"


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_delete_group_success() -> None:
    """Test deleting a Cluster Auth group."""
    with patch("app.apikeys.router.delete_group_from_cluster_auth") as mock_service:
        mock_service.return_value = None
        with TestClient(app) as client:
            response = client.delete("/v1/api-keys/groups/test-group-456")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
def test_update_api_key_bindings_success() -> None:
    """Test updating API key AIM deployment bindings."""
    api_key_id = uuid4()
    mock_updated_key = ApiKeyDetails(
        id=api_key_id,
        name="Updated Key",
        truncated_key="••••••••abcd",
        namespace="test-namespace",
        renewable=True,
        num_uses=0,
        ttl="1h",
        expires_at=None,
        groups=["aim-group-1", "aim-group-2"],
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T01:00:00Z",
        created_by="user@example.com",
        updated_by="user@example.com",
    )

    with patch("app.apikeys.router.update_api_key_bindings_with_cluster_auth") as mock_service:
        mock_service.return_value = mock_updated_key
        with TestClient(app) as client:
            response = client.patch(
                f"/v1/namespaces/test-namespace/api-keys/{api_key_id}",
                json={"aim_ids": [str(uuid4()), str(uuid4())]},
            )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["groups"]) == 2
