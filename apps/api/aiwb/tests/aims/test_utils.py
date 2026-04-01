# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs utils module."""

from app.aims.crds import (
    HTTPRouteBackendRef,
    HTTPRouteMatch,
    HTTPRoutePathMatch,
    HTTPRouteResource,
    HTTPRouteRule,
    HTTPRouteSpec,
)
from app.aims.enums import OptimizationMetric
from app.aims.schemas import AIMDeployRequest
from app.aims.utils import (
    extract_endpoints,
    generate_aim_service_manifest,
    generate_aim_service_name,
)
from app.dispatch.crds import K8sMetadata
from tests.factory import make_aim_cluster_model, make_aim_service_k8s, make_httproute


def test_generate_aim_service_name() -> None:
    """Test name generation is consistent and has correct format."""
    name1 = generate_aim_service_name("12345678-1234-5678-1234-567812345678")
    name2 = generate_aim_service_name("12345678-1234-5678-1234-567812345678")

    assert name1 == name2
    assert name1.startswith("wb-aim-")
    assert len(name1) == 15


def test_extract_endpoints_both_urls() -> None:
    """Test extraction of both internal and external URLs from HTTPRoute."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns", with_httproute=True)

    endpoints = extract_endpoints(svc, httproute=svc.httproute, cluster_host="https://cluster.example.com")
    assert "internal" in endpoints
    assert "external" in endpoints
    assert endpoints["internal"].startswith("http://my-svc-predictor.my-ns.svc.cluster.local")
    assert endpoints["external"].startswith("https://cluster.example.com/my-ns/")


def test_extract_endpoints_with_custom_port() -> None:
    """Test internal URL includes port when not 80."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns")
    httproute = make_httproute(namespace="my-ns", service_name="my-svc-predictor", port=8080)

    endpoints = extract_endpoints(svc, httproute=httproute)
    assert endpoints["internal"] == "http://my-svc-predictor.my-ns.svc.cluster.local:8080"


def test_extract_endpoints_adds_https_protocol() -> None:
    """Test adds https:// when cluster_host lacks protocol."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns", with_httproute=True)

    endpoints = extract_endpoints(svc, httproute=svc.httproute, cluster_host="cluster.example.com")
    assert endpoints["external"].startswith("https://")


def test_extract_endpoints_no_path_match() -> None:
    """Test returns only internal URL when no PathPrefix match found."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns")
    httproute = HTTPRouteResource(
        metadata=K8sMetadata(name="my-route", namespace="my-ns"),
        spec=HTTPRouteSpec(
            rules=[
                HTTPRouteRule(
                    backend_refs=[HTTPRouteBackendRef(kind="Service", name="my-svc-predictor", port=80)],
                    matches=[
                        HTTPRouteMatch(
                            path=HTTPRoutePathMatch(type="Exact", value="/my-ns/12345678-1234-5678-1234-567812345678")
                        )
                    ],
                )
            ]
        ),
    )

    endpoints = extract_endpoints(svc, httproute=httproute, cluster_host="https://cluster.example.com")
    assert endpoints["internal"] == "http://my-svc-predictor.my-ns.svc.cluster.local"
    assert "external" not in endpoints


def test_extract_endpoints_no_httproute_with_isvc() -> None:
    """Test derives internal URL from InferenceService name when HTTPRoute is missing."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns")
    endpoints = extract_endpoints(svc, httproute=None, inference_service_name="my-svc-a1b2c3")
    assert endpoints == {"internal": "http://my-svc-a1b2c3-predictor.my-ns.svc.cluster.local"}
    assert "external" not in endpoints


def test_extract_endpoints_no_httproute_no_isvc() -> None:
    """Test returns no internal URL when neither HTTPRoute nor InferenceService is available."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns")
    endpoints = extract_endpoints(svc, httproute=None, inference_service_name=None)
    assert "internal" not in endpoints
    assert "external" not in endpoints


def test_extract_endpoints_no_rules() -> None:
    """Test falls back to InferenceService name when HTTPRoute has no rules."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns")
    httproute = HTTPRouteResource(
        metadata=K8sMetadata(name="my-route", namespace="my-ns"), spec=HTTPRouteSpec(rules=[])
    )

    endpoints = extract_endpoints(svc, httproute=httproute, inference_service_name="my-svc-x9y8z7")
    assert endpoints["internal"] == "http://my-svc-x9y8z7-predictor.my-ns.svc.cluster.local"
    assert "external" not in endpoints


def test_extract_endpoints_no_service_backend() -> None:
    """Test falls back to InferenceService name when no Service backend found."""
    svc = make_aim_service_k8s(name="my-svc", namespace="my-ns")
    httproute = HTTPRouteResource(
        metadata=K8sMetadata(name="my-route", namespace="my-ns"),
        spec=HTTPRouteSpec(rules=[HTTPRouteRule(backend_refs=[HTTPRouteBackendRef(kind="Other", name="other")])]),
    )

    endpoints = extract_endpoints(svc, httproute=httproute, inference_service_name="my-svc-x9y8z7")
    assert endpoints["internal"] == "http://my-svc-x9y8z7-predictor.my-ns.svc.cluster.local"
    assert "external" not in endpoints


def test_generate_aim_service_manifest_basic() -> None:
    """Test basic manifest generation."""
    aim = make_aim_cluster_model(name="llama3-8b")
    req = AIMDeployRequest(model="llama3-8b", replicas=2)

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="test-ns",
        service_name="wb-aim-12345678",
        api_version="aims.amd.com/v1alpha1",
        submitter="test@example.com",
        cluster_auth_group_id="group-123",
    )

    assert manifest["apiVersion"] == "aims.amd.com/v1alpha1"
    assert manifest["kind"] == "AIMService"
    assert manifest["metadata"]["namespace"] == "test-ns"
    assert manifest["spec"]["replicas"] == 2
    assert manifest["spec"]["model"]["name"] == "llama3-8b"
    assert manifest["spec"]["routing"]["annotations"]["cluster-auth/allowed-group"] == "group-123"


def test_generate_aim_service_manifest_with_metric() -> None:
    """Test manifest with metric override."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="img", metric=OptimizationMetric.LATENCY)

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert manifest["spec"]["overrides"]["metric"] == "latency"


def test_generate_aim_service_manifest_with_hf_token() -> None:
    """Test manifest includes env with HF_TOKEN when hf_token is provided."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="img", hf_token="my-hf-secret")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert "env" in manifest["spec"]
    assert len(manifest["spec"]["env"]) == 1
    assert manifest["spec"]["env"][0]["name"] == "HF_TOKEN"
    assert manifest["spec"]["env"][0]["valueFrom"]["secretKeyRef"]["name"] == "my-hf-secret"
    assert manifest["spec"]["env"][0]["valueFrom"]["secretKeyRef"]["key"] == "token"


def test_generate_aim_service_manifest_with_image_pull_secrets() -> None:
    """Test manifest includes imagePullSecrets when image_pull_secrets is provided."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="meta-llama-3-8b", image_pull_secrets=["secret1", "secret2"])

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert "imagePullSecrets" in manifest["spec"]
    assert len(manifest["spec"]["imagePullSecrets"]) == 2
    assert manifest["spec"]["imagePullSecrets"][0]["name"] == "secret1"
    assert manifest["spec"]["imagePullSecrets"][1]["name"] == "secret2"


def test_generate_aim_service_manifest_with_scaling() -> None:
    """Test manifest with scaling policy."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="llama3-8b",
        min_replicas=2,
        max_replicas=10,
        auto_scaling={"metrics": [{"type": "PodMetric"}]},
    )

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert manifest["spec"]["minReplicas"] == 2
    assert manifest["spec"]["maxReplicas"] == 10
    assert "autoScaling" in manifest["spec"]


def test_generate_aim_service_manifest_with_allow_unoptimized() -> None:
    """Test manifest has template.allowUnoptimized in camelCase."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", allow_unoptimized=True)

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert "template" in manifest["spec"]
    assert manifest["spec"]["template"]["allowUnoptimized"] is True


def test_generate_aim_service_manifest_camelcase_keys_to_cluster() -> None:
    """Test manifest sent to cluster uses camelCase for imagePullSecrets, allowUnoptimized, autoScaling."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="llama3-8b",
        image_pull_secrets=["s1"],
        allow_unoptimized=True,
        min_replicas=1,
        max_replicas=5,
        auto_scaling={"metrics": []},
    )

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    spec = manifest["spec"]
    assert "imagePullSecrets" in spec
    assert spec["imagePullSecrets"][0]["name"] == "s1"
    assert spec["template"]["allowUnoptimized"] is True
    assert spec["minReplicas"] == 1
    assert spec["maxReplicas"] == 5
    assert "autoScaling" in spec


def test_generate_aim_service_manifest_with_cluster_auth_group() -> None:
    """Test manifest includes cluster-auth annotation in routing."""
    aim = make_aim_cluster_model(name="llama3-8b")
    req = AIMDeployRequest(model="llama3-8b")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="group-123",
    )

    assert "routing" in manifest["spec"]
    assert "annotations" in manifest["spec"]["routing"]
    assert manifest["spec"]["routing"]["annotations"]["cluster-auth/allowed-group"] == "group-123"


def test_generate_aim_service_manifest_includes_workload_type_label() -> None:
    """Test manifest includes workload-type label (but not workload-id or component-id)."""
    aim = make_aim_cluster_model(name="llama3-8b")
    req = AIMDeployRequest(model="llama3-8b")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-12345678",
        api_version="v1",
        submitter="test@example.com",
        cluster_auth_group_id="group-123",
    )

    assert "labels" in manifest["metadata"]
    assert manifest["metadata"]["labels"]["airm.silogen.ai/workload-type"] == "INFERENCE"
    # workload-id and component-id labels are NOT included as they added by Kyverno/AIRM when deployed to the cluster
    assert "airm.silogen.ai/workload-id" not in manifest["metadata"]["labels"]
    assert "airm.silogen.ai/component-id" not in manifest["metadata"]["labels"]
