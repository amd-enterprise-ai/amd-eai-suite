# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Service layer for AIMs - handles business logic for AIM deployment and management."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ExternalServiceError, NotFoundException, ValidationException

from ..dispatch.kube_client import KubernetesClient
from ..secrets.service import get_secret_details
from ..workloads.constants import MODEL_NAME_LABEL
from ..workloads.service import stream_downstream
from .constants import (
    AIM_CHATTABLE_CONDITIONS,
    CLUSTER_AUTH_GROUP_ANNOTATION,
)
from .crds import AIMClusterServiceTemplateResource, AIMServiceTemplateResource
from .enums import AIMClusterModelStatus, AIMServiceStatus
from .gateway import create_aim_service as create_aim_service_in_k8s
from .gateway import create_fine_tuned_aim_service as create_fine_tuned_aim_service_in_k8s
from .gateway import delete_aim_service as delete_aim_service_from_k8s
from .gateway import get_aim_by_name
from .gateway import get_aim_model as get_aim_model_from_k8s
from .gateway import get_aim_service_by_id as get_aim_service_from_k8s
from .gateway import list_aim_cluster_service_templates as get_aim_templates_from_k8s
from .gateway import list_aim_service_templates as get_aim_service_templates_from_k8s
from .gateway import list_aim_services as get_aim_services_from_k8s
from .gateway import list_aims as get_aims_from_k8s
from .gateway import patch_aim_service_scaling_policy as patch_aim_service_scaling_policy_in_k8s
from .repository import list_aim_services_history as list_aim_services_history_from_db
from .schemas import (
    AIMDeployRequest,
    AIMResponse,
    AIMServiceHistoryResponse,
    AIMServiceResponse,
)
from .utils import generate_aim_service_name, is_condition_true

if TYPE_CHECKING:
    from ..cluster_auth.client import ClusterAuthClient


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
    statuses: list[AIMClusterModelStatus] | None = None,
) -> list[AIMResponse]:
    """List all AIMs from Kubernetes."""
    aims_crds = await get_aims_from_k8s(kube_client, statuses)
    return [AIMResponse.model_validate(crd.model_dump()) for crd in aims_crds]


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
        )
        logger.info(f"Created AIMService {aim_service_name} in namespace {namespace}")
        return AIMServiceResponse.model_validate(created, from_attributes=True)

    # Fall back to namespace-scoped AIMModel (fine-tuned)
    aim_model = await get_aim_model_from_k8s(kube_client, namespace, deploy_request.model)
    if aim_model:
        # Create cluster-auth group for this AIM deployment (only when cluster-auth is enabled)
        if cluster_auth_client is not None:
            group_id = await _create_cluster_auth_group_for_aim(
                cluster_auth_client=cluster_auth_client,
                aim_model_name=deploy_request.model,
                aim_service_name=aim_service_name,
            )
        labels = aim_model.metadata.labels or {}
        model_sources = aim_model.spec.model_sources or []
        created = await create_fine_tuned_aim_service_in_k8s(
            kube_client=kube_client,
            namespace=namespace,
            model_name=deploy_request.model,
            deploy_request=deploy_request,
            submitter=submitter,
            service_name=aim_service_name,
            cluster_auth_group_id=group_id,
            display_name=labels.get(MODEL_NAME_LABEL, ""),
            canonical_name=model_sources[0].model_id if model_sources else "",
        )
        logger.info(
            f"Created AIMService {aim_service_name} for fine-tuned model {deploy_request.model} in namespace {namespace}"
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
    """List all AIMServices from Kubernetes."""
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


async def list_aim_services_history(
    session: AsyncSession,
    namespace: str,
) -> list[AIMServiceHistoryResponse]:
    """List historical AIM service deployments from database."""
    services = await list_aim_services_history_from_db(session, namespace)
    return [AIMServiceHistoryResponse.model_validate(s) for s in services]


async def list_chattable_aim_services(
    kube_client: KubernetesClient,
    namespace: str,
) -> list[AIMServiceResponse]:
    """List all AIM services with ready conditions that support chat."""
    services_crds = await get_aim_services_from_k8s(kube_client, namespace, chattable_only=True)
    return [AIMServiceResponse.model_validate(crd, from_attributes=True) for crd in services_crds]


async def chat_with_aim_service(
    kube_client: KubernetesClient,
    namespace: str,
    id: UUID,
    request: Request,
) -> StreamingResponse:
    """Chat with a deployed AIM service.

    Raises:
        NotFoundException: If AIM service is not found
        ValidationException: If AIM service conditions are not ready (InferenceServiceReady, HTTPRouteReady)
    """
    aim_service = await get_aim_service_from_k8s(kube_client, namespace, id)
    if not aim_service:
        raise NotFoundException(f"AIM service {id} not found in Kubernetes (may be deleted)")

    conditions = aim_service.status.conditions
    failed = [c for c in AIM_CHATTABLE_CONDITIONS if not is_condition_true(conditions, c)]
    if failed:
        raise ValidationException(
            f"AIM service {id} is not available for chat (conditions not ready: {', '.join(failed)})"
        )

    aim_service_response = AIMServiceResponse.model_validate(aim_service, from_attributes=True)
    base_url = aim_service_response.endpoints.get("internal")

    if not base_url:
        raise ValidationException(f"No endpoint available for AIM service {id}")

    return await stream_downstream(base_url=base_url, request=request)


async def list_aim_cluster_service_templates(
    kube_client: KubernetesClient,
    aim_resource_name: str,
) -> list[AIMClusterServiceTemplateResource]:
    """
    List AIMClusterServiceTemplate resources for a specific AIM."""
    aim_crd = await get_aim_by_name(kube_client, aim_resource_name)
    if not aim_crd:
        raise NotFoundException(f"AIM '{aim_resource_name}' not found")

    templates = await get_aim_templates_from_k8s(kube_client, model_name=aim_resource_name)
    if not templates:
        raise NotFoundException(f"No service templates found for AIM '{aim_resource_name}'")

    return templates


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


async def list_fine_tuned_aim_service_templates(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str,
) -> list[AIMServiceTemplateResource]:
    """List namespace-scoped AIMServiceTemplates for a fine-tuned model.

    Raises:
        NotFoundException: If the AIMModel CR is not found in the namespace.
    """
    aim_model = await get_aim_model_from_k8s(kube_client, namespace, model_name)
    if not aim_model:
        raise NotFoundException(f"Fine-tuned model '{model_name}' not found in namespace '{namespace}'")
    return await get_aim_service_templates_from_k8s(kube_client, namespace, model_name=model_name)
