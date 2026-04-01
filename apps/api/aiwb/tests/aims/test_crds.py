# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs CRD Pydantic models."""

from app.aims.crds import (
    AIMClusterModelResource,
    AIMClusterModelStatusFields,
    AIMImageMetadata,
    AIMModelMetadata,
    AIMServiceSpec,
    AIMServiceStatusFields,
    HTTPRouteResource,
)
from app.aims.enums import AIMClusterModelStatus, AIMServiceStatus
from tests.factory import make_aim_cluster_model, make_aim_cluster_service_template, make_aim_service_k8s


def test_aim_model_metadata_defaults() -> None:
    """Test AIMModelMetadata defaults."""
    m = AIMModelMetadata()
    assert m.canonical_name is None
    assert m.tags == []


def test_aim_model_metadata_with_values() -> None:
    """Test AIMModelMetadata with values."""
    m = AIMModelMetadata.model_validate(
        {
            "canonicalName": "meta/llama",
            "tags": ["chat"],
            "hfTokenRequired": True,
        }
    )
    assert m.canonical_name == "meta/llama"
    assert m.hf_token_required is True


def test_aim_image_metadata() -> None:
    """Test AIMImageMetadata."""
    m = AIMImageMetadata.model_validate(
        {
            "model": {"canonicalName": "test"},
            "originalLabels": {"key": "value"},
        }
    )
    assert m.model.canonical_name == "test"
    assert m.original_labels == {"key": "value"}


def test_aim_cluster_model_status_defaults() -> None:
    """Test AIMClusterModelStatusFields defaults."""
    s = AIMClusterModelStatusFields()
    assert s.status == AIMClusterModelStatus.NOT_AVAILABLE


def test_aim_cluster_model_resource_with_factory() -> None:
    """Test AIMClusterModelResource using factory."""
    aim = make_aim_cluster_model(name="my-model", image="docker.io/test:v1")

    assert aim.metadata.name == "my-model"
    assert aim.spec.image == "docker.io/test:v1"
    assert aim.status.status == AIMClusterModelStatus.READY
    # Computed fields
    assert aim.resource_name == "my-model"
    assert aim.image_reference == "docker.io/test:v1"
    assert aim.status_value == "Ready"


def test_aim_cluster_model_resource_minimal() -> None:
    """Test parsing minimal AIMClusterModelResource."""
    aim = AIMClusterModelResource.model_validate({"metadata": {"name": "minimal"}})
    assert aim.metadata.name == "minimal"
    assert aim.spec.image == ""
    assert aim.status.status == AIMClusterModelStatus.NOT_AVAILABLE


def test_aim_service_spec_defaults() -> None:
    """Test AIMServiceSpec defaults."""
    s = AIMServiceSpec()
    assert s.replicas == 1
    assert s.min_replicas is None
    assert s.max_replicas is None
    assert s.auto_scaling is None


def test_aim_service_spec_with_scaling() -> None:
    """Test AIMServiceSpec with scaling."""
    s = AIMServiceSpec.model_validate(
        {
            "minReplicas": 2,
            "maxReplicas": 10,
            "autoScaling": {"metrics": []},
            "cacheModel": True,
        }
    )
    assert s.min_replicas == 2
    assert s.max_replicas == 10
    assert s.cache_model is True


def test_aim_service_status_fields() -> None:
    """Test AIMServiceStatusFields."""
    s = AIMServiceStatusFields()
    assert s.status == AIMServiceStatus.PENDING

    s2 = AIMServiceStatusFields.model_validate(
        {
            "status": "Running",
            "routing": {"path": "/v1/chat"},
        }
    )
    assert s2.status == AIMServiceStatus.RUNNING
    assert s2.routing["path"] == "/v1/chat"


def test_aim_service_resource_with_factory() -> None:
    """Test AIMServiceResource using factory."""
    svc = make_aim_service_k8s(
        namespace="my-ns",
        model_ref="llama3-8b",
        replicas=2,
        status=AIMServiceStatus.RUNNING,
    )

    assert svc.metadata.namespace == "my-ns"
    assert svc.spec.model["name"] == "llama3-8b"
    assert svc.spec.replicas == 2
    assert svc.status.status == AIMServiceStatus.RUNNING
    assert svc.id is not None  # Computed from label
    assert svc.resource_name == svc.metadata.name


def test_aim_service_resource_with_scaling() -> None:
    """Test AIMServiceResource with scaling policy."""
    svc = make_aim_service_k8s(min_replicas=2, max_replicas=10, auto_scaling={"metrics": []})

    assert svc.spec.min_replicas == 2
    assert svc.spec.max_replicas == 10


def test_aim_cluster_service_template_with_factory() -> None:
    """Test AIMClusterServiceTemplateResource using factory."""
    t = make_aim_cluster_service_template(name="my-template", model_name="llama", metric="throughput")

    assert t.metadata.name == "my-template"
    assert t.spec["modelName"] == "llama"
    assert t.spec["metric"] == "throughput"


def test_httproute_resource_from_dict() -> None:
    """Test HTTPRouteResource parsing from Kubernetes API dict."""
    route_dict = {
        "metadata": {"name": "my-route", "namespace": "test-ns"},
        "spec": {
            "rules": [
                {
                    "backendRefs": [{"kind": "Service", "name": "my-svc-predictor", "port": 80}],
                    "matches": [{"path": {"type": "PathPrefix", "value": "/v1/chat"}}],
                }
            ]
        },
    }
    route = HTTPRouteResource.model_validate(route_dict)
    assert route.metadata.name == "my-route"
    assert route.spec.rules[0].backend_refs[0].name == "my-svc-predictor"
