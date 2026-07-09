# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


import hashlib
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin
from uuid import uuid4

from loguru import logger

from api_common.exceptions import ValidationException

from ..config import CLUSTER_HOST, EAI_APPS_METADATA_PREFIX, SUBMITTER_ANNOTATION
from ..dispatch.crds import K8sMetadata
from ..workloads.constants import CANONICAL_NAME_LABEL, DISPLAY_NAME_ANNOTATION, MODEL_NAME_LABEL
from ..workloads.enums import WorkloadType
from .config import AIM_CLUSTER_RUNTIME_CONFIG_NAME, AIM_GATEWAY_NAME, AIM_GATEWAY_NAMESPACE
from .constants import (
    CLUSTER_AUTH_GROUP_ANNOTATION,
    FINE_TUNED_LABEL,
    NAMESPACE_AIM_MODEL_LABEL,
    RECONCILER_PIPELINE_ANNOTATION,
    RECONCILER_PIPELINE_PROFILE,
)
from .crds import AIMModelResource, AIMServiceResource, AIMServiceSpec, HTTPRouteResource

if TYPE_CHECKING:
    from .schemas import AIMDeployRequest


def is_condition_true(conditions: list[dict[str, Any]], condition_type: str) -> bool:
    """Check if a specific condition type is True.

    Args:
        conditions: List of condition dicts from AIMService status
        condition_type: Condition type to check (e.g., "InferenceServiceReady")

    Returns:
        True if condition exists and status is "True", False otherwise
    """
    for condition in conditions:
        if condition.get("type") == condition_type:
            return condition.get("status") == "True"
    return False


def generate_aim_service_name(aim_id: str | None = None) -> str:
    """
    Generate a unique name for an AIM service.

    Args:
        aim_id: Optional UUID string. If not provided, generates a new UUID internally.

    Returns:
        Service name in format "wb-aim-{hash}" (15 chars total)

    Note:
        - Uses "wb-aim-" prefix + 8-char hash (15 chars total)
        - Prefix ensures name starts with letter (KServe requirement)
        - This allows namespace names up to 63 - 15 - 10 ("-predictor") - 1 = 37 chars
    """
    uuid_str = str(aim_id) if aim_id else str(uuid4())
    hash_digest = hashlib.sha256(uuid_str.encode()).hexdigest()
    return f"wb-aim-{hash_digest[:8]}"


def get_aim_service_internal_url(
    httproute: HTTPRouteResource,
    namespace: str,
) -> str:
    """
    Extract the internal URL for an AIMService from HTTPRoute backend.

    Args:
        httproute: HTTPRoute resource from Kubernetes API
        namespace: Namespace of the AIMService

    Returns:
        Internal service URL

    Raises:
        ValidationException: If HTTPRoute has no rules or no Service backend reference
    """

    if not httproute.spec.rules:
        raise ValidationException("HTTPRoute has no rules")

    # Find first Service backend reference
    service_backend = next(
        (ref for rule in httproute.spec.rules for ref in rule.backend_refs if ref.kind == "Service" and ref.name),
        None,
    )
    if not service_backend:
        raise ValidationException("No Service backend reference found in HTTPRoute")

    port_suffix = f":{service_backend.port}" if service_backend.port not in (None, 80) else ""
    return f"http://{service_backend.name}.{namespace}.svc.cluster.local{port_suffix}"


def get_aim_service_external_url(
    httproute: HTTPRouteResource,
    cluster_host: str = CLUSTER_HOST,
) -> str:
    """
    Extract the external URL for an AIMService from HTTPRoute path.

    Args:
        httproute: HTTPRoute resource from Kubernetes API
        cluster_host: Base URL of the cluster (should include http:// or https://)

    Returns:
        External URL

    Raises:
        ValidationException: If cluster host not configured, no rules, or no PathPrefix found
    """

    if not cluster_host:
        raise ValidationException("Cluster host is not set - external URLs not available")

    if not httproute.spec.rules:
        raise ValidationException("HTTPRoute has no rules")

    # Find first PathPrefix match
    path_match = next(
        (
            match.path.value
            for rule in httproute.spec.rules
            for match in rule.matches
            if match.path and match.path.type == "PathPrefix" and match.path.value
        ),
        None,
    )
    if not path_match:
        raise ValidationException("No PathPrefix match found in HTTPRoute")

    base_url = cluster_host if cluster_host.startswith(("http://", "https://")) else f"https://{cluster_host}"
    return urljoin(base_url, path_match)


def extract_endpoints(
    aim_service: AIMServiceResource,
    httproute: HTTPRouteResource | None = None,
    cluster_host: str = CLUSTER_HOST,
    inference_service_name: str | None = None,
) -> dict[str, str]:
    """
    Extract internal and external endpoints for an AIMService.

    When an HTTPRoute is present, the internal URL uses its backend ref (which
    may include a custom port) and the external URL is derived from its path
    prefix. Otherwise, the internal URL is derived from the KServe predictor
    service name ({isvc-name}-predictor.{namespace}.svc.cluster.local).

    Args:
        aim_service: The AIMService CRD resource
        httproute: HTTPRoute resource from Kubernetes API (optional)
        cluster_host: Base URL of the cluster (should include http:// or https://)
        inference_service_name: Name of the KServe InferenceService owned by this
            AIMService (fetched via ownerReferences). Used to derive the predictor
            service URL when HTTPRoute is not available.

    Returns:
        Dictionary with "internal" and optionally "external" URLs
    """
    namespace = aim_service.metadata.namespace or ""
    name = aim_service.metadata.name

    endpoints: dict[str, str] = {}

    if httproute:
        try:
            endpoints["internal"] = get_aim_service_internal_url(httproute, namespace)
        except Exception as e:
            logger.warning(f"Could not determine internal URL from HTTPRoute for {name}: {e}")

        try:
            endpoints["external"] = get_aim_service_external_url(httproute, cluster_host)
        except Exception as e:
            logger.warning(f"Could not determine external URL for {name}: {e}")

    if "internal" not in endpoints and inference_service_name:
        endpoints["internal"] = f"http://{inference_service_name}-predictor.{namespace}.svc.cluster.local"

    if "internal" not in endpoints:
        logger.warning(
            f"Could not determine internal URL for AIMService {name}: no HTTPRoute or InferenceService found"
        )

    return endpoints


def _build_aim_service_profile(deploy_request: "AIMDeployRequest") -> dict[str, Any]:
    """Build spec.profile (direct name or selector) from deploy-time criteria.

    Always injects minimumType=any so aim-engine considers all profile tiers
    (optimized, preview, unoptimized) rather than enforcing the default optimized
    floor. Without this, deployments on clusters that only have unoptimized or
    preview profiles fail with ProfileNotFound even when matching candidates exist.
    """
    if deploy_request.profile_name:
        return {"name": deploy_request.profile_name}

    selector: dict[str, Any] = {"minimumType": "any"}
    if deploy_request.metric:
        selector["metric"] = deploy_request.metric
    if deploy_request.precision:
        selector["precision"] = deploy_request.precision
    if deploy_request.gpu_model is not None:
        selector["acceleratorModel"] = deploy_request.gpu_model
    return {"selector": selector}


def env_entries_to_map(entries: list[dict[str, Any]]) -> dict[str, str]:
    """Convert K8s-style env var entries to the engineEnv map shape."""
    result: dict[str, str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValidationException(f"engineEnv[{index}] must be an object with name and value")
        if "name" not in entry:
            raise ValidationException(f"engineEnv[{index}] is missing required field 'name'")
        if "value" not in entry:
            raise ValidationException(f"engineEnv[{index}] is missing required field 'value'")

        name = entry["name"]
        value = entry["value"]
        if not isinstance(name, str) or not name:
            raise ValidationException(f"engineEnv[{index}].name must be a non-empty string")
        if value is None:
            raise ValidationException(f"engineEnv[{index}].value must be a string")
        if not isinstance(value, str):
            raise ValidationException(f"engineEnv[{index}].value must be a string")
        if name in result:
            raise ValidationException(f"engineEnv[{index}].name duplicates earlier entry '{name}'")

        result[name] = value
    return result


def _build_aim_service_profile_overrides(deploy_request: "AIMDeployRequest") -> dict[str, Any]:
    """Build spec.profileOverrides patches applied on top of the resolved profile."""
    overrides: dict[str, Any] = {}
    if deploy_request.gpu_count is not None:
        overrides["acceleratorCount"] = deploy_request.gpu_count
    if deploy_request.engine_args:
        overrides["engineArgs"] = deploy_request.engine_args
    if deploy_request.engine_env:
        overrides["engineEnv"] = env_entries_to_map(deploy_request.engine_env)
    if deploy_request.container_env:
        overrides["containerEnv"] = deploy_request.container_env
    return overrides


def _apply_deploy_profile_fields(spec_dict: dict[str, Any], deploy_request: "AIMDeployRequest") -> None:
    """Populate spec.profile and spec.profileOverrides from the deploy request."""
    spec_dict["profile"] = _build_aim_service_profile(deploy_request)
    profile_overrides = _build_aim_service_profile_overrides(deploy_request)
    if profile_overrides:
        spec_dict["profile_overrides"] = profile_overrides


def generate_fine_tuned_aim_service_manifest(
    model_name: str,
    deploy_request: "AIMDeployRequest",
    namespace: str,
    service_name: str,
    api_version: str,
    submitter: str,
    cluster_auth_group_id: str | None,
    display_name: str,
    canonical_name: str,
) -> dict:
    """Backward-compatible wrapper for fine-tuned namespace deployments."""
    return generate_namespace_aim_service_manifest(
        model_name=model_name,
        deploy_request=deploy_request,
        namespace=namespace,
        service_name=service_name,
        api_version=api_version,
        submitter=submitter,
        cluster_auth_group_id=cluster_auth_group_id,
        display_name=display_name,
        canonical_name=canonical_name,
        is_fine_tuned=True,
    )


def generate_namespace_aim_service_manifest(
    model_name: str,
    deploy_request: "AIMDeployRequest",
    namespace: str,
    service_name: str,
    api_version: str,
    submitter: str,
    cluster_auth_group_id: str | None,
    display_name: str,
    canonical_name: str,
    is_fine_tuned: bool = True,
    resolved_profile_name: str | None = None,
    deploy_display_name: str | None = None,
) -> dict:
    """Generate AIMService manifest for a namespace AIMModel deployment.

    Sibling of generate_aim_service_manifest; takes a namespace-scoped AIMModel
    name (`model_name`) instead of an AIMModelResource. Stamps
    NAMESPACE_AIM_MODEL_LABEL so chattable detection skips the cluster-catalog
    lookup. For backward compatibility, fine-tuned deployments also keep
    FINE_TUNED_LABEL.

    ``display_name`` is the onboarded model's identity (kept on MODEL_NAME_LABEL).
    ``deploy_display_name`` is the optional user-entered deploy name; when present
    it wins for the user-visible DISPLAY_NAME_ANNOTATION, otherwise it falls back
    to the model identity.
    """
    routing_config: dict[str, Any] = {
        "enabled": True,
        "gatewayRef": {
            "name": AIM_GATEWAY_NAME,
            "namespace": AIM_GATEWAY_NAMESPACE,
        },
    }
    # DEPRECATED (EAI-6038): retained for the legacy kgateway + API key auth path.
    # The Envoy AI Gateway path reads cluster-auth/allowed-group from
    # metadata.annotations below (propagated to InferenceService by aim-engine,
    # then surfaced as SecurityPolicy contextExtensions by ai-gateway-discovery).
    # Remove once kgateway is no longer in use.
    if cluster_auth_group_id is not None:
        routing_config["annotations"] = {CLUSTER_AUTH_GROUP_ANNOTATION: cluster_auth_group_id}

    spec_dict: dict[str, Any] = {
        "model": {"name": model_name},
        "replicas": deploy_request.replicas,
        "runtime_config_name": AIM_CLUSTER_RUNTIME_CONFIG_NAME,
        "caching": {"mode": "Shared"},
        "routing": routing_config,
    }

    # When a ready namespace AIMProfile exists (custom onboarding or fine-tuned
    # emission), pin it by name so aim-engine uses model/profile settings instead
    # of selector resolution. Deploy-time selectors and profileOverrides on the
    # request are ignored in that case. Without a pinned profile, the deploy
    # request may supply selectors/overrides or omit spec.profile for auto-resolve.
    if resolved_profile_name:
        spec_dict["profile"] = {"name": resolved_profile_name}
    else:
        _apply_deploy_profile_fields(spec_dict, deploy_request)

    if deploy_request.min_replicas is not None:
        spec_dict["min_replicas"] = deploy_request.min_replicas
        spec_dict["max_replicas"] = deploy_request.max_replicas
        spec_dict["auto_scaling"] = deploy_request.auto_scaling

    # A whitespace-only deploy name is not a real name; fall back to model identity.
    effective_display_name = (deploy_display_name or "").strip() or display_name

    resource = AIMServiceResource(
        metadata=K8sMetadata(
            name=service_name,
            namespace=namespace,
            annotations={
                SUBMITTER_ANNOTATION: submitter,
                # TODO(EAI-6783): drop once aim-engine removes v1alpha1 and the
                # profile pipeline becomes the default dispatch.
                RECONCILER_PIPELINE_ANNOTATION: RECONCILER_PIPELINE_PROFILE,
                CANONICAL_NAME_LABEL: canonical_name,
                MODEL_NAME_LABEL: display_name,
                **({DISPLAY_NAME_ANNOTATION: effective_display_name} if effective_display_name else {}),
                **({CLUSTER_AUTH_GROUP_ANNOTATION: cluster_auth_group_id} if cluster_auth_group_id is not None else {}),
            },
            labels={
                f"{EAI_APPS_METADATA_PREFIX}/workload-type": WorkloadType.INFERENCE,
                # Marks this service as deployed from a namespace AIMModel so
                # chattable detection does not require an AIMClusterModel catalog lookup.
                NAMESPACE_AIM_MODEL_LABEL: "true",
                **({FINE_TUNED_LABEL: "true"} if is_fine_tuned else {}),
            },
        ),
        spec=AIMServiceSpec.model_validate(spec_dict),
    )

    manifest = resource.model_dump(
        by_alias=True,
        exclude_none=True,
        exclude={"status", "httproute", "inference_service_name", "id"},
    )
    manifest["apiVersion"] = api_version
    manifest["kind"] = "AIMService"
    return manifest


def generate_aim_service_manifest(
    aim: AIMModelResource,
    deploy_request: "AIMDeployRequest",
    namespace: str,
    service_name: str,
    api_version: str,
    submitter: str,
    cluster_auth_group_id: str | None,
    display_name: str | None = None,
) -> dict:
    """Generate AIMService CRD manifest for deploying an AIM using Pydantic models.

    Args:
        aim: AIMClusterModel resource
        deploy_request: The deployment request with model identifier
        namespace: Target namespace
        service_name: The K8s resource name for the AIMService
        api_version: K8s API version
        submitter: User submitting the service
        cluster_auth_group_id: Cluster-Auth group ID for access control, or None when disabled
        display_name: Optional user-visible display name stored as annotation
    """
    # Build spec using dict for complex fields that aren't fully modeled
    routing_config: dict[str, Any] = {
        "enabled": True,
        "gatewayRef": {
            "name": AIM_GATEWAY_NAME,
            "namespace": AIM_GATEWAY_NAMESPACE,
        },
    }
    # DEPRECATED (EAI-6038): retained for the legacy kgateway + API key auth path.
    # The Envoy AI Gateway path reads cluster-auth/allowed-group from
    # metadata.annotations below (propagated to InferenceService by aim-engine,
    # then surfaced as SecurityPolicy contextExtensions by ai-gateway-discovery).
    # Remove once kgateway is no longer in use.
    if cluster_auth_group_id is not None:
        routing_config["annotations"] = {CLUSTER_AUTH_GROUP_ANNOTATION: cluster_auth_group_id}

    spec_dict: dict[str, Any] = {
        "model": {"name": aim.metadata.name},
        "replicas": deploy_request.replicas,
        "runtime_config_name": AIM_CLUSTER_RUNTIME_CONFIG_NAME,
        "caching": {"mode": "Shared"},
        "routing": routing_config,
    }

    _apply_deploy_profile_fields(spec_dict, deploy_request)

    # Add scaling policy if provided (validation handled by pydantic schema)
    if deploy_request.min_replicas is not None:
        spec_dict["min_replicas"] = deploy_request.min_replicas
        spec_dict["max_replicas"] = deploy_request.max_replicas
        spec_dict["auto_scaling"] = deploy_request.auto_scaling

    if deploy_request.image_pull_secrets:
        spec_dict["imagePullSecrets"] = [{"name": secret_name} for secret_name in deploy_request.image_pull_secrets]

    if deploy_request.hf_token:
        spec_dict["caching"]["env"] = [
            {
                "name": "HF_TOKEN",
                "valueFrom": {"secretKeyRef": {"name": deploy_request.hf_token, "key": "token"}},
            }
        ]

    resource = AIMServiceResource(
        metadata=K8sMetadata(
            name=service_name,
            namespace=namespace,
            annotations={
                SUBMITTER_ANNOTATION: submitter,
                # TODO(EAI-6783): drop once aim-engine removes v1alpha1 and the
                # profile pipeline becomes the default dispatch.
                RECONCILER_PIPELINE_ANNOTATION: RECONCILER_PIPELINE_PROFILE,
                **({DISPLAY_NAME_ANNOTATION: display_name} if display_name else {}),
                **({CLUSTER_AUTH_GROUP_ANNOTATION: cluster_auth_group_id} if cluster_auth_group_id is not None else {}),
            },
            labels={
                f"{EAI_APPS_METADATA_PREFIX}/workload-type": WorkloadType.INFERENCE,
            },
        ),
        spec=AIMServiceSpec.model_validate(spec_dict),
    )

    # Convert to dict with camelCase for K8s API
    # Exclude status and computed fields (e.g., id) which aren't part of the CRD
    manifest = resource.model_dump(
        by_alias=True,
        exclude_none=True,
        exclude={"status", "httproute", "inference_service_name", "id"},
    )
    manifest["apiVersion"] = api_version
    manifest["kind"] = "AIMService"

    return manifest
