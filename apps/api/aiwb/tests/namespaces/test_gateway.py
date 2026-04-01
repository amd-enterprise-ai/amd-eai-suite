# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from kubernetes_asyncio.client import ApiException
from kubernetes_asyncio.client.models import V1NamespaceList

from app.namespaces.gateway import get_namespace, get_namespaces
from tests.factory import make_namespace_k8s


@pytest.mark.asyncio
async def test_get_namespaces_success(mock_kube_api_client: MagicMock) -> None:
    """Test successful listing of namespaces."""
    mock_ns_1 = make_namespace_k8s(
        name="namespace-1",
        labels={"env": "prod"},
        annotations={"note": "production"},
        created_at=datetime(2025, 1, 1, 0, 0, 0),
    )

    mock_ns_2 = make_namespace_k8s(
        name="namespace-2",
        created_at=datetime(2025, 1, 2, 0, 0, 0),
    )

    mock_list_response = MagicMock(spec=V1NamespaceList)
    mock_list_response.items = [mock_ns_1, mock_ns_2]

    mock_kube_api_client.core_v1.list_namespace = AsyncMock(return_value=mock_list_response)

    result = await get_namespaces(kube_client=mock_kube_api_client)

    mock_kube_api_client.core_v1.list_namespace.assert_awaited_once()

    expected_namespace_count = 2
    assert len(result) == expected_namespace_count
    assert result[0].name == "namespace-1"
    assert result[0].labels == {"env": "prod", "airm.silogen.ai/project-id": "test-project-id"}
    assert result[0].annotations == {"note": "production"}
    assert result[0].created_at == datetime(2025, 1, 1, 0, 0, 0)
    assert result[1].name == "namespace-2"
    assert result[1].labels == {"airm.silogen.ai/project-id": "test-project-id"}
    assert result[1].annotations == {}


@pytest.mark.asyncio
async def test_get_namespaces_empty(mock_kube_api_client: MagicMock) -> None:
    """Test listing namespaces when none exist."""
    mock_list_response = MagicMock(spec=V1NamespaceList)
    mock_list_response.items = []

    mock_kube_api_client.core_v1.list_namespace = AsyncMock(return_value=mock_list_response)

    result = await get_namespaces(kube_client=mock_kube_api_client)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_namespaces_handles_none_labels_annotations(mock_kube_api_client: MagicMock) -> None:
    """Test that None labels and annotations are converted to empty dicts."""
    mock_ns = make_namespace_k8s(
        name="test-namespace",
        labels=None,
        annotations=None,
        created_at=datetime(2025, 1, 1, 0, 0, 0),
        project_id=None,
    )
    # Override None values after creation to test handling
    mock_ns.metadata.labels = None
    mock_ns.metadata.annotations = None

    mock_list_response = MagicMock(spec=V1NamespaceList)
    mock_list_response.items = [mock_ns]

    mock_kube_api_client.core_v1.list_namespace = AsyncMock(return_value=mock_list_response)

    result = await get_namespaces(kube_client=mock_kube_api_client)

    assert len(result) == 1
    assert result[0].labels == {}
    assert result[0].annotations == {}


@pytest.mark.asyncio
async def test_get_namespace_found(mock_kube_api_client: MagicMock) -> None:
    """Test retrieving a specific namespace that exists."""
    mock_ns = make_namespace_k8s(
        name="test-namespace",
        labels={"team": "platform"},
        annotations={"owner": "admin@example.com"},
        created_at=datetime(2025, 1, 1, 12, 0, 0),
    )

    mock_kube_api_client.core_v1.read_namespace = AsyncMock(return_value=mock_ns)

    result = await get_namespace(kube_client=mock_kube_api_client, name="test-namespace")

    mock_kube_api_client.core_v1.read_namespace.assert_awaited_once_with("test-namespace")

    assert result is not None
    assert result.name == "test-namespace"
    assert result.labels == {"team": "platform", "airm.silogen.ai/project-id": "test-project-id"}
    assert result.annotations == {"owner": "admin@example.com"}
    assert result.created_at == datetime(2025, 1, 1, 12, 0, 0)


@pytest.mark.asyncio
async def test_get_namespace_not_found(mock_kube_api_client: MagicMock) -> None:
    """Test retrieving a namespace that doesn't exist returns None."""
    mock_kube_api_client.core_v1.read_namespace = AsyncMock(side_effect=ApiException(status=404))

    result = await get_namespace(kube_client=mock_kube_api_client, name="nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_get_namespace_api_error_raises(mock_kube_api_client: MagicMock) -> None:
    """Test that non-404 API errors are re-raised."""
    mock_kube_api_client.core_v1.read_namespace = AsyncMock(side_effect=ApiException(status=500))

    with pytest.raises(ApiException) as exc_info:
        await get_namespace(kube_client=mock_kube_api_client, name="test-namespace")

    assert exc_info.value.status == 500


@pytest.mark.asyncio
async def test_get_namespaces_api_error_raises(mock_kube_api_client: MagicMock) -> None:
    """Test that API errors during list are re-raised."""
    mock_kube_api_client.core_v1.list_namespace = AsyncMock(side_effect=ApiException(status=500))

    with pytest.raises(ApiException) as exc_info:
        await get_namespaces(kube_client=mock_kube_api_client)

    assert exc_info.value.status == 500


@pytest.mark.asyncio
async def test_get_namespace_api_error_401_unauthorized(mock_kube_api_client: MagicMock) -> None:
    """Test that 401 Unauthorized errors are re-raised."""
    mock_kube_api_client.core_v1.read_namespace = AsyncMock(side_effect=ApiException(status=401))

    with pytest.raises(ApiException) as exc_info:
        await get_namespace(kube_client=mock_kube_api_client, name="test-namespace")

    assert exc_info.value.status == 401


@pytest.mark.asyncio
async def test_get_namespace_api_error_403_forbidden(mock_kube_api_client: MagicMock) -> None:
    """Test that 403 Forbidden errors are re-raised."""
    mock_kube_api_client.core_v1.read_namespace = AsyncMock(side_effect=ApiException(status=403))

    with pytest.raises(ApiException) as exc_info:
        await get_namespace(kube_client=mock_kube_api_client, name="test-namespace")

    assert exc_info.value.status == 403
