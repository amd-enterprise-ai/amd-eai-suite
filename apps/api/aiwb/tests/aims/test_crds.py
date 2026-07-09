# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs CRD Pydantic models."""

from app.aims.crds import (
    AIMImageMetadata,
    AIMModelMetadata,
    AIMModelResource,
    AIMModelStatusFields,
    AIMServiceResource,
    AIMServiceSpec,
    AIMServiceStatusFields,
    CachingConfig,
    HTTPRouteResource,
    ResolvedRef,
)
from app.aims.enums import AIMModelStatus, AIMServiceStatus
from app.dispatch.crds import K8sMetadata
from tests.factory import make_aim_cluster_model, make_aim_cluster_profile, make_aim_service_k8s


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
            "model": {"canonicalName": "test", "descriptionFull": "A full description"},
            "oci": {"description": "Short desc", "version": "1.0"},
        }
    )
    assert m.model.canonical_name == "test"
    assert m.model.description_full == "A full description"
    assert m.oci.description == "Short desc"
    assert m.oci.version == "1.0"


def test_aim_model_status_defaults() -> None:
    """Test AIMModelStatusFields defaults."""
    s = AIMModelStatusFields()
    assert s.status == AIMModelStatus.NOT_AVAILABLE


def test_aim_cluster_model_resource_with_factory() -> None:
    """Test AIMModelResource using factory."""
    aim = make_aim_cluster_model(name="my-model", image="docker.io/test:v1")

    assert aim.metadata.name == "my-model"
    assert aim.spec.image == "docker.io/test:v1"
    assert aim.status.status == AIMModelStatus.READY


def test_aim_cluster_model_resource_minimal() -> None:
    """Test parsing minimal AIMModelResource."""
    aim = AIMModelResource.model_validate({"metadata": {"name": "minimal"}})
    assert aim.metadata.name == "minimal"
    assert aim.spec.image == ""
    assert aim.status.status == AIMModelStatus.NOT_AVAILABLE


def test_aim_model_status_includes_failure_class_variants() -> None:
    """Both ``Failed`` and ``Error`` are recognized failure-class statuses.

    The engine emits ``Failed`` for terminal failures. ``Error`` is a parallel
    failure-class status defensively recognized so Pydantic does not reject the
    whole CR if aim-engine ever emits it.
    """
    assert AIMModelStatus("Failed") is AIMModelStatus.FAILED
    assert AIMModelStatus("Error") is AIMModelStatus.ERROR


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
        }
    )
    assert s.min_replicas == 2
    assert s.max_replicas == 10


def test_aim_service_spec_caching_default() -> None:
    """AIMServiceSpec defaults caching.mode to Shared (v1alpha2 baseline that replaces cacheModel=true)."""
    s = AIMServiceSpec()
    assert isinstance(s.caching, CachingConfig)
    assert s.caching.mode == "Shared"


def test_aim_service_spec_caching_explicit() -> None:
    """AIMServiceSpec accepts an explicit caching config and exposes it on the model."""
    s = AIMServiceSpec.model_validate({"caching": {"mode": "None"}})
    assert s.caching.mode == "None"


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


def test_aim_service_resource_with_scaling() -> None:
    """Test AIMServiceResource with scaling policy."""
    svc = make_aim_service_k8s(min_replicas=2, max_replicas=10, auto_scaling={"metrics": []})

    assert svc.spec.min_replicas == 2
    assert svc.spec.max_replicas == 10


def test_aim_service_resource_backfills_model_name_from_resolved_model() -> None:
    """Legacy v1alpha1 deploy-by-image services have spec.model.name empty;
    the engine resolves the image and writes the AIMClusterModel resource name
    to status.resolvedModel.name. The validator backfills spec.model.name so
    FE consumers can always read it directly. TODO(EAI-6783) — drop when
    v1alpha1 is removed."""
    svc = AIMServiceResource(
        metadata=K8sMetadata(name="svc", namespace="ns"),
        spec=AIMServiceSpec.model_validate({"model": {"image": "amd/aim:0.8.5"}}),
        status=AIMServiceStatusFields(
            resolved_model=ResolvedRef(name="amd-aim-resource-name", scope="Cluster"),
        ),
    )

    assert svc.spec.model["name"] == "amd-aim-resource-name"
    # status is left untouched so engine-written data remains diagnosable.
    assert svc.status.resolved_model is not None
    assert svc.status.resolved_model.name == "amd-aim-resource-name"


def test_aim_service_resource_backfill_no_op_when_spec_name_set() -> None:
    """When spec.model.name is already set the validator leaves it alone,
    even if status.resolvedModel.name differs (e.g. v1alpha2 profile pipeline
    writes the canonical model id there, not a resource name)."""
    svc = AIMServiceResource(
        metadata=K8sMetadata(name="svc", namespace="ns"),
        spec=AIMServiceSpec.model_validate({"model": {"name": "amd-aim-resource-name"}}),
        status=AIMServiceStatusFields(
            resolved_model=ResolvedRef(name="amd/Llama-3.1-8B", scope="Cluster"),
        ),
    )

    assert svc.spec.model["name"] == "amd-aim-resource-name"


def test_aim_service_resource_backfill_no_op_when_resolved_model_missing() -> None:
    """When neither spec.model.name nor status.resolvedModel is set (pending
    reconcile), the validator leaves spec.model.name unset."""
    svc = AIMServiceResource(
        metadata=K8sMetadata(name="svc", namespace="ns"),
        spec=AIMServiceSpec.model_validate({"model": {"image": "amd/aim:0.8.5"}}),
        status=AIMServiceStatusFields(resolved_model=None),
    )

    assert svc.spec.model.get("name") is None


def test_aim_cluster_profile_with_factory() -> None:
    """Test AIMProfileResource using factory (v1alpha2)."""
    profile = make_aim_cluster_profile(name="my-profile", aim_id="org/llama", metric="throughput")

    assert profile.metadata.name == "my-profile"
    assert profile.spec.aim_id == "org/llama"
    assert profile.spec.metric == "throughput"


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
