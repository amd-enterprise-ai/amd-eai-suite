# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs utils module."""

import pytest

from api_common.exceptions import ValidationException
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
    generate_fine_tuned_aim_service_manifest,
    generate_namespace_aim_service_manifest,
)
from app.dispatch.crds import K8sMetadata
from app.workloads.constants import CANONICAL_NAME_LABEL, DISPLAY_NAME_ANNOTATION, MODEL_NAME_LABEL
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
        api_version="aims.amd.com/v1alpha2",
        submitter="test@example.com",
        cluster_auth_group_id="group-123",
    )

    assert manifest["apiVersion"] == "aims.amd.com/v1alpha2"
    assert manifest["kind"] == "AIMService"
    assert manifest["metadata"]["namespace"] == "test-ns"
    assert manifest["spec"]["replicas"] == 2
    assert manifest["spec"]["model"]["name"] == "llama3-8b"
    assert manifest["spec"]["routing"]["annotations"]["cluster-auth/allowed-group"] == "group-123"
    # caching.mode replaces the deprecated cacheModel boolean.
    assert manifest["spec"]["caching"]["mode"] == "Shared"
    assert "cacheModel" not in manifest["spec"]
    # Forces the v1alpha2 profile pipeline so status.resolvedProfile lands;
    # EAI-6783 will remove the annotation once aim-engine drops v1alpha1 dispatch.
    assert manifest["metadata"]["annotations"]["aim.eai.amd.com/reconciler-pipeline"] == "profile"


def test_generate_aim_service_manifest_with_metric() -> None:
    """Metric criteria flow into spec.profile.selector (ADR 006b §3)."""
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

    assert "overrides" not in manifest["spec"]
    assert manifest["spec"]["profile"]["selector"] == {"minimumType": "any", "metric": "latency"}


def test_generate_aim_service_manifest_with_hf_token() -> None:
    """HF_TOKEN lands in spec.caching.env, not spec.env, so it reaches the download Job only."""
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

    assert manifest["spec"]["env"] == []
    caching_env = manifest["spec"]["caching"]["env"]
    assert len(caching_env) == 1
    assert caching_env[0]["name"] == "HF_TOKEN"
    assert caching_env[0]["valueFrom"]["secretKeyRef"]["name"] == "my-hf-secret"
    assert caching_env[0]["valueFrom"]["secretKeyRef"]["key"] == "token"


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


def test_generate_aim_service_manifest_auto_via_model() -> None:
    """When profile_name is unset, the manifest emits spec.profile.selector with minimumType=any.

    This allows aim-engine to consider all profile tiers (optimized, preview,
    unoptimized) rather than enforcing the default optimized floor, which would
    fail on clusters that only have unoptimized or preview profiles.
    """
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert manifest["spec"]["model"]["name"] == "llama3-8b"
    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any"}}
    assert "template" not in manifest["spec"]


def test_generate_aim_service_manifest_profile_name_wins_over_selector() -> None:
    """When profile_name is explicit, it takes the direct-reference path:
    spec.profile.name is set and the selector criteria (metric/precision/gpu_model)
    are skipped. gpu_count is independent of selector/profile_name resolution and
    still lands in spec.profileOverrides.acceleratorCount when supplied.
    """
    aim = make_aim_cluster_model(name="llama3-8b")
    req = AIMDeployRequest(
        model="llama3-8b",
        metric=OptimizationMetric.LATENCY,
        precision="fp8",
        gpu_model="MI300X",
        gpu_count=8,
        profile_name="my-explicit-profile",
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

    # ADR 006b: legacy spec.overrides shape must not be emitted by v1alpha2.
    assert "overrides" not in manifest["spec"]
    profile = manifest["spec"]["profile"]
    assert profile == {"name": "my-explicit-profile"}
    # gpu_count is layered on top of the named profile via profileOverrides.
    assert manifest["spec"]["profileOverrides"] == {"acceleratorCount": 8}


def test_generate_aim_service_manifest_selector_only_precision() -> None:
    """Precision alone populates spec.profile.selector with precision and minimumType=any."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", precision="bf16")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert "overrides" not in manifest["spec"]
    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any", "precision": "bf16"}}


def test_generate_aim_service_manifest_gpu_count_alone_emits_minimum_type_selector() -> None:
    """gpu_count is not a selector field — it lives in spec.profileOverrides.

    With only gpu_count set, spec.profile.selector carries minimumType=any (so
    aim-engine considers all profile tiers) and spec.profileOverrides carries
    acceleratorCount as a per-service override on top of the resolved profile.
    """
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", gpu_count=4)

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert "overrides" not in manifest["spec"]
    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any"}}
    assert manifest["spec"]["profileOverrides"] == {"acceleratorCount": 4}


def test_generate_aim_service_manifest_gpu_count_omitted_emits_no_overrides() -> None:
    """When gpu_count is not supplied, spec.profileOverrides is not emitted.

    Per ADR 006b §3 the engine derives the count from the resolved profile, so
    AIWB must not stamp an empty/default override that would shadow it.
    """
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert "profileOverrides" not in manifest["spec"]


def test_generate_aim_service_manifest_gpu_count_with_profile_name() -> None:
    """gpu_count overrides apply on top of direct profile_name references too.

    profile_name picks the base profile; profileOverrides.acceleratorCount is
    then layered on top — both keys coexist in spec.
    """
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", profile_name="mi300x-throughput-fp8", gpu_count=2)

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert manifest["spec"]["profile"] == {"name": "mi300x-throughput-fp8"}
    assert manifest["spec"]["profileOverrides"] == {"acceleratorCount": 2}


def test_generate_aim_service_manifest_selector_only_gpu_model() -> None:
    """gpu_model alone sets spec.profile.selector.acceleratorModel only."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", gpu_model="MI300X")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert "overrides" not in manifest["spec"]
    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any", "acceleratorModel": "MI300X"}}


def test_generate_aim_service_manifest_selector_metric_precision_gpu_model() -> None:
    """All three selector fields combine into a single spec.profile.selector."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="llama3-8b",
        metric=OptimizationMetric.THROUGHPUT,
        precision="fp8",
        gpu_model="MI325X",
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

    assert "overrides" not in manifest["spec"]
    assert manifest["spec"]["profile"]["selector"] == {
        "minimumType": "any",
        "metric": "throughput",
        "precision": "fp8",
        "acceleratorModel": "MI325X",
    }


def test_generate_aim_service_manifest_gpu_count_with_selector() -> None:
    """gpu_count and selector criteria coexist on independent spec branches.

    Fences a future refactor from folding gpu_count back into the selector dict:
    the selector picks the profile by hardware model (per ADR 006b §3) and
    gpu_count layers as profileOverrides.acceleratorCount on the resolved profile.
    """
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="llama3-8b",
        metric=OptimizationMetric.LATENCY,
        gpu_count=2,
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

    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any", "metric": "latency"}}
    assert manifest["spec"]["profileOverrides"] == {"acceleratorCount": 2}


def test_generate_aim_service_manifest_camelcase_keys_to_cluster() -> None:
    """Manifest sent to cluster uses camelCase keys."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="llama3-8b",
        image_pull_secrets=["s1"],
        profile_name="profile-x",
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
    assert spec["profile"]["name"] == "profile-x"
    assert "template" not in spec
    assert spec["minReplicas"] == 1
    assert spec["maxReplicas"] == 5
    assert "autoScaling" in spec


def test_generate_aim_service_manifest_with_cluster_auth_group() -> None:
    """Cluster-auth group ID is stamped in two places during the migration window:

    - metadata.annotations: read by aim-engine, propagated to InferenceService,
      then surfaced as SecurityPolicy contextExtensions by ai-gateway-discovery
      (the Envoy AI Gateway auth path, EAI-6038)
    - spec.routing.annotations: legacy slot still consumed by kgateway + API key auth;
      kept for back-compat until kgateway is removed
    """
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

    assert manifest["metadata"]["annotations"]["cluster-auth/allowed-group"] == "group-123"
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


def test_generate_fine_tuned_aim_service_manifest_stamps_finetuned_metadata() -> None:
    """User-facing fine-tune identity (display name + canonical name) lives in annotations,
    not labels — so values can carry characters K8s label values forbid (e.g. `/`).
    Labels are reserved for selector-relevant flags (fine-tuned marker, workload type)."""
    req = AIMDeployRequest(model="wb-llm-finetune-abc123")

    manifest = generate_fine_tuned_aim_service_manifest(
        model_name="wb-llm-finetune-abc123",
        deploy_request=req,
        namespace="workbench",
        service_name="wb-aim-test",
        api_version="aim.eai.amd.com/v1alpha2",
        submitter="user@example.com",
        cluster_auth_group_id="group-123",
        display_name="my-finetune",
        canonical_name="Qwen/Qwen2.5-0.5B-Instruct",
    )

    labels = manifest["metadata"]["labels"]
    assert labels["aiwb.apps.eai.amd.com/fine-tuned"] == "true"
    assert labels["aiwb.apps.eai.amd.com/namespace-aim-model"] == "true"
    # User-facing identity is intentionally NOT in labels.
    assert MODEL_NAME_LABEL not in labels
    assert CANONICAL_NAME_LABEL not in labels

    annotations = manifest["metadata"]["annotations"]
    assert annotations[MODEL_NAME_LABEL] == "my-finetune"
    # Annotation preserves slashes; the FE reads this for code samples.
    assert annotations[CANONICAL_NAME_LABEL] == "Qwen/Qwen2.5-0.5B-Instruct"
    # Forces the v1alpha2 profile pipeline so status.resolvedProfile lands;
    # EAI-6783 will remove the annotation once aim-engine drops v1alpha1 dispatch.
    assert annotations["aim.eai.amd.com/reconciler-pipeline"] == "profile"
    # Cluster-auth group is stamped on metadata for the Envoy AI Gateway path
    # (EAI-6038), and also on spec.routing.annotations for legacy kgateway.
    assert annotations["cluster-auth/allowed-group"] == "group-123"
    assert manifest["spec"]["routing"]["annotations"]["cluster-auth/allowed-group"] == "group-123"

    # caching.mode replaces the deprecated cacheModel boolean.
    assert manifest["spec"]["caching"]["mode"] == "Shared"
    assert "cacheModel" not in manifest["spec"]


def _fine_tuned_manifest(req: AIMDeployRequest) -> dict:
    return generate_fine_tuned_aim_service_manifest(
        model_name="wb-llm-finetune-abc123",
        deploy_request=req,
        namespace="workbench",
        service_name="wb-aim-test",
        api_version="aim.eai.amd.com/v1alpha2",
        submitter="user@example.com",
        cluster_auth_group_id="group-123",
        display_name="my-finetune",
        canonical_name="Qwen/Qwen2.5-0.5B-Instruct",
    )


def test_generate_fine_tuned_aim_service_manifest_auto_via_model() -> None:
    """Empty deploy request emits spec.profile.selector with minimumType=any."""
    manifest = _fine_tuned_manifest(AIMDeployRequest(model="wb-llm-finetune-abc123"))

    assert manifest["spec"]["model"]["name"] == "wb-llm-finetune-abc123"
    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any"}}
    assert "profileOverrides" not in manifest["spec"]
    assert "overrides" not in manifest["spec"]


def test_generate_namespace_aim_service_manifest_pins_resolved_profile_name() -> None:
    """Pinned profiles take precedence over deploy-time selectors and overrides."""
    manifest = generate_namespace_aim_service_manifest(
        model_name="custom-model",
        deploy_request=AIMDeployRequest(
            model="custom-model",
            metric=OptimizationMetric.LATENCY,
            precision="fp8",
        ),
        namespace="workbench",
        service_name="wb-aim-test",
        api_version="aim.eai.amd.com/v1alpha2",
        submitter="user@example.com",
        cluster_auth_group_id=None,
        display_name="Custom Display",
        canonical_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        is_fine_tuned=False,
        resolved_profile_name="custom-profile",
    )

    assert manifest["spec"]["profile"] == {"name": "custom-profile"}
    assert "profileOverrides" not in manifest["spec"]
    assert "selector" not in manifest["spec"].get("profile", {})


def test_generate_namespace_aim_service_manifest_uses_deploy_display_name() -> None:
    """A user-entered deploy display name wins for the display-name annotation,
    while the model identity stays on MODEL_NAME_LABEL."""
    manifest = generate_namespace_aim_service_manifest(
        model_name="custom-model",
        deploy_request=AIMDeployRequest(model="custom-model"),
        namespace="workbench",
        service_name="wb-aim-test",
        api_version="aim.eai.amd.com/v1alpha2",
        submitter="user@example.com",
        cluster_auth_group_id=None,
        display_name="Custom Display",
        canonical_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        is_fine_tuned=False,
        resolved_profile_name="custom-profile",
        deploy_display_name="My TinyLlama",
    )

    annotations = manifest["metadata"]["annotations"]
    assert annotations[DISPLAY_NAME_ANNOTATION] == "My TinyLlama"
    assert annotations[MODEL_NAME_LABEL] == "Custom Display"


def test_generate_namespace_aim_service_manifest_falls_back_to_model_display_name() -> None:
    """Without a deploy display name, the display-name annotation falls back to
    the onboarded model's identity."""
    manifest = generate_namespace_aim_service_manifest(
        model_name="custom-model",
        deploy_request=AIMDeployRequest(model="custom-model"),
        namespace="workbench",
        service_name="wb-aim-test",
        api_version="aim.eai.amd.com/v1alpha2",
        submitter="user@example.com",
        cluster_auth_group_id=None,
        display_name="Custom Display",
        canonical_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        is_fine_tuned=False,
        resolved_profile_name="custom-profile",
    )

    assert manifest["metadata"]["annotations"][DISPLAY_NAME_ANNOTATION] == "Custom Display"


def test_generate_namespace_aim_service_manifest_ignores_whitespace_deploy_display_name() -> None:
    """A whitespace-only deploy name is not a real name; fall back to model identity."""
    manifest = generate_namespace_aim_service_manifest(
        model_name="custom-model",
        deploy_request=AIMDeployRequest(model="custom-model"),
        namespace="workbench",
        service_name="wb-aim-test",
        api_version="aim.eai.amd.com/v1alpha2",
        submitter="user@example.com",
        cluster_auth_group_id=None,
        display_name="Custom Display",
        canonical_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        is_fine_tuned=False,
        resolved_profile_name="custom-profile",
        deploy_display_name="   ",
    )

    assert manifest["metadata"]["annotations"][DISPLAY_NAME_ANNOTATION] == "Custom Display"


def test_generate_fine_tuned_aim_service_manifest_with_metric_selector() -> None:
    manifest = _fine_tuned_manifest(AIMDeployRequest(model="wb-llm-finetune-abc123", metric=OptimizationMetric.LATENCY))

    assert manifest["spec"]["profile"]["selector"] == {"minimumType": "any", "metric": "latency"}


def test_generate_fine_tuned_aim_service_manifest_with_precision_selector() -> None:
    manifest = _fine_tuned_manifest(AIMDeployRequest(model="wb-llm-finetune-abc123", precision="bf16"))

    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any", "precision": "bf16"}}


def test_generate_fine_tuned_aim_service_manifest_with_gpu_model_selector() -> None:
    manifest = _fine_tuned_manifest(AIMDeployRequest(model="wb-llm-finetune-abc123", gpu_model="MI300X"))

    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any", "acceleratorModel": "MI300X"}}


def test_generate_fine_tuned_aim_service_manifest_combined_selector() -> None:
    manifest = _fine_tuned_manifest(
        AIMDeployRequest(
            model="wb-llm-finetune-abc123",
            metric=OptimizationMetric.THROUGHPUT,
            precision="fp8",
            gpu_model="MI325X",
        )
    )

    assert manifest["spec"]["profile"]["selector"] == {
        "minimumType": "any",
        "metric": "throughput",
        "precision": "fp8",
        "acceleratorModel": "MI325X",
    }


def test_generate_fine_tuned_aim_service_manifest_with_profile_name() -> None:
    manifest = _fine_tuned_manifest(
        AIMDeployRequest(model="wb-llm-finetune-abc123", profile_name="my-namespace-profile")
    )

    assert manifest["spec"]["profile"] == {"name": "my-namespace-profile"}


def test_generate_fine_tuned_aim_service_manifest_with_gpu_count_profile_override() -> None:
    manifest = _fine_tuned_manifest(AIMDeployRequest(model="wb-llm-finetune-abc123", gpu_count=8))

    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any"}}
    assert manifest["spec"]["profileOverrides"] == {"acceleratorCount": 8}


def test_generate_fine_tuned_aim_service_manifest_with_engine_args_profile_override() -> None:
    manifest = _fine_tuned_manifest(
        AIMDeployRequest(model="wb-llm-finetune-abc123", engine_args={"max-model-len": 8192})
    )

    assert manifest["spec"]["profileOverrides"] == {"engineArgs": {"max-model-len": 8192}}


def test_generate_fine_tuned_aim_service_manifest_with_engine_env_profile_override() -> None:
    manifest = _fine_tuned_manifest(
        AIMDeployRequest(model="wb-llm-finetune-abc123", engine_env=[{"name": "VLLM_LOGGING_LEVEL", "value": "DEBUG"}])
    )

    assert manifest["spec"]["profileOverrides"] == {"engineEnv": {"VLLM_LOGGING_LEVEL": "DEBUG"}}


@pytest.mark.parametrize(
    ("engine_env", "message"),
    [
        ([{"value": "DEBUG"}], "missing required field 'name'"),
        ([{"name": "VLLM_LOGGING_LEVEL"}], "missing required field 'value'"),
        ([{"name": "VLLM_LOGGING_LEVEL", "value": None}], "value must be a string"),
        (
            [{"name": "VLLM_LOGGING_LEVEL", "value": "DEBUG"}, {"name": "VLLM_LOGGING_LEVEL", "value": "INFO"}],
            "duplicates earlier entry",
        ),
    ],
)
def test_generate_aim_service_manifest_rejects_invalid_engine_env_entries(
    engine_env: list[dict[str, object]], message: str
) -> None:
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", engine_env=engine_env)

    with pytest.raises(ValidationException, match=message):
        generate_aim_service_manifest(
            aim=aim,
            deploy_request=req,
            namespace="ns",
            service_name="wb-aim-test",
            api_version="v1",
            submitter="u",
            cluster_auth_group_id="grp",
        )


def test_generate_fine_tuned_aim_service_manifest_with_container_env_profile_override() -> None:
    container_env = [{"name": "FOO", "value": "bar"}]
    manifest = _fine_tuned_manifest(AIMDeployRequest(model="wb-llm-finetune-abc123", container_env=container_env))

    assert manifest["spec"]["profileOverrides"] == {"containerEnv": container_env}


def test_generate_fine_tuned_aim_service_manifest_selector_and_profile_overrides() -> None:
    manifest = _fine_tuned_manifest(
        AIMDeployRequest(
            model="wb-llm-finetune-abc123",
            precision="fp8",
            gpu_count=4,
            engine_args={"max-model-len": 4096},
        )
    )

    assert manifest["spec"]["profile"] == {"selector": {"minimumType": "any", "precision": "fp8"}}
    assert manifest["spec"]["profileOverrides"] == {
        "acceleratorCount": 4,
        "engineArgs": {"max-model-len": 4096},
    }


def test_generate_aim_service_manifest_with_engine_args_profile_override() -> None:
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", engine_args={"max-model-len": 8192})

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert manifest["spec"]["profileOverrides"] == {"engineArgs": {"max-model-len": 8192}}


def test_generate_aim_service_manifest_with_engine_env_profile_override() -> None:
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", engine_env=[{"name": "VLLM_LOGGING_LEVEL", "value": "DEBUG"}])

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert manifest["spec"]["profileOverrides"] == {"engineEnv": {"VLLM_LOGGING_LEVEL": "DEBUG"}}


def test_generate_aim_service_manifest_with_container_env_profile_override() -> None:
    container_env = [{"name": "FOO", "value": "bar"}]
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="llama3-8b", container_env=container_env)

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=req,
        namespace="ns",
        service_name="wb-aim-test",
        api_version="v1",
        submitter="u",
        cluster_auth_group_id="grp",
    )

    assert manifest["spec"]["profileOverrides"] == {"containerEnv": container_env}


def test_generate_aim_service_manifest_selector_and_profile_overrides() -> None:
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="llama3-8b",
        metric=OptimizationMetric.LATENCY,
        gpu_count=2,
        engine_env=[{"name": "VLLM_LOGGING_LEVEL", "value": "INFO"}],
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

    assert manifest["spec"]["profile"]["selector"] == {"minimumType": "any", "metric": "latency"}
    assert manifest["spec"]["profileOverrides"] == {
        "acceleratorCount": 2,
        "engineEnv": {"VLLM_LOGGING_LEVEL": "INFO"},
    }
