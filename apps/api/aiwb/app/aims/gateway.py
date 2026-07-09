# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Gateway for accessing AIMClusterModel resources from Kubernetes."""

import asyncio
from typing import Any
from uuid import UUID

from kubernetes_asyncio.client import ApiException
from loguru import logger

from api_common.exceptions import ConflictException, ExternalServiceError

from ..dispatch.kube_client import KubernetesClient
from ..dispatch.utils import get_resource_version
from ..workloads.constants import WORKLOAD_ID_LABEL
from .constants import (
    AIM_API_GROUP,
    AIM_API_VERSION,
    AIM_ARTIFACT_PLURAL,
    AIM_CHATTABLE_CONDITIONS,
    AIM_CLUSTER_MODEL_PLURAL,
    AIM_CLUSTER_PROFILE_PLURAL,
    AIM_COND_HTTP_ROUTE_READY,
    AIM_MODEL_LABEL,
    AIM_MODEL_PLURAL,
    AIM_PROFILE_PLURAL,
    AIM_SERVICE_PLURAL,
    AIM_SERVICE_RESOURCE,
    CHAT_TAG_VALUE,
    FINE_TUNED_LABEL,
    HTTP_ROUTE_API_GROUP,
    HTTP_ROUTE_PLURAL,
    KSERVE_API_GROUP,
    KSERVE_INFERENCE_SERVICE_PLURAL,
    NAMESPACE_AIM_MODEL_LABEL,
)
from .crds import (
    AIMArtifactResource,
    AIMModelResource,
    AIMProfileResource,
    AIMServiceResource,
    HTTPRouteResource,
)
from .enums import AIMModelStatus
from .enums import AIMServiceStatus as AIMServiceStatusEnum
from .schemas import AIMDeployRequest
from .utils import (
    generate_aim_service_manifest,
    generate_namespace_aim_service_manifest,
    is_condition_true,
)


async def list_aims(
    kube_client: KubernetesClient,
    statuses: list[AIMModelStatus] | None = None,
) -> list[AIMModelResource]:
    """Get all AIMClusterModels from Kubernetes."""
    try:
        result = await kube_client.custom_objects.list_cluster_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            plural=AIM_CLUSTER_MODEL_PLURAL,
        )

        aims = []
        for item in result.get("items", []):
            aim = AIMModelResource.model_validate(item)
            aims.append(aim)

        logger.debug(f"Found {len(aims)} AIMClusterModels in cluster")

        # Filter by status if provided
        if statuses:
            aims = [aim for aim in aims if aim.status.status in statuses]

        return aims

    except Exception as e:
        logger.exception(f"Failed to list AIMClusterModels: {e}")
        return []


async def get_aim_by_name(kube_client: KubernetesClient, resource_name: str) -> AIMModelResource | None:
    """Get a specific AIMClusterModel from Kubernetes by resource name."""
    try:
        result = await kube_client.custom_objects.get_cluster_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            plural=AIM_CLUSTER_MODEL_PLURAL,
            name=resource_name,
        )

        return AIMModelResource.model_validate(result)

    except Exception as e:
        if hasattr(e, "status") and e.status == 404:
            logger.debug(f"AIMClusterModel {resource_name} not found")
            return None
        logger.exception(f"Failed to get AIMClusterModel {resource_name}: {e}")
        return None


def is_aim_service_chattable(
    aim_service: AIMServiceResource,
    aims_by_name: dict[str, AIMModelResource],
) -> bool:
    """Check if an AIM service is chattable.

    A service is chattable if:
    1. InferenceServiceReady condition is True (endpoint is reachable)
    2. HTTPRouteReady condition is True (routing is configured)
    3. Either:
       a. Its associated AIMClusterModel has the "chat" tag in its image metadata, OR
       b. It is a namespace AIMModel service (marked with NAMESPACE_AIM_MODEL_LABEL or
          legacy FINE_TUNED_LABEL) — namespace models don't have cluster-scoped
          AIMClusterModels, so their chat capability is inferred from the label instead
          of the model catalog tag.

    Note: We check conditions rather than status.status because a service
    can be in Degraded status while still having a functional inference endpoint.
    """
    conditions = aim_service.status.conditions
    if not all(is_condition_true(conditions, c) for c in AIM_CHATTABLE_CONDITIONS):
        return False

    # Namespace AIMModel services (fine-tuned/custom-onboarded) are chattable
    # if their conditions are ready. They don't have associated AIMClusterModels,
    # so we skip the catalog tag check.
    if NAMESPACE_AIM_MODEL_LABEL in aim_service.metadata.labels or FINE_TUNED_LABEL in aim_service.metadata.labels:
        return True

    aim_name = aim_service.spec.model.get("name")
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
        chattable_only: If True, only return services with ready conditions and chat-capable AIMs
        status_filter: List of statuses to include in results (if provided)
    """
    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_SERVICE_PLURAL,
        )

        httproutes, isvc_names, aims_by_name = await asyncio.gather(
            _get_httproutes_for_aim_services(kube_client, namespace),
            _get_isvc_names(kube_client, namespace),
            _get_aims_by_name(kube_client) if chattable_only else asyncio.sleep(0, result={}),
        )

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

                if is_condition_true(aim_service.status.conditions, AIM_COND_HTTP_ROUTE_READY):
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
    try:
        label_selector = f"{WORKLOAD_ID_LABEL}={str(id)}"
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_SERVICE_PLURAL,
            label_selector=label_selector,
        )

        items = result.get("items", [])
        if not items:
            return None

        aim_service = AIMServiceResource.model_validate(items[0])
        if is_condition_true(aim_service.status.conditions, AIM_COND_HTTP_ROUTE_READY):
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
    aim: AIMModelResource,
    deploy_request: AIMDeployRequest,
    submitter: str,
    service_name: str,
    cluster_auth_group_id: str | None,
    display_name: str | None = None,
) -> AIMServiceResource:
    """Create an AIMService in Kubernetes.

    Args:
        aim: AIMClusterModel resource if found, None if deploying by image reference that doesn't exist yet
        service_name: The K8s resource name for the AIMService
        cluster_auth_group_id: Cluster-Auth group ID to stamp on the resource, or None when disabled
        display_name: Optional user-visible display name stored as annotation
    """
    manifest = generate_aim_service_manifest(
        aim=aim,
        deploy_request=deploy_request,
        namespace=namespace,
        service_name=service_name,
        api_version=f"{AIM_API_GROUP}/{AIM_API_VERSION}",
        submitter=submitter,
        cluster_auth_group_id=cluster_auth_group_id,
        display_name=display_name,
    )

    created = await kube_client.custom_objects.create_namespaced_custom_object(
        group=AIM_API_GROUP,
        version=AIM_API_VERSION,
        namespace=namespace,
        plural=AIM_SERVICE_PLURAL,
        body=manifest,
    )

    return AIMServiceResource.model_validate(created)


async def create_namespace_aim_service(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str,
    deploy_request: AIMDeployRequest,
    submitter: str,
    service_name: str,
    cluster_auth_group_id: str | None,
    display_name: str,
    canonical_name: str,
    is_fine_tuned: bool = True,
    resolved_profile_name: str | None = None,
    deploy_display_name: str | None = None,
) -> AIMServiceResource:
    """Create an AIMService for a namespace-scoped AIMModel.

    ``display_name`` carries the onboarded model's identity (used for
    MODEL_NAME_LABEL/canonical display). ``deploy_display_name`` is the optional
    user-entered name from the deploy request; when present it takes precedence
    for the user-visible display-name annotation.
    """
    manifest = generate_namespace_aim_service_manifest(
        model_name=model_name,
        deploy_request=deploy_request,
        namespace=namespace,
        service_name=service_name,
        api_version=f"{AIM_API_GROUP}/{AIM_API_VERSION}",
        submitter=submitter,
        cluster_auth_group_id=cluster_auth_group_id,
        display_name=display_name,
        canonical_name=canonical_name,
        is_fine_tuned=is_fine_tuned,
        resolved_profile_name=resolved_profile_name,
        deploy_display_name=deploy_display_name,
    )

    created = await kube_client.custom_objects.create_namespaced_custom_object(
        group=AIM_API_GROUP,
        version=AIM_API_VERSION,
        namespace=namespace,
        plural=AIM_SERVICE_PLURAL,
        body=manifest,
    )
    return AIMServiceResource.model_validate(created)


async def create_fine_tuned_aim_service(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str,
    deploy_request: AIMDeployRequest,
    submitter: str,
    service_name: str,
    cluster_auth_group_id: str | None,
    display_name: str,
    canonical_name: str,
) -> AIMServiceResource:
    """Wrapper for namespace-scoped AIMModel fine-tuned deployments."""
    return await create_namespace_aim_service(
        kube_client=kube_client,
        namespace=namespace,
        model_name=model_name,
        deploy_request=deploy_request,
        submitter=submitter,
        service_name=service_name,
        cluster_auth_group_id=cluster_auth_group_id,
        display_name=display_name,
        canonical_name=canonical_name,
        is_fine_tuned=True,
    )


async def delete_aim_service(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
) -> str:
    """Delete an AIMService from Kubernetes by id."""
    service = await get_aim_service_by_id(kube_client, namespace, id)
    if not service:
        raise ValueError(f"No AIMService found with id '{id}' in namespace '{namespace}'")

    # Delete the service
    await kube_client.custom_objects.delete_namespaced_custom_object(
        group=AIM_API_GROUP,
        version=AIM_API_VERSION,
        namespace=namespace,
        plural=AIM_SERVICE_PLURAL,
        name=service.metadata.name,
    )

    return service.metadata.name


async def list_aim_cluster_profiles_by_aim_ids(
    kube_client: KubernetesClient,
    aim_ids: list[str] | None = None,
) -> list[AIMProfileResource]:
    """List AIMClusterProfile resources, optionally filtered by spec.aimId.

    aim-engine declares ``spec.aimId`` in the CRD's ``selectableFields``, so
    multi-id filtering fans out to N parallel API-server calls (field
    selectors are equality-only). ``aim_ids`` is deduped before fan-out.
    """
    selectors: list[str | None] = [f"spec.aimId={aim_id}" for aim_id in dict.fromkeys(aim_ids)] if aim_ids else [None]

    async def fetch(field_selector: str | None) -> list[dict[str, Any]]:
        list_kwargs: dict[str, Any] = {
            "group": AIM_API_GROUP,
            "version": AIM_API_VERSION,
            "plural": AIM_CLUSTER_PROFILE_PLURAL,
        }
        if field_selector is not None:
            list_kwargs["field_selector"] = field_selector
        try:
            result = await kube_client.custom_objects.list_cluster_custom_object(**list_kwargs)
        except ApiException as e:
            logger.error(f"Failed to list AIMClusterProfiles: {e}")
            raise ExternalServiceError(f"Failed to list AIMClusterProfiles: {e.reason}") from e
        return result.get("items", [])

    item_lists = await asyncio.gather(*(fetch(fs) for fs in selectors))

    profiles: list[AIMProfileResource] = []
    for items in item_lists:
        for item in items:
            try:
                profiles.append(AIMProfileResource.model_validate(item))
            except Exception as e:
                logger.error(f"Failed to parse AIMClusterProfile: {e}")

    logger.debug(f"Found {len(profiles)} AIMClusterProfiles for aimIds {aim_ids or 'all'}")
    return profiles


async def get_aim_cluster_profile_by_name(
    kube_client: KubernetesClient,
    name: str,
) -> AIMProfileResource | None:
    """Fetch a single AIMClusterProfile by resource name.

    Direct K8s GET — ``metadata.name`` is always selectable, so no list /
    Python-side filter is needed. Returns ``None`` when the CR does not exist
    so callers can map to a 404 at the router boundary.
    """
    try:
        result = await kube_client.custom_objects.get_cluster_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            plural=AIM_CLUSTER_PROFILE_PLURAL,
            name=name,
        )
    except ApiException as e:
        if e.status == 404:
            return None
        logger.error(f"Failed to get AIMClusterProfile {name}: {e}")
        raise ExternalServiceError(f"Failed to get AIMClusterProfile '{name}': {e.reason}") from e
    return AIMProfileResource.model_validate(result)


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
            version=AIM_API_VERSION,
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


async def list_aim_service_replicas(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
) -> list[dict]:
    """Return raw pod dicts for all pods belonging to an AIM service, sorted by name.

    Pods are fetched from Kubernetes and serialized to camelCase dicts via the K8s
    API client. Schema mapping is left to the router layer.
    """
    label_selector = f"{WORKLOAD_ID_LABEL}={str(id)}"
    try:
        result = await kube_client.core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=label_selector,
        )
        replicas = []
        for pod in result.items:
            if not pod.metadata or not pod.metadata.name:
                continue
            pod_dict: dict = kube_client._api_client.sanitize_for_serialization(pod)
            replicas.append(pod_dict)

        return sorted(replicas, key=lambda r: r["metadata"]["name"])
    except Exception as e:
        logger.exception(f"Failed to list pods for AIM service {id}: {e}")
        return []


async def list_aim_models(
    kube_client: KubernetesClient,
    namespace: str,
    label_selector: str | None = None,
) -> list[AIMModelResource]:
    """List namespace-scoped AIMModel resources from Kubernetes.

    AIMModel CRs are created by the fine-tuning engine when a job completes successfully.
    """
    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_MODEL_PLURAL,
            label_selector=label_selector,
        )

        models = []
        for item in result.get("items", []):
            try:
                model = AIMModelResource.model_validate(item)
                models.append(model)
            except Exception as e:
                logger.error(f"Failed to parse AIMModel: {e}")
                continue

        logger.debug(f"Found {len(models)} AIMModels in namespace {namespace}")
        return models

    except Exception as e:
        logger.exception(f"Failed to list AIMModels in namespace {namespace}: {e}")
        return []


async def _get_aims_by_name(
    kube_client: KubernetesClient,
) -> dict[str, AIMModelResource]:
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


async def get_aim_model(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
) -> AIMModelResource | None:
    """Get a namespace-scoped AIMModel by name."""
    try:
        result = await kube_client.custom_objects.get_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_MODEL_PLURAL,
            name=name,
        )
        return AIMModelResource.model_validate(result)
    except ApiException as e:
        if e.status == 404:
            return None
        raise


async def find_aim_model_by_label(
    kube_client: KubernetesClient,
    namespace: str,
    label_selector: str,
) -> AIMModelResource | None:
    """Find a namespace-scoped AIMModel matching a label selector. Returns the first match or None."""
    result = await kube_client.custom_objects.list_namespaced_custom_object(
        group=AIM_API_GROUP,
        version=AIM_API_VERSION,
        namespace=namespace,
        plural=AIM_MODEL_PLURAL,
        label_selector=label_selector,
    )
    items = result.get("items", [])
    if not items:
        return None
    return AIMModelResource.model_validate(items[0])


async def list_aim_services_for_model(
    kube_client: KubernetesClient,
    namespace: str,
    resource_name: str,
) -> list[AIMServiceResource]:
    """List AIMService CRs in a namespace that reference the given AIMModel by name."""
    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_SERVICE_PLURAL,
        )
        return [
            AIMServiceResource.model_validate(item)
            for item in result.get("items", [])
            if item.get("spec", {}).get("model", {}).get("name") == resource_name
        ]
    except ApiException as e:
        if e.status == 404:
            return []
        raise


async def delete_aim_model(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
) -> None:
    """Delete a namespace-scoped AIMModel CR. No-ops if the resource is missing."""
    try:
        await kube_client.custom_objects.delete_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_MODEL_PLURAL,
            name=name,
        )
        logger.info(f"Deleted AIMModel {name} from namespace {namespace}")
    except ApiException as e:
        if e.status == 404:
            return
        raise


async def create_aim_model(
    kube_client: KubernetesClient,
    namespace: str,
    manifest: dict,
) -> AIMModelResource:
    """Create a namespace-scoped AIMModel CR from a fully composed manifest.

    Sibling of create_aim_service; the manifest is composed by the caller because
    AIMModel covers more onboarding shapes than a single helper would. Translates
    409 from the API server into ConflictException so the FE sees a stable signal
    when a CR with the same name already exists.
    """
    try:
        created = await kube_client.custom_objects.create_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_MODEL_PLURAL,
            body=manifest,
        )
    except ApiException as e:
        if e.status == 409:
            raise ConflictException(
                f"AIMModel '{manifest.get('metadata', {}).get('name')}' already exists in namespace '{namespace}'"
            ) from e
        raise

    return AIMModelResource.model_validate(created)


async def patch_aim_model(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
    patch_body: dict,
) -> AIMModelResource:
    """Patch a namespace-scoped AIMModel CR using merge-patch semantics.

    Non-domain K8s failures wrap as ``ExternalServiceError`` (502). Status
    passthrough via the global ApiException handler is a follow-up — the
    FastAPI app currently only registers ``kubernetes.client.exceptions.ApiException``
    (the sync class), so re-raising the async client's ``kubernetes_asyncio.client.ApiException``
    would fall through to the generic handler and surface as an opaque 500
    rather than the upstream K8s status/body.
    """
    try:
        patched = await kube_client.custom_objects.patch_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_MODEL_PLURAL,
            name=name,
            body=patch_body,
            _content_type="application/merge-patch+json",
        )
    except ApiException as e:
        logger.error(f"Failed to patch AIMModel {name} in namespace {namespace}: {e}")
        raise ExternalServiceError(f"Failed to patch AIMModel '{name}': {e.reason}") from e

    return AIMModelResource.model_validate(patched)


def _is_service_owned_profile(item: dict[str, Any]) -> bool:
    """True if the profile carries an AIMService ownerReference (engine overlay).

    Per ADR 006b §3 the engine materializes ``spec.profileOverrides`` as a
    namespace-scoped AIMProfile copy owned by the originating AIMService.
    These are deployment-internal artifacts; they should not appear in the
    user-facing profile catalog. We distinguish them by the controller
    ownerReference rather than a label so we don't depend on the engine
    setting one.
    """
    for owner_ref in item.get("metadata", {}).get("ownerReferences", []):
        if owner_ref.get("kind") == AIM_SERVICE_RESOURCE:
            return True
    return False


async def list_aim_profiles_by_aim_ids(
    kube_client: KubernetesClient,
    namespace: str,
    aim_ids: list[str] | None = None,
) -> list[AIMProfileResource]:
    """List namespace-scoped AIMProfile resources, optionally filtered by spec.aimId.

    Same field-selector mechanic as the cluster-scoped variant. The
    AIMService-owned overlay exclusion stays client-side — ownerReferences
    are not a selectable field.
    """
    selectors: list[str | None] = [f"spec.aimId={aim_id}" for aim_id in dict.fromkeys(aim_ids)] if aim_ids else [None]

    async def fetch(field_selector: str | None) -> list[dict[str, Any]]:
        list_kwargs: dict[str, Any] = {
            "group": AIM_API_GROUP,
            "version": AIM_API_VERSION,
            "namespace": namespace,
            "plural": AIM_PROFILE_PLURAL,
        }
        if field_selector is not None:
            list_kwargs["field_selector"] = field_selector
        try:
            result = await kube_client.custom_objects.list_namespaced_custom_object(**list_kwargs)
        except ApiException as e:
            logger.error(f"Failed to list AIMProfiles in namespace {namespace}: {e}")
            raise ExternalServiceError(f"Failed to list AIMProfiles in namespace '{namespace}': {e.reason}") from e
        return result.get("items", [])

    item_lists = await asyncio.gather(*(fetch(fs) for fs in selectors))

    profiles: list[AIMProfileResource] = []
    for items in item_lists:
        for item in items:
            if _is_service_owned_profile(item):
                continue
            try:
                profiles.append(AIMProfileResource.model_validate(item))
            except Exception as e:
                logger.error(f"Failed to parse AIMProfile: {e}")

    logger.debug(f"Found {len(profiles)} AIMProfiles for aimIds {aim_ids or 'all'} in {namespace}")
    return profiles


async def get_aim_profile_by_name(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
) -> AIMProfileResource | None:
    """Fetch a single namespace-scoped AIMProfile by resource name.

    Direct K8s GET — ``metadata.name`` is always selectable, so no list /
    Python-side filter is needed. Returns ``None`` when the CR does not exist
    so callers can map to a 404 at the router boundary.
    """
    try:
        result = await kube_client.custom_objects.get_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_PROFILE_PLURAL,
            name=name,
        )
    except ApiException as e:
        if e.status == 404:
            return None
        logger.error(f"Failed to get AIMProfile {name} in namespace {namespace}: {e}")
        raise ExternalServiceError(f"Failed to get AIMProfile '{name}' in namespace '{namespace}': {e.reason}") from e
    return AIMProfileResource.model_validate(result)


async def list_aim_artifacts(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str | None = None,
) -> list[AIMArtifactResource]:
    """List namespace-scoped AIMArtifact resources, optionally filtered to one model.

    AIMArtifacts are created by aim-engine to track weight-import progress.
    The CRD may not yet be installed in older clusters; a 404 from the API
    server is treated as an empty list so callers degrade gracefully.

    Args:
        kube_client: Kubernetes client.
        namespace: Namespace to search in.
        model_name: Optional AIMModel CR name; when provided only the artifact
            for that model is returned (via the ``aim.eai.amd.com/model.name``
            label that aim-engine stamps on every AIMArtifact it creates).

    Returns:
        List of AIMArtifact resources; empty when none exist or the CRD is absent.
    """
    try:
        label_selector = f"{AIM_MODEL_LABEL}={model_name}" if model_name else None
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_ARTIFACT_PLURAL,
            label_selector=label_selector,
        )
        artifacts = []
        for item in result.get("items", []):
            try:
                artifacts.append(AIMArtifactResource.model_validate(item))
            except Exception as e:
                logger.error(f"Failed to parse AIMArtifact: {e}")
                continue
        logger.debug(f"Found {len(artifacts)} AIMArtifacts for model {model_name or 'all'} in {namespace}")
        return artifacts
    except ApiException as e:
        if e.status == 404:
            logger.debug(f"AIMArtifact CRD not found in namespace {namespace}; treating as empty")
            return []
        logger.exception(f"Failed to list AIMArtifacts in namespace {namespace}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Failed to list AIMArtifacts in namespace {namespace}: {e}")
        return []
