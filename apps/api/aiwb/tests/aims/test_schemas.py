# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs Pydantic schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.aims.enums import AIMServiceStatus, OptimizationMetric
from app.aims.schemas import (
    AIMDeployRequest,
    AIMServiceHistoryResponse,
    AIMServicePatchRequest,
)
from tests.factory import make_aim_service_k8s


def test_aim_deploy_request_defaults() -> None:
    """Test AIMDeployRequest defaults."""
    r = AIMDeployRequest(model="meta-llama-3-8b")
    assert r.replicas == 1
    assert r.metric is None
    assert r.allow_unoptimized is False
    assert r.min_replicas is None


def test_aim_deploy_request_with_resource_name() -> None:
    """Test AIMDeployRequest with model as resource_name."""
    r = AIMDeployRequest(model="my-aim-model")
    assert r.model == "my-aim-model"
    assert r.replicas == 1


def test_aim_deploy_request_with_all_fields() -> None:
    """Test AIMDeployRequest with all fields."""
    r = AIMDeployRequest(
        model="docker.io/amd/model:v1",
        replicas=4,
        metric=OptimizationMetric.LATENCY,
        image_pull_secrets=["secret1"],
        hf_token="hf_token",
        allow_unoptimized=True,
    )
    assert r.replicas == 4
    assert r.metric == OptimizationMetric.LATENCY
    assert r.allow_unoptimized is True


def test_aim_deploy_request_parses_camelcase_input() -> None:
    """Test AIMDeployRequest accepts camelCase keys from API/UI payload."""
    r = AIMDeployRequest(
        model="meta-llama-3-8b",
        imagePullSecrets=["secret1", "secret2"],
        hfToken="hf_secret_name",
        allowUnoptimized=True,
        minReplicas=2,
        maxReplicas=10,
        autoScaling={"metrics": []},
    )
    assert r.image_pull_secrets == ["secret1", "secret2"]
    assert r.hf_token == "hf_secret_name"
    assert r.allow_unoptimized is True
    assert r.min_replicas == 2
    assert r.max_replicas == 10
    assert r.auto_scaling == {"metrics": []}


def test_aim_deploy_request_with_scaling() -> None:
    """Test AIMDeployRequest with scaling policy."""
    r = AIMDeployRequest(
        model="img",
        min_replicas=2,
        max_replicas=10,
        auto_scaling={"metrics": []},
    )
    assert r.min_replicas == 2
    assert r.max_replicas == 10


def test_aim_deploy_request_partial_scaling_fails() -> None:
    """Test partial scaling policy validation."""
    with pytest.raises(ValueError, match="Autoscaling requires all three fields"):
        AIMDeployRequest(model="img", min_replicas=2)

    with pytest.raises(ValueError, match="Autoscaling requires all three fields"):
        AIMDeployRequest(model="img", min_replicas=2, max_replicas=10)


def test_aim_deploy_request_max_gte_min() -> None:
    """Test max_replicas >= min_replicas validation."""
    with pytest.raises(ValueError, match="maxReplicas .* must be >= minReplicas"):
        AIMDeployRequest(model="img", min_replicas=10, max_replicas=5, auto_scaling={"metrics": []})
    with pytest.raises(ValueError, match="autoScaling cannot be empty"):
        AIMDeployRequest(model="img", min_replicas=1, max_replicas=5, auto_scaling={})


def test_aim_service_patch_request_empty() -> None:
    """Test empty patch request is valid."""
    r = AIMServicePatchRequest()
    assert r.min_replicas is None


def test_aim_service_patch_request_with_scaling() -> None:
    """Test patch request with scaling."""
    r = AIMServicePatchRequest(min_replicas=1, max_replicas=5, auto_scaling={"metrics": []})
    assert r.min_replicas == 1


def test_aim_service_patch_request_camelcase() -> None:
    """Test camelCase aliases."""
    r = AIMServicePatchRequest(**{"minReplicas": 3, "maxReplicas": 10, "autoScaling": {"metrics": []}})
    assert r.min_replicas == 3


def test_aim_service_patch_request_partial_fails() -> None:
    """Test partial scaling policy fails."""
    with pytest.raises(ValueError, match="Autoscaling requires all three fields"):
        AIMServicePatchRequest(min_replicas=2, max_replicas=10)


def test_aim_service_patch_request_min_replicas_validation() -> None:
    """Test min_replicas >= 1."""
    with pytest.raises(ValueError):
        AIMServicePatchRequest(min_replicas=0, max_replicas=10, auto_scaling={"metrics": []})


def test_aim_service_patch_request_max_gte_min() -> None:
    """Test max >= min validation."""
    with pytest.raises(ValueError, match="maxReplicas .* must be >= minReplicas"):
        AIMServicePatchRequest(min_replicas=10, max_replicas=5, auto_scaling={"metrics": []})


def test_aim_service_history_response() -> None:
    """Test AIMServiceHistoryResponse."""
    now = datetime.now(UTC)
    r = AIMServiceHistoryResponse.model_validate(
        {
            "id": str(uuid4()),
            "model": "llama3-8b",
            "status": "Running",
            "metric": "latency",
            "created_at": now,
            "updated_at": now,
            "created_by": "test@example.com",
            "updated_by": "test@example.com",
        }
    )
    assert r.model == "llama3-8b"
    assert r.metric == OptimizationMetric.LATENCY


def test_aim_service_response_endpoints_with_httproute() -> None:
    """Test that AIMServiceResponse.endpoints returns proper values when httproute is present."""
    svc = make_aim_service_k8s(
        name="test-aim",
        namespace="default",
        status=AIMServiceStatus.RUNNING,
        with_httproute=True,
        as_response=True,
    )

    # Check endpoints are populated
    assert svc.endpoints != {}
    assert "internal" in svc.endpoints
    assert "external" in svc.endpoints
    assert svc.endpoints["internal"] == "http://test-aim-predictor.default.svc.cluster.local"
    # External URL uses default CLUSTER_HOST (http://localhost:8080)
    assert svc.endpoints["external"].startswith("http://localhost:8080/default/")


def test_aim_service_response_endpoints_empty_when_not_running() -> None:
    """Test that endpoints are empty when AIMService is not RUNNING."""
    svc = make_aim_service_k8s(
        name="test-aim",
        namespace="default",
        status=AIMServiceStatus.PENDING,
        with_httproute=True,
        as_response=True,
    )

    assert svc.endpoints == {}


def test_aim_service_response_cluster_auth_group_id_present() -> None:
    """Test that cluster_auth_group_id is extracted from routing annotations."""
    svc = make_aim_service_k8s(
        name="test-aim",
        namespace="default",
        status=AIMServiceStatus.RUNNING,
        as_response=True,
    )
    svc.spec.routing = {"annotations": {"cluster-auth/allowed-group": "group-123"}}

    assert svc.cluster_auth_group_id == "group-123"


def test_aim_service_response_cluster_auth_group_id_absent() -> None:
    """Test that cluster_auth_group_id is None when annotation is absent."""
    svc = make_aim_service_k8s(
        name="test-aim",
        namespace="default",
        status=AIMServiceStatus.RUNNING,
        as_response=True,
    )
    svc.spec.routing = {}

    assert svc.cluster_auth_group_id is None
