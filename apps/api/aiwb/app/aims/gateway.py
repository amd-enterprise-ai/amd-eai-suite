# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Gateway for accessing AIMClusterModel resources from Kubernetes."""

from typing import Any
from uuid import UUID

from loguru import logger

from ..dispatch.kube_client import KubernetesClient
from ..dispatch.utils import get_resource_version
from ..workloads.constants import WORKLOAD_ID_LABEL
from .constants import (
    AIM_API_GROUP,
    AIM_CLUSTER_MODEL_LABEL,
    AIM_CLUSTER_MODEL_PLURAL,
    AIM_CLUSTER_SERVICE_TEMPLATE_PLURAL,
    AIM_SERVICE_PLURAL,
    AIM_SERVICE_RESOURCE,
    CHAT_TAG_VALUE,
    HTTP_ROUTE_API_GROUP,
    HTTP_ROUTE_PLURAL,
    KSERVE_API_GROUP,
    KSERVE_INFERENCE_SERVICE_PLURAL,
)
from .crds import AIMClusterModelResource, AIMClusterServiceTemplateResource, AIMServiceResource, HTTPRouteResource
from .enums import AIMClusterModelStatus
from .enums import AIMServiceStatus as AIMServiceStatusEnum
from .schemas import AIMDeployRequest
from .utils import generate_aim_service_manifest


async def list_aims(
    kube_client: KubernetesClient,
    statuses: list[AIMClusterModelStatus] | None = None,
) -> list[AIMClusterModelResource]:
    """Get all AIMClusterModels from Kubernetes."""
    aim_version = await get_resource_version(AIM_API_GROUP, AIM_CLUSTER_MODEL_PLURAL)
    if not aim_version:
        logger.warning("AIMClusterModel CRD not found in cluster")
        return []

    try:
        result = await kube_client.custom_objects.list_cluster_custom_object(
            group=AIM_API_GROUP,
            version=aim_version,
            plural=AIM_CLUSTER_MODEL_PLURAL,
        )

        aims = []
        for item in result.get("items", []):
            aim = AIMClusterModelResource.model_validate(item)
            aims.append(aim)

        logger.debug(f"Found {len(aims)} AIMClusterModels in cluster")

        # Filter by status if provided
        if statuses:
            aims = [aim for aim in aims if aim.status.status in statuses]

        return aims

    except Exception as e:
        logger.exception(f"Failed to list AIMClusterModels: {e}")
        return []


async def get_aim_by_name(kube_client: KubernetesClient, resource_name: str) -> AIMClusterModelResource | None:
    """Get a specific AIMClusterModel from Kubernetes by resource name."""
    aim_version = await get_resource_version(AIM_API_GROUP, AIM_CLUSTER_MODEL_PLURAL)
    if not aim_version:
        logger.warning("AIMClusterModel CRD not found in cluster")
        return None

    try:
        result = await kube_client.custom_objects.get_cluster_custom_object(
            group=AIM_API_GROUP,
            version=aim_version,
            plural=AIM_CLUSTER_MODEL_PLURAL,
            name=resource_name,
        )

        return AIMClusterModelResource.model_validate(result)

    except Exception as e:
        if hasattr(e, "status") and e.status == 404:
            logger.debug(f"AIMClusterModel {resource_name} not found")
            return None
        logger.exception(f"Failed to get AIMClusterModel {resource_name}: {e}")
        return None


def is_aim_service_chattable(
    aim_service: AIMServiceResource,
    aims_by_name: dict[str, AIMClusterModelResource],
) -> bool:
    """Check if an AIM service is chattable.

    A service is chattable if:
    1. It is in RUNNING status
    2. Its associated AIM has the "chat" tag in its image metadata
    """
    if aim_service.status.status != AIMServiceStatusEnum.RUNNING:
        return False

    aim_name = aim_service.status.resolved_model.name if aim_service.status.resolved_model else None
    if not aim_name:
        return False

    aim_crd = aims_by_name.get(aim_name)
    if not aim_crd:
        logger.debug(f"AIM {aim_name} not found for service {aim_service.metadata.name}")
        return False

    return CHAT_TAG_VALUE in aim_crd.status.image_metadata.model.tags


async def list_aim_services(
    kube_client: KubernetesClient,
    namespace: str,
    chattable_only: bool = False,
    status_filter: list[AIMServiceStatusEnum] | None = None,
) -> list[AIMServiceResource]:
    """List AIMService resources from Kubernetes.

    Args:
        kube_client: Kubernetes client
        namespace: Namespace to search in
        chattable_only: If True, only return RUNNING services with chat-capable AIMs
        status_filter: List of statuses to include in results (if provided)
    """
    version = await get_resource_version(AIM_API_GROUP, AIM_SERVICE_PLURAL)
    if not version:
        logger.warning("AIMService CRD not found in cluster")
        return []

    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=version,
            namespace=namespace,
            plural=AIM_SERVICE_PLURAL,
        )

        httproutes = await _get_httproutes_for_aim_services(kube_client, namespace)
        isvc_names = await _get_isvc_names(kube_client, namespace)
        aims_by_name = await _get_aims_by_name(kube_client) if chattable_only else {}

        aim_services = []
        for item in result.get("items", []):
            try:
                aim_service = AIMServiceResource.model_validate(item)

                # Filter by status inclusions
                if status_filter and aim_service.status.status not in status_filter:
                    continue

                # Apply chattable filter
                if chattable_only and not is_aim_service_chattable(aim_service, aims_by_name):
                    continue

                if aim_service.status.status == AIMServiceStatusEnum.RUNNING:
                    aim_service.httproute = httproutes.get(aim_service.metadata.name)
                    aim_service.inference_service_name = isvc_names.get(aim_service.metadata.name)
                aim_services.append(aim_service)
            except Exception as e:
                logger.error(f"Failed to parse AIMService: {e}")
                continue

        return aim_services

    except Exception as e:
        logger.exception(f"Failed to list AIMServices: {e}")
        return []


async def get_aim_service_by_id(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
) -> AIMServiceResource | None:
    """Get an AIMService by id label."""
    version = await get_resource_version(AIM_API_GROUP, AIM_SERVICE_PLURAL)
    if not version:
        logger.warning("AIMService CRD not found in cluster")
        return None

    try:
        label_selector = f"{WORKLOAD_ID_LABEL}={str(id)}"
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=version,
            namespace=namespace,
            plural=AIM_SERVICE_PLURAL,
            label_selector=label_selector,
        )

        items = result.get("items", [])
        if not items:
            return None

        aim_service = AIMServiceResource.model_validate(items[0])
        if aim_service.status.status == AIMServiceStatusEnum.RUNNING:
            httproutes = await _get_httproutes_for_aim_services(kube_client, namespace)
            isvc_names = await _get_isvc_names(kube_client, namespace)
            aim_service.httproute = httproutes.get(aim_service.metadata.name)
            aim_service.inference_service_name = isvc_names.get(aim_service.metadata.name)
        return aim_service

    except Exception as e:
        logger.exception(f"Failed to get AIMService by id {str(id)}: {e}")
        return None


async def create_aim_service(
    kube_client: KubernetesClient,
    namespace: str,
    aim: AIMClusterModelResource,
    deploy_request: AIMDeployRequest,
    submitter: str,
    service_name: str,
    cluster_auth_group_id: str,
) -> AIMServiceResource:
    """Create an AIMService in Kubernetes.

    Args:
        aim: AIMClusterModel resource if found, None if deploying by image reference that doesn't exist yet
        service_name: The K8s resource name for the AIMService
        cluster_auth_group_id: Cluster-Auth group ID to stamp on the resource
    """
    version = await get_resource_version(AIM_API_GROUP, AIM_SERVICE_PLURAL)
    if not version:
        raise RuntimeError("AIMService CRD not available in cluster")

    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=deploy_request,
        namespace=namespace,
        service_name=service_name,
        api_version=f"{AIM_API_GROUP}/{version}",
        submitter=submitter,
        cluster_auth_group_id=cluster_auth_group_id,
    )

    created = await kube_client.custom_objects.create_namespaced_custom_object(
        group=AIM_API_GROUP,
        version=version,
        namespace=namespace,
        plural=AIM_SERVICE_PLURAL,
        body=manifest,
    )

    return AIMServiceResource.model_validate(created)


async def delete_aim_service(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
) -> str:
    """Delete an AIMService from Kubernetes by id."""
    version = await get_resource_version(AIM_API_GROUP, AIM_SERVICE_PLURAL)
    if not version:
        raise RuntimeError("AIMService CRD not available in cluster")

    service = await get_aim_service_by_id(kube_client, namespace, id)
    if not service:
        raise ValueError(f"No AIMService found with id '{id}' in namespace '{namespace}'")

    # Delete the service
    await kube_client.custom_objects.delete_namespaced_custom_object(
        group=AIM_API_GROUP,
        version=version,
        namespace=namespace,
        plural=AIM_SERVICE_PLURAL,
        name=service.metadata.name,
    )

    return service.metadata.name


async def list_aim_cluster_service_templates(
    kube_client: KubernetesClient,
    model_name: str | None = None,
) -> list[AIMClusterServiceTemplateResource]:
    """
    List AIMClusterServiceTemplate resources from Kubernetes.

    Args:
        kube_client: Kubernetes client
        model_name: Optional filter by model name (matches spec.modelName)

    Returns:
        List of AIMClusterServiceTemplate resources
    """
    version = await get_resource_version(AIM_API_GROUP, AIM_CLUSTER_SERVICE_TEMPLATE_PLURAL)
    if not version:
        logger.warning("AIMClusterServiceTemplate CRD not found in cluster")
        return []

    try:
        # Use label selector to filter by model if provided
        # The controller creates templates with label: aim.eai.amd.com/aim-image: {model-name}
        label_selector = f"{AIM_CLUSTER_MODEL_LABEL}={model_name}" if model_name else None

        result = await kube_client.custom_objects.list_cluster_custom_object(
            group=AIM_API_GROUP,
            version=version,
            plural=AIM_CLUSTER_SERVICE_TEMPLATE_PLURAL,
            label_selector=label_selector,
        )

        templates = []
        for item in result.get("items", []):
            try:
                template = AIMClusterServiceTemplateResource.model_validate(item)
                templates.append(template)
            except Exception as e:
                logger.error(f"Failed to parse AIMClusterServiceTemplate: {e}")
                continue

        logger.debug(f"Found {len(templates)} AIMClusterServiceTemplates for model {model_name or 'all'}")
        return templates

    except Exception as e:
        logger.exception(f"Failed to list AIMClusterServiceTemplates: {e}")
        return []


async def patch_aim_service_scaling_policy(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
    min_replicas: int,
    max_replicas: int,
    auto_scaling: dict[str, Any],
) -> AIMServiceResource:
    """
    Patch the scaling policy of an existing AIMService.

    Updates minReplicas, maxReplicas, and autoScaling configuration
    without modifying other fields. Uses strategic merge patch.

    Note: All three parameters (minReplicas, maxReplicas, autoScaling) are required
    and must be provided together as a unit.

    Args:
        kube_client: Kubernetes client
        namespace: Kubernetes namespace
        id: UUID to identify the AIMService
        min_replicas: Minimum number of replicas (must be >= 1)
        max_replicas: Maximum number of replicas (must be >= min_replicas)
        auto_scaling: Autoscaling configuration dict (required)

    Returns:
        Updated AIMServiceResource

    Raises:
        ValueError: If AIMService not found
        RuntimeError: If AIMService CRD not available
    """
    version = await get_resource_version(AIM_API_GROUP, AIM_SERVICE_PLURAL)
    if not version:
        raise RuntimeError("AIMService CRD not available in cluster")

    service = await get_aim_service_by_id(kube_client, namespace, id)
    if not service:
        raise ValueError(f"No AIMService found with id '{id}' in namespace '{namespace}'")

    # Build the patch payload - scaling policy fields must come together
    # minReplicas, maxReplicas, and autoScaling work as a unit
    # Leave replicas as-is - KEDA will pick the priority
    patch_body: dict = {
        "spec": {
            "minReplicas": min_replicas,
            "maxReplicas": max_replicas,
            "autoScaling": auto_scaling,
        }
    }

    logger.info(f"Patching AIMService {service.metadata.name} scaling policy: min={min_replicas}, max={max_replicas}")

    try:
        patched = await kube_client.custom_objects.patch_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=version,
            namespace=namespace,
            plural=AIM_SERVICE_PLURAL,
            name=service.metadata.name,
            body=patch_body,
            _content_type="application/merge-patch+json",
        )
    except Exception as e:
        logger.exception(f"Failed to patch AIMService {service.metadata.name} scaling policy: {e}")
        raise RuntimeError(f"Failed to update scaling policy for AIMService: {e}") from e

    return AIMServiceResource.model_validate(patched)


async def _get_aims_by_name(
    kube_client: KubernetesClient,
) -> dict[str, AIMClusterModelResource]:
    """Get all AIMClusterModels, indexed by name.

    Single API call to avoid N+1 queries when checking chattable services.
    """
    aims = await list_aims(kube_client)
    return {aim.metadata.name: aim for aim in aims}


async def _get_httproutes_for_aim_services(
    kube_client: KubernetesClient,
    namespace: str,
) -> dict[str, HTTPRouteResource]:
    """Get all HTTPRoutes in a namespace, indexed by their owning AIMService name.

    Single API call to avoid N+1 queries when listing multiple AIMServices.
    """
    version = await get_resource_version(HTTP_ROUTE_API_GROUP, HTTP_ROUTE_PLURAL)
    if not version:
        return {}

    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=HTTP_ROUTE_API_GROUP,
            version=version,
            namespace=namespace,
            plural=HTTP_ROUTE_PLURAL,
        )

        routes: dict[str, HTTPRouteResource] = {}
        for item in result.get("items", []):
            for owner_ref in item.get("metadata", {}).get("ownerReferences", []):
                if (
                    owner_ref.get("kind") == AIM_SERVICE_RESOURCE
                    and owner_ref.get("controller") is True
                    and owner_ref.get("name")
                ):
                    routes[owner_ref["name"]] = HTTPRouteResource.model_validate(item)
                    break
        return routes

    except Exception as e:
        logger.exception(f"Failed to list HTTPRoutes in namespace {namespace}: {e}")
        return {}


async def _get_isvc_names(
    kube_client: KubernetesClient,
    namespace: str,
) -> dict[str, str]:
    """Map AIMService names to their InferenceService names via ownerReferences."""
    version = await get_resource_version(KSERVE_API_GROUP, KSERVE_INFERENCE_SERVICE_PLURAL)
    if not version:
        return {}

    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=KSERVE_API_GROUP, version=version, namespace=namespace, plural=KSERVE_INFERENCE_SERVICE_PLURAL
        )
        mapping: dict[str, str] = {}
        for item in result.get("items", []):
            isvc_name = item.get("metadata", {}).get("name")
            if not isvc_name:
                continue
            for owner in item.get("metadata", {}).get("ownerReferences", []):
                owner_name = owner.get("name")
                if owner_name and owner.get("kind") == AIM_SERVICE_RESOURCE and owner.get("controller"):
                    mapping[owner_name] = isvc_name
                    break
        return mapping
    except Exception as e:
        logger.warning(f"Failed to list InferenceServices in namespace {namespace}: {e}")
        return {}
