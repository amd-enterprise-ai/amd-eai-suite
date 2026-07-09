# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Service layer for AIMs - handles business logic for AIM deployment and management."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from kubernetes_asyncio.client import ApiException
from loguru import logger

from api_common.exceptions import ExternalServiceError, NotFoundException, ValidationException

from ..custom_models.constants import IMPORT_ERROR_ANNOTATION, IMPORT_STATE_ANNOTATION
from ..custom_models.enums import OnboardPhase
from ..custom_models.gateway import find_aim_profile_for_model
from ..dispatch.kube_client import KubernetesClient
from ..secrets.service import get_secret_details
from ..workloads.constants import DISPLAY_NAME_ANNOTATION, MODEL_NAME_LABEL, MODEL_SOURCE_TYPE_LABEL
from ..workloads.enums import ModelSourceType
from .constants import AIM_MODEL_LABEL, CLUSTER_AUTH_GROUP_ANNOTATION
from .crds import AIMProfileResource
from .enums import AcceleratorType, AIMModelStatus, AIMServiceStatus
from .gateway import create_aim_service as create_aim_service_in_k8s
from .gateway import create_namespace_aim_service as create_namespace_aim_service_in_k8s
from .gateway import delete_aim_service as delete_aim_service_from_k8s
from .gateway import get_aim_by_name
from .gateway import get_aim_cluster_profile_by_name as get_aim_cluster_profile_from_k8s
from .gateway import get_aim_model as get_aim_model_from_k8s
from .gateway import get_aim_profile_by_name as get_aim_profile_from_k8s
from .gateway import get_aim_service_by_id as get_aim_service_from_k8s
from .gateway import list_aim_cluster_profiles_by_aim_ids as get_aim_cluster_profiles_from_k8s
from .gateway import list_aim_profiles_by_aim_ids as get_aim_profiles_from_k8s
from .gateway import list_aim_services as get_aim_services_from_k8s
from .gateway import list_aims as get_aims_from_k8s
from .gateway import patch_aim_service_scaling_policy as patch_aim_service_scaling_policy_in_k8s
from .schemas import (
    AIMDeployRequest,
    AIMResponse,
    AIMServiceResponse,
)
from .utils import generate_aim_service_name

if TYPE_CHECKING:
    from ..cluster_auth.client import ClusterAuthClient


# AIMDeployRequest fields the namespace AIMModel path does not accept.
# profile_name would bypass AIMModel-driven profile resolution. image_pull_secrets and
# hf_token are only honored for cluster-scoped AIMClusterModel deployments — namespace
# models materialize weights into object storage ahead of time and drive profile resolution
# through the AIMModel CR, so neither caller-supplied images nor HF credentials are needed
# at deploy time. Selector criteria and profileOverrides may still be sent on the request
# but are ignored when a ready namespace AIMProfile is pinned onto the manifest.
_NAMESPACE_MODEL_DISALLOWED_FIELDS = (
    "profile_name",
    "image_pull_secrets",
    "hf_token",
)


async def _create_cluster_auth_group_for_aim(
    cluster_auth_client: "ClusterAuthClient",
    aim_model_name: str,
    aim_service_name: str,
) -> str:
    """Create cluster-auth group for AIM deployment.

    Args:
        cluster_auth_client: Cluster-auth client
        aim_model_name: AIMClusterModel resource name
        aim_service_name: AIMService name (K8s resource name)

    Returns:
        Group ID

    Raises:
        Exception: If group creation fails
    """
    group_name = f"{aim_model_name}-{aim_service_name}"

    group_result = await cluster_auth_client.create_group(name=group_name)
    group_id = group_result["id"]
    logger.info(f"Created cluster-auth group {group_id} for AIM deployment {aim_service_name}")
    return group_id


async def _delete_cluster_auth_group_for_aim(
    cluster_auth_client: "ClusterAuthClient",
    group_id: str,
    aim_service_name: str,
) -> None:
    """Delete cluster-auth group for AIM deployment.

    Args:
        cluster_auth_client: Cluster-auth client
        group_id: Group ID to delete
        aim_service_name: AIMService name for logging
    """
    await cluster_auth_client.delete_group(group_id)
    logger.info(f"Deleted cluster-auth group {group_id} for AIM deployment {aim_service_name}")


async def list_aims(
    kube_client: KubernetesClient,
    statuses: list[AIMModelStatus] | None = None,
    accelerator_type: list[AcceleratorType] | None = None,
) -> list[AIMResponse]:
    """List all AIMs from Kubernetes.

    When ``accelerator_type`` is set, an AIM matches when any entry of its
    ``status.discoveredProfiles.byHardware[]`` has an accelerator family in
    the requested set. AIMs whose engine has not yet published a hardware
    breakdown (``discoveredProfiles`` is ``None`` or has an empty
    ``byHardware``) are excluded when the filter is set — consistent with
    the prior single-value behavior of dropping AIMs without accelerator
    metadata. The engine's ``accelerator_type`` is a raw string; the filter
    matches by comparing against the enum's ``.value``.
    """
    aims_crds = await get_aims_from_k8s(kube_client, statuses)
    aims = [AIMResponse.model_validate(crd.model_dump()) for crd in aims_crds]
    if accelerator_type:
        requested = {at.value for at in accelerator_type}
        aims = [
            aim
            for aim in aims
            if aim.status.discovered_profiles is not None
            and any(h.accelerator_type in requested for h in aim.status.discovered_profiles.by_hardware)
        ]
    return aims


async def get_aim_by_resource_name(
    kube_client: KubernetesClient,
    resource_name: str,
) -> AIMResponse:
    """Get a specific AIM from Kubernetes by resource name.

    Args:
        kube_client: Kubernetes client
        resource_name: The Kubernetes resource name of the AIMClusterModel

    Returns:
        AIMResponse containing the AIMClusterModel data

    Raises:
        NotFoundException: If AIMClusterModel not found
    """
    aim_crd = await get_aim_by_name(kube_client, resource_name)
    if not aim_crd:
        raise NotFoundException(f"AIM with resource name '{resource_name}' not found")

    return AIMResponse.model_validate(aim_crd.model_dump())


async def deploy_aim(
    kube_client: KubernetesClient,
    deploy_request: AIMDeployRequest,
    namespace: str,
    submitter: str,
    cluster_auth_client: "ClusterAuthClient | None",
) -> AIMServiceResponse:
    """Deploy an AIM by creating an AIMService CRD in Kubernetes.

    Auto-detects the model type: tries AIMClusterModel (cluster-scoped) first,
    then falls back to AIMModel (namespace-scoped fine-tuned model).

    Args:
        kube_client: Kubernetes client
        deploy_request: Deployment request
        namespace: Target namespace
        submitter: User submitting the service
        cluster_auth_client: Cluster-auth client for access control, or None when disabled
    """
    aim_service_name = generate_aim_service_name()
    group_id: str | None = None

    # Try cluster-scoped AIMClusterModel first
    aim_cluster_model = await get_aim_by_name(kube_client, deploy_request.model)
    if aim_cluster_model:
        if aim_cluster_model.status.image_metadata.model.hf_token_required:
            if not deploy_request.hf_token:
                raise ValidationException("This model requires a Hugging Face token but none was provided")
            await get_secret_details(kube_client, namespace, deploy_request.hf_token)

        # Create cluster-auth group for this AIM deployment (only when cluster-auth is enabled)
        if cluster_auth_client is not None:
            group_id = await _create_cluster_auth_group_for_aim(
                cluster_auth_client=cluster_auth_client,
                aim_model_name=aim_cluster_model.metadata.name,
                aim_service_name=aim_service_name,
            )

        created = await create_aim_service_in_k8s(
            kube_client=kube_client,
            namespace=namespace,
            aim=aim_cluster_model,
            deploy_request=deploy_request,
            submitter=submitter,
            service_name=aim_service_name,
            cluster_auth_group_id=group_id,
            display_name=deploy_request.display_name,
        )
        logger.info(f"Created AIMService {aim_service_name} in namespace {namespace}")
        return AIMServiceResponse.model_validate(created, from_attributes=True)

    # Fall back to namespace-scoped AIMModel (fine-tuned/custom-onboarded)
    aim_model = await get_aim_model_from_k8s(kube_client, namespace, deploy_request.model)
    if aim_model:
        is_custom_model = _is_custom_onboarded_model(aim_model)
        offending = [
            AIMDeployRequest.model_fields[name].alias or name
            for name in _NAMESPACE_MODEL_DISALLOWED_FIELDS
            if getattr(deploy_request, name) is not None
        ]
        if offending:
            raise ValidationException(
                "Namespace model deployments do not accept an explicit profile name, image pull secrets, or "
                f"Hugging Face token; remove: {', '.join(offending)}"
            )

        resolved_profile = await _resolve_namespace_deploy_profile(
            kube_client=kube_client,
            namespace=namespace,
            model_name=deploy_request.model,
            aim_model=aim_model,
            is_custom_model=is_custom_model,
        )
        resolved_profile_name = resolved_profile.metadata.name if resolved_profile else None

        # Create cluster-auth group for this AIM deployment (only when cluster-auth is enabled)
        if cluster_auth_client is not None:
            group_id = await _create_cluster_auth_group_for_aim(
                cluster_auth_client=cluster_auth_client,
                aim_model_name=deploy_request.model,
                aim_service_name=aim_service_name,
            )
        created = await create_namespace_aim_service_in_k8s(
            kube_client=kube_client,
            namespace=namespace,
            model_name=deploy_request.model,
            deploy_request=deploy_request,
            submitter=submitter,
            service_name=aim_service_name,
            cluster_auth_group_id=group_id,
            display_name=_extract_namespace_model_display_name(aim_model),
            canonical_name=_extract_namespace_model_canonical_name(aim_model),
            is_fine_tuned=not is_custom_model,
            resolved_profile_name=resolved_profile_name,
            deploy_display_name=deploy_request.display_name,
        )
        logger.info(
            f"Created AIMService {aim_service_name} for namespace model {deploy_request.model} in namespace {namespace}"
        )
        return AIMServiceResponse.model_validate(created, from_attributes=True)

    raise NotFoundException(
        f"Model '{deploy_request.model}' not found as AIMClusterModel or AIMModel in namespace '{namespace}'"
    )


async def undeploy_aim(
    kube_client: KubernetesClient,
    id: UUID,
    namespace: str,
    cluster_auth_client: "ClusterAuthClient | None",
) -> None:
    """Undeploy an AIM by deleting its AIMService CRD from Kubernetes using service id.

    Args:
        kube_client: Kubernetes client
        id: AIM service ID
        namespace: Target namespace
        cluster_auth_client: Cluster-auth client for access control cleanup, or None when disabled
    """
    try:
        # Get the service before deletion to access cluster-auth group annotation
        service = await get_aim_service_from_k8s(kube_client, namespace, id)
        if not service:
            raise NotFoundException(f"AIM service {id} not found in Kubernetes (may be deleted)")

        # Clean up cluster-auth group if cluster-auth is enabled and a group was created
        if cluster_auth_client is not None:
            routing_annotations = service.spec.routing.get("annotations", {})
            group_id = routing_annotations.get(CLUSTER_AUTH_GROUP_ANNOTATION)
            if group_id:
                await _delete_cluster_auth_group_for_aim(
                    cluster_auth_client=cluster_auth_client,
                    group_id=group_id,
                    aim_service_name=service.metadata.name,
                )

        service_name = await delete_aim_service_from_k8s(kube_client, namespace, id)
        logger.info(f"Deleted AIMService {service_name} (id: {id}) from namespace {namespace}")
    except ValueError as e:
        raise NotFoundException(str(e))


async def list_aim_services(
    kube_client: KubernetesClient,
    namespace: str,
    status_filter: list[AIMServiceStatus] | None = None,
) -> list[AIMServiceResponse]:
    """List all AIMServices from Kubernetes.

    Returns the raw service status. Consumers that need the resolved
    AIMProfile/AIMClusterProfile spec must fetch the profile catalog from
    the profile endpoints and join client-side by ``status.resolvedProfile.name``.
    """
    services_crds = await get_aim_services_from_k8s(kube_client, namespace, status_filter=status_filter)
    return [AIMServiceResponse.model_validate(crd, from_attributes=True) for crd in services_crds]


async def get_aim_service(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
) -> AIMServiceResponse:
    """Get a single AIMService by ID."""
    service = await get_aim_service_from_k8s(kube_client, namespace, id)
    if not service:
        raise NotFoundException(f"AIM service {id} not found in Kubernetes (may be deleted)")
    return AIMServiceResponse.model_validate(service, from_attributes=True)


async def list_chattable_aim_services(
    kube_client: KubernetesClient,
    namespace: str,
) -> list[AIMServiceResponse]:
    """List all AIM services with ready conditions that support chat."""
    services_crds = await get_aim_services_from_k8s(kube_client, namespace, chattable_only=True)
    return [AIMServiceResponse.model_validate(crd, from_attributes=True) for crd in services_crds]


async def list_aim_cluster_profiles(
    kube_client: KubernetesClient,
    aim_ids: list[str] | None = None,
) -> list[AIMProfileResource]:
    """List AIMClusterProfile resources, optionally filtered by ``spec.aimId``.

    Returns an empty list when no profiles match. Callers that need to
    distinguish "no profiles" from "model unknown" should do so via the
    model endpoints — this listing does not validate the existence of any
    AIMClusterModel.
    """
    return await get_aim_cluster_profiles_from_k8s(kube_client, aim_ids=aim_ids)


async def get_aim_cluster_profile(
    kube_client: KubernetesClient,
    name: str,
) -> AIMProfileResource:
    """Fetch a single AIMClusterProfile by resource name.

    Used by callers that already know the exact profile name (e.g. from
    ``AIMService.status.resolvedProfile.name``) and want a targeted lookup
    instead of the aimId-keyed batched list.

    Raises:
        NotFoundException: When no AIMClusterProfile with that name exists.
    """
    profile = await get_aim_cluster_profile_from_k8s(kube_client, name)
    if profile is None:
        raise NotFoundException(f"AIMClusterProfile '{name}' not found")
    return profile


async def update_aim_scaling_policy(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
    min_replicas: int,
    max_replicas: int,
    auto_scaling: dict[str, Any],
) -> AIMServiceResponse:
    """
    Update scaling policy on an existing AIM deployment.

    This directly patches the AIMService resource in Kubernetes with the new
    scaling configuration. No redeployment is required.

    Args:
        kube_client: Kubernetes client
        namespace: Kubernetes namespace
        id: UUID of the AIMService
        min_replicas: Minimum number of replicas
        max_replicas: Maximum number of replicas
        auto_scaling: Autoscaling configuration dict

    Returns:
        Updated AIMServiceResponse

    Raises:
        NotFoundException: If AIMService not found
        ExternalServiceError: If Kubernetes API call fails
    """
    try:
        updated_service = await patch_aim_service_scaling_policy_in_k8s(
            kube_client=kube_client,
            namespace=namespace,
            id=id,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            auto_scaling=auto_scaling,
        )
        logger.info(
            f"Updated scaling policy for AIMService {updated_service.metadata.name}: "
            f"min={min_replicas}, max={max_replicas}"
        )
        return AIMServiceResponse.model_validate(updated_service.model_dump())
    except ValueError as e:
        raise NotFoundException(str(e))
    except RuntimeError as e:
        raise ExternalServiceError(str(e))


async def list_aim_profiles(
    kube_client: KubernetesClient,
    namespace: str,
    aim_ids: list[str] | None = None,
) -> list[AIMProfileResource]:
    """List namespace-scoped AIMProfile resources, optionally filtered by ``spec.aimId``.

    Returns an empty list when no profiles match. Like the cluster-scoped
    variant, this listing does not validate that any AIMModel CR exists in
    the namespace.
    """
    return await get_aim_profiles_from_k8s(kube_client, namespace, aim_ids=aim_ids)


async def get_aim_profile(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
) -> AIMProfileResource:
    """Fetch a single namespace-scoped AIMProfile by resource name.

    Targeted lookup variant of ``list_aim_profiles`` — used when the caller
    already knows the exact profile name (e.g. fine-tuned model detail page
    joining ``AIMService.status.resolvedProfile.name``).

    Raises:
        NotFoundException: When no AIMProfile with that name exists in the
            namespace.
    """
    profile = await get_aim_profile_from_k8s(kube_client, namespace, name)
    if profile is None:
        raise NotFoundException(f"AIMProfile '{name}' not found in namespace '{namespace}'")
    return profile


def _is_custom_onboarded_model(aim_model: Any) -> bool:
    labels = aim_model.metadata.labels or {}
    return labels.get(MODEL_SOURCE_TYPE_LABEL) == ModelSourceType.CUSTOM


def _extract_namespace_model_display_name(aim_model: Any) -> str:
    annotations = aim_model.metadata.annotations or {}
    labels = aim_model.metadata.labels or {}
    return annotations.get(DISPLAY_NAME_ANNOTATION) or labels.get(MODEL_NAME_LABEL, "")


def _extract_namespace_model_canonical_name(aim_model: Any) -> str:
    model_sources = aim_model.spec.model_sources or []
    if model_sources:
        return model_sources[0].model_id
    profiles = aim_model.spec.profiles
    overrides = profiles.overrides if profiles else None
    if overrides and overrides.model_id:
        return overrides.model_id
    if overrides and overrides.model_sources:
        return overrides.model_sources[0].model_id
    return ""


async def _resolve_namespace_deploy_profile(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str,
    aim_model: Any,
    *,
    is_custom_model: bool,
) -> AIMProfileResource | None:
    """Resolve the namespace AIMProfile to pin on an AIMService manifest.

    Custom models require a Ready AIMModel and Ready namespace AIMProfile and
    always pin that profile. Runtime settings are configured via model settings
    and written to the AIMProfile manifest at onboard/edit time — the deploy
    request does not carry profile selector or override fields.

    Fine-tuned and other namespace models pin the same profile when aim-engine
    has emitted a Ready one; otherwise deploy-time selectors/overrides or
    engine auto-resolution apply. Profile lookup failures fall back to that path
    for non-custom models; custom model lookup failures raise ExternalServiceError.
    """
    try:
        profile = await find_aim_profile_for_model(kube_client, namespace, model_name)
    except ApiException as e:
        if is_custom_model:
            raise ExternalServiceError(
                f"Failed to look up AIMProfile for custom model '{model_name}': {e.reason}"
            ) from e
        logger.warning(
            "Namespace AIMProfile lookup failed for model {} in {}; continuing without pinned profile",
            model_name,
            namespace,
        )
        return None
    profile_status = str(profile.status.status) if profile and profile.status and profile.status.status else ""

    if not is_custom_model:
        if profile is not None and profile_status == AIMModelStatus.READY:
            return profile
        return None

    annotations = aim_model.metadata.annotations or {}
    import_state = annotations.get(IMPORT_STATE_ANNOTATION)
    if import_state == OnboardPhase.FAILED:
        import_error = annotations.get(IMPORT_ERROR_ANNOTATION)
        reason = f": {import_error}" if import_error else "."
        raise ValidationException(
            f"Custom model '{model_name}' is not deployable: weight import failed{reason} Re-import the model before deploying."
        )
    if import_state and import_state not in (OnboardPhase.READY, OnboardPhase.FAILED):
        raise ValidationException(
            f"Custom model '{model_name}' is not deployable yet: weight import is still in progress."
        )

    model_status = str(aim_model.status.status) if (aim_model.status and aim_model.status.status) else ""
    if model_status != AIMModelStatus.READY:
        raise ValidationException(
            f"Custom model '{model_name}' is not deployable yet: AIMModel status is '{model_status or 'Unknown'}', expected 'Ready'."
        )
    if profile is None:
        raise ValidationException(
            f"Custom model '{model_name}' is not deployable yet: no namespace AIMProfile was found for this model. "
            f"Expected an AIMProfile labeled {AIM_MODEL_LABEL}={model_name}. "
            "If the AIMModel is Ready but no profile is listed, check aim-engine reconciliation for that model."
        )
    if profile_status != AIMModelStatus.READY:
        raise ValidationException(
            f"Custom model '{model_name}' is not deployable yet: AIMProfile '{profile.metadata.name}' status is "
            f"'{profile_status or 'Unknown'}', expected 'Ready'."
        )
    return profile
