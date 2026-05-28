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
from ..workloads.constants import CANONICAL_NAME_LABEL, MODEL_NAME_LABEL
from ..workloads.enums import WorkloadType
from .config import AIM_CLUSTER_RUNTIME_CONFIG_NAME, AIM_GATEWAY_NAME, AIM_GATEWAY_NAMESPACE
from .constants import CLUSTER_AUTH_GROUP_ANNOTATION, FINE_TUNED_LABEL
from .crds import AIMClusterModelResource, AIMServiceResource, AIMServiceSpec, HTTPRouteResource

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
    """Generate AIMService manifest for a fine-tuned model deployment.

    Sibling of generate_aim_service_manifest; takes a namespace-scoped AIMModel
    name (`model_name`) instead of an AIMClusterModelResource. Stamps
    FINE_TUNED_LABEL so chattable detection skips the cluster-catalog lookup,
    plus display_name and canonical_name as annotations for the FE.
    """
    routing_config: dict[str, Any] = {
        "enabled": True,
        "gatewayRef": {
            "name": AIM_GATEWAY_NAME,
            "namespace": AIM_GATEWAY_NAMESPACE,
        },
    }
    if cluster_auth_group_id is not None:
        routing_config["annotations"] = {CLUSTER_AUTH_GROUP_ANNOTATION: cluster_auth_group_id}

    template_dict: dict[str, Any] = {
        "allowUnoptimized": deploy_request.allow_unoptimized,
    }
    if deploy_request.template_name:
        template_dict["name"] = deploy_request.template_name

    spec_dict: dict[str, Any] = {
        "model": {"name": model_name},
        "replicas": deploy_request.replicas,
        "runtime_config_name": AIM_CLUSTER_RUNTIME_CONFIG_NAME,
        "cache_model": True,
        "routing": routing_config,
        "template": template_dict,
    }

    if deploy_request.min_replicas is not None:
        spec_dict["min_replicas"] = deploy_request.min_replicas
        spec_dict["max_replicas"] = deploy_request.max_replicas
        spec_dict["auto_scaling"] = deploy_request.auto_scaling

    resource = AIMServiceResource(
        metadata=K8sMetadata(
            name=service_name,
            namespace=namespace,
            annotations={
                SUBMITTER_ANNOTATION: submitter,
                CANONICAL_NAME_LABEL: canonical_name,
                MODEL_NAME_LABEL: display_name,
            },
            labels={
                f"{EAI_APPS_METADATA_PREFIX}/workload-type": WorkloadType.INFERENCE,
                # Marks this service as deployed from a fine-tuned model so that
                # chattable detection does not require an AIMClusterModel catalog lookup.
                FINE_TUNED_LABEL: "true",
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
    aim: AIMClusterModelResource,
    deploy_request: "AIMDeployRequest",
    namespace: str,
    service_name: str,
    api_version: str,
    submitter: str,
    cluster_auth_group_id: str | None,
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
    """
    # Build spec using dict for complex fields that aren't fully modeled
    routing_config: dict[str, Any] = {
        "enabled": True,
        "gatewayRef": {
            "name": AIM_GATEWAY_NAME,
            "namespace": AIM_GATEWAY_NAMESPACE,
        },
    }
    if cluster_auth_group_id is not None:
        routing_config["annotations"] = {CLUSTER_AUTH_GROUP_ANNOTATION: cluster_auth_group_id}

    template_dict: dict[str, Any] = {
        "allowUnoptimized": deploy_request.allow_unoptimized,
    }
    if deploy_request.template_name:
        template_dict["name"] = deploy_request.template_name

    spec_dict: dict[str, Any] = {
        "model": {"name": aim.metadata.name},
        "replicas": deploy_request.replicas,
        "runtime_config_name": AIM_CLUSTER_RUNTIME_CONFIG_NAME,
        "cache_model": True,
        "routing": routing_config,
        "template": template_dict,
    }

    # Add scaling policy if provided (validation handled by pydantic schema)
    if deploy_request.min_replicas is not None:
        spec_dict["min_replicas"] = deploy_request.min_replicas
        spec_dict["max_replicas"] = deploy_request.max_replicas
        spec_dict["auto_scaling"] = deploy_request.auto_scaling

    if deploy_request.image_pull_secrets:
        spec_dict["imagePullSecrets"] = [{"name": secret_name} for secret_name in deploy_request.image_pull_secrets]

    if deploy_request.hf_token:
        spec_dict["env"] = [
            {
                "name": "HF_TOKEN",
                "valueFrom": {"secretKeyRef": {"name": deploy_request.hf_token, "key": "token"}},
            }
        ]

    overrides: dict[str, Any] = {}
    if deploy_request.metric:
        overrides["metric"] = deploy_request.metric
    if deploy_request.precision:
        overrides["precision"] = deploy_request.precision
    if deploy_request.gpu_model is not None or deploy_request.gpu_count is not None:
        gpu_spec: dict[str, Any] = {}
        if deploy_request.gpu_model is not None:
            gpu_spec["model"] = deploy_request.gpu_model
        if deploy_request.gpu_count is not None:
            gpu_spec["requests"] = deploy_request.gpu_count
        if gpu_spec:
            overrides["hardware"] = {"gpu": gpu_spec}

    if overrides:
        spec_dict["overrides"] = overrides

    resource = AIMServiceResource(
        metadata=K8sMetadata(
            name=service_name,
            namespace=namespace,
            annotations={SUBMITTER_ANNOTATION: submitter},
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
