# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from app import app  # type: ignore[attr-defined]
from app.secrets.crds import K8sMetadata
from app.secrets.schemas import SecretResponse
from tests.dependency_overrides import BASE_OVERRIDES, override_dependencies


@override_dependencies(BASE_OVERRIDES)
def test_get_secrets_success():
    """Test listing secrets for a namespace."""
    mock_namespace = "test-namespace"

    expected_secrets = [
        SecretResponse(
            metadata=K8sMetadata(
                name="huggingface-token",
                namespace=mock_namespace,
                creation_timestamp="2025-01-01T00:00:00Z",
            ),
        )
    ]

    with patch("app.secrets.router.list_secrets_for_namespace") as mock_service:
        mock_service.return_value = expected_secrets
        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/{mock_namespace}/secrets")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["metadata"]["name"] == "huggingface-token"


@override_dependencies(BASE_OVERRIDES)
def test_get_secrets_with_use_case_filter():
    """Test listing secrets filtered by use case."""
    mock_namespace = "test-namespace"

    expected_secrets = [
        SecretResponse(
            metadata=K8sMetadata(
                name="s3-credentials",
                namespace=mock_namespace,
                creation_timestamp="2025-01-01T00:00:00Z",
            ),
        )
    ]

    with patch("app.secrets.router.list_secrets_for_namespace") as mock_service:
        mock_service.return_value = expected_secrets
        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/{mock_namespace}/secrets?use_case=S3")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["metadata"]["name"] == "s3-credentials"


@override_dependencies(BASE_OVERRIDES)
def test_create_secret_success():
    """Test creating a new secret."""
    mock_namespace = "test-namespace"

    expected_response = SecretResponse(
        metadata=K8sMetadata(
            name="new-secret",
            namespace=mock_namespace,
            creation_timestamp="2025-01-01T00:00:00Z",
        ),
    )

    with patch("app.secrets.router.create_secret") as mock_service:
        mock_service.return_value = expected_response
        with TestClient(app) as client:
            response = client.post(
                f"/v1/namespaces/{mock_namespace}/secrets",
                json={
                    "name": "new-secret",
                    "type": "Opaque",
                    "data": {
                        "username": "admin",
                        "password": "secret123",
                    },
                },
            )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["metadata"]["name"] == "new-secret"


@override_dependencies(BASE_OVERRIDES)
def test_get_secret_details_success():
    """Test getting detailed secret information."""
    mock_namespace = "test-namespace"
    secret_name = "detailed-secret"

    expected_details = SecretResponse(
        metadata=K8sMetadata(
            name=secret_name,
            namespace=mock_namespace,
            creation_timestamp="2025-01-01T00:00:00Z",
            labels={"use-case": "HuggingFace"},
            annotations={"description": "Authentication token"},
        ),
    )

    with patch("app.secrets.router.get_secret_details") as mock_service:
        mock_service.return_value = expected_details
        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/{mock_namespace}/secrets/{secret_name}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["metadata"]["name"] == secret_name
    assert data["metadata"]["labels"]["use-case"] == "HuggingFace"


@override_dependencies(BASE_OVERRIDES)
def test_delete_secret_success():
    """Test deleting a secret."""
    mock_namespace = "test-namespace"
    secret_name = "old-secret"

    with patch("app.secrets.router.delete_secret") as mock_service:
        mock_service.return_value = None
        with TestClient(app) as client:
            response = client.delete(f"/v1/namespaces/{mock_namespace}/secrets/{secret_name}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@override_dependencies(BASE_OVERRIDES)
def test_create_secret_with_use_case():
    """Test creating a secret with a use case label."""
    mock_namespace = "test-namespace"

    expected_response = SecretResponse(
        metadata=K8sMetadata(
            name="s3-secret",
            namespace=mock_namespace,
            creation_timestamp="2025-01-01T00:00:00Z",
        ),
    )

    with patch("app.secrets.router.create_secret") as mock_service:
        mock_service.return_value = expected_response
        with TestClient(app) as client:
            response = client.post(
                f"/v1/namespaces/{mock_namespace}/secrets",
                json={
                    "name": "s3-secret",
                    "type": "Opaque",
                    "use_case": "S3",
                    "data": {
                        "accessKey": "AKIAIOSFODNN7EXAMPLE",
                        "secretKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    },
                },
            )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["metadata"]["name"] == "s3-secret"


@override_dependencies(BASE_OVERRIDES)
def test_get_secrets_empty_namespace():
    """Test listing secrets for an empty namespace."""
    mock_namespace = "empty-namespace"

    expected_secrets: list[SecretResponse] = []

    with patch("app.secrets.router.list_secrets_for_namespace") as mock_service:
        mock_service.return_value = expected_secrets
        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/{mock_namespace}/secrets")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 0
