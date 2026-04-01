# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for secrets gateway layer."""

from unittest.mock import MagicMock

import pytest
from kubernetes_asyncio.client import ApiException, V1ObjectMeta, V1Secret

from app.config import SUBMITTER_ANNOTATION
from app.secrets.constants import USE_CASE_LABEL
from app.secrets.enums import SecretUseCase
from app.secrets.gateway import create_kubernetes_secret, list_kubernetes_secrets


@pytest.mark.asyncio
async def test_list_kubernetes_secrets(mock_kube_api_client: MagicMock) -> None:
    """Test listing native Kubernetes Secrets in a namespace."""
    # Create mock V1Secret objects
    mock_secret_1 = MagicMock()
    mock_secret_1.metadata.name = "k8s-secret-1"
    mock_secret_1.metadata.namespace = "test-ns"
    mock_secret_1.metadata.labels = {
        USE_CASE_LABEL: "HuggingFace",
    }
    mock_secret_1.metadata.annotations = {"note": "test annotation"}
    mock_secret_1.metadata.creation_timestamp = "2025-01-01T00:00:00Z"
    mock_secret_1.metadata.owner_references = []

    mock_secret_2 = MagicMock()
    mock_secret_2.metadata.name = "k8s-secret-2"
    mock_secret_2.metadata.namespace = "test-ns"
    mock_secret_2.metadata.labels = {}
    mock_secret_2.metadata.annotations = None
    mock_secret_2.metadata.creation_timestamp = "2025-01-01T00:00:00Z"
    mock_secret_2.metadata.owner_references = []

    mock_list_response = MagicMock()
    mock_list_response.items = [mock_secret_1, mock_secret_2]

    # Set the async return value
    mock_kube_api_client.core_v1.list_namespaced_secret.return_value = mock_list_response

    result = await list_kubernetes_secrets(
        kube_client=mock_kube_api_client,
        namespace="test-ns",
    )

    # Verify the K8s API was called correctly
    mock_kube_api_client.core_v1.list_namespaced_secret.assert_awaited_once_with(
        namespace="test-ns",
    )

    # Verify results
    assert len(result) == 2
    assert result[0].metadata.name == "k8s-secret-1"
    assert result[1].metadata.name == "k8s-secret-2"


@pytest.mark.asyncio
async def test_list_kubernetes_secrets_empty_namespace(mock_kube_api_client: MagicMock) -> None:
    """Test listing Kubernetes Secrets in a namespace with no secrets."""
    mock_list_response = MagicMock()
    mock_list_response.items = []

    mock_kube_api_client.core_v1.list_namespaced_secret.return_value = mock_list_response

    result = await list_kubernetes_secrets(
        kube_client=mock_kube_api_client,
        namespace="empty-ns",
    )

    assert len(result) == 0


@pytest.mark.asyncio
async def test_list_kubernetes_secrets_api_error(mock_kube_api_client: MagicMock) -> None:
    """Test listing Kubernetes Secrets with API error."""
    # Simulate API error
    mock_kube_api_client.core_v1.list_namespaced_secret.side_effect = ApiException(status=500)

    result = await list_kubernetes_secrets(
        kube_client=mock_kube_api_client,
        namespace="test-ns",
    )

    # Should return empty list on error
    assert len(result) == 0


@pytest.mark.asyncio
async def test_list_kubernetes_secrets_invalid_item_skipped(mock_kube_api_client: MagicMock) -> None:
    """Test that invalid Kubernetes Secret items are skipped with warning."""
    # Create mock secrets
    valid_secret = MagicMock()
    valid_secret.metadata.name = "valid-secret"
    valid_secret.metadata.namespace = "test-ns"
    valid_secret.metadata.labels = {}
    valid_secret.metadata.annotations = {}
    valid_secret.metadata.creation_timestamp = "2025-01-01T00:00:00Z"
    valid_secret.metadata.owner_references = []

    # Invalid secret - will fail validation
    invalid_secret = MagicMock()
    invalid_secret.metadata.name = None  # Invalid name
    invalid_secret.metadata.namespace = "test-ns"
    invalid_secret.metadata.labels = {}
    invalid_secret.metadata.annotations = {}
    invalid_secret.metadata.creation_timestamp = "2025-01-01T00:00:00Z"
    invalid_secret.metadata.owner_references = []

    mock_list_response = MagicMock()
    mock_list_response.items = [valid_secret, invalid_secret]

    mock_kube_api_client.core_v1.list_namespaced_secret.return_value = mock_list_response

    result = await list_kubernetes_secrets(
        kube_client=mock_kube_api_client,
        namespace="test-ns",
    )

    # Should only return valid secret, invalid one is skipped
    assert len(result) == 1
    assert result[0].metadata.name == "valid-secret"


@pytest.mark.asyncio
async def test_list_kubernetes_secrets_with_none_labels_and_annotations(mock_kube_api_client: MagicMock) -> None:
    """Test listing secrets where labels and annotations are None."""
    mock_secret = MagicMock()
    mock_secret.metadata.name = "secret-no-labels"
    mock_secret.metadata.namespace = "test-ns"
    mock_secret.metadata.labels = None  # None instead of empty dict
    mock_secret.metadata.annotations = None  # None instead of empty dict
    mock_secret.metadata.creation_timestamp = "2025-01-01T00:00:00Z"
    mock_secret.metadata.owner_references = []

    mock_list_response = MagicMock()
    mock_list_response.items = [mock_secret]

    mock_kube_api_client.core_v1.list_namespaced_secret.return_value = mock_list_response

    result = await list_kubernetes_secrets(
        kube_client=mock_kube_api_client,
        namespace="test-ns",
    )

    # Should convert None to empty dicts
    assert len(result) == 1
    assert result[0].metadata.labels == {}
    assert result[0].metadata.annotations == {}


@pytest.mark.asyncio
async def test_create_kubernetes_secret_sets_created_by_annotation(mock_kube_api_client: MagicMock) -> None:
    """Test creating a secret with created_by sets aiwb created-by annotation."""
    created_secret = V1Secret(
        metadata=V1ObjectMeta(
            name="my-secret",
            namespace="test-ns",
            labels={USE_CASE_LABEL: SecretUseCase.HUGGING_FACE.value},
            annotations={SUBMITTER_ANNOTATION: "user@example.com"},
        ),
        data={"token": "base64value"},
    )
    mock_kube_api_client.core_v1.create_namespaced_secret.return_value = created_secret

    result = await create_kubernetes_secret(
        kube_client=mock_kube_api_client,
        namespace="test-ns",
        name="my-secret",
        data={"token": "base64value"},
        use_case=SecretUseCase.HUGGING_FACE,
        submitter="user@example.com",
    )

    call_args = mock_kube_api_client.core_v1.create_namespaced_secret.call_args
    body = call_args.kwargs["body"]
    assert body.metadata.annotations.get(SUBMITTER_ANNOTATION) == "user@example.com"
    assert body.metadata.labels.get(USE_CASE_LABEL) == SecretUseCase.HUGGING_FACE.value
    assert result.metadata.name == "my-secret"
