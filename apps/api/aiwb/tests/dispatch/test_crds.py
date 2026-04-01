# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for Kubernetes CRD models."""

from datetime import UTC, datetime

from app.dispatch.crds import K8sListResponse, K8sMetadata


def test_k8s_metadata_creation():
    """Test creating K8sMetadata with required fields."""
    metadata = K8sMetadata(
        name="test-resource",
        namespace="test-namespace",
    )
    assert metadata.name == "test-resource"
    assert metadata.namespace == "test-namespace"
    assert metadata.labels == {}
    assert metadata.annotations == {}


def test_k8s_metadata_with_all_fields():
    """Test creating K8sMetadata with all fields."""
    now = datetime.now(UTC)
    metadata = K8sMetadata(
        name="test-resource",
        namespace="test-namespace",
        uid="abc-123",
        labels={"app": "test", "env": "dev"},
        annotations={"description": "Test resource"},
        creation_timestamp=now,
        owner_references=[{"kind": "Deployment", "name": "test-deploy"}],
    )

    assert metadata.name == "test-resource"
    assert metadata.namespace == "test-namespace"
    assert metadata.uid == "abc-123"
    assert metadata.labels == {"app": "test", "env": "dev"}
    assert metadata.annotations == {"description": "Test resource"}
    assert metadata.creation_timestamp == now
    assert len(metadata.owner_references) == 1


def test_k8s_metadata_with_camel_case_alias():
    """Test K8sMetadata accepts camelCase fields from K8s API."""
    metadata = K8sMetadata.model_validate(
        {
            "name": "test-resource",
            "namespace": "test-namespace",
            "creationTimestamp": "2024-01-01T00:00:00Z",
            "ownerReferences": [{"kind": "Pod", "name": "test-pod"}],
        }
    )

    assert metadata.name == "test-resource"
    assert metadata.creation_timestamp is not None
    assert len(metadata.owner_references) == 1


def test_k8s_list_response_creation():
    """Test creating K8sListResponse."""
    response = K8sListResponse(
        api_version="v1",
        kind="PodList",
        items=[
            {"metadata": {"name": "pod1"}},
            {"metadata": {"name": "pod2"}},
        ],
    )

    assert response.api_version == "v1"
    assert response.kind == "PodList"
    assert len(response.items) == 2
    assert response.metadata == {}


def test_k8s_list_response_with_camel_case():
    """Test K8sListResponse accepts camelCase from K8s API."""
    response = K8sListResponse.model_validate(
        {
            "apiVersion": "v1",
            "kind": "ServiceList",
            "items": [{"metadata": {"name": "svc1"}}],
            "metadata": {"resourceVersion": "12345"},
        }
    )

    assert response.api_version == "v1"
    assert response.kind == "ServiceList"
    assert len(response.items) == 1
    assert response.metadata["resourceVersion"] == "12345"


def test_k8s_list_response_empty_items():
    """Test K8sListResponse with no items."""
    response = K8sListResponse(
        api_version="v1",
        kind="ConfigMapList",
        items=[],
    )

    assert response.api_version == "v1"
    assert response.kind == "ConfigMapList"
    assert response.items == []
