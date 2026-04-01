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
from ..workloads.service import stream_downstream
from .constants import CLUSTER_AUTH_GROUP_ANNOTATION
from .crds import AIMClusterServiceTemplateResource
from .enums import AIMClusterModelStatus, AIMServiceStatus
from .gateway import create_aim_service as create_aim_service_in_k8s
from .gateway import delete_aim_service as delete_aim_service_from_k8s
from .gateway import get_aim_by_name
from .gateway import get_aim_service_by_id as get_aim_service_from_k8s
from .gateway import list_aim_cluster_service_templates as get_aim_templates_from_k8s
from .gateway import list_aim_services as get_aim_services_from_k8s
from .gateway import list_aims as get_aims_from_k8s
from .gateway import patch_aim_service_scaling_policy as patch_aim_service_scaling_policy_in_k8s
from .repository import list_aim_services_history as list_aim_services_history_from_db
from .schemas import AIMDeployRequest, AIMResponse, AIMServiceHistoryResponse, AIMServiceResponse
from .utils import generate_aim_service_name

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
    cluster_auth_client: "ClusterAuthClient",
) -> AIMServiceResponse:
    """Deploy an AIM by creating an AIMService CRD in Kubernetes.

    The model field must reference an existing AIMClusterModel by resource name.

    Args:
        kube_client: Kubernetes client
        deploy_request: Deployment request
        namespace: Target namespace
        submitter: User submitting the service
        cluster_auth_client: Cluster-auth client for access control
    """
    # Fetch the AIM by resource name
    aim_model = await get_aim_by_name(kube_client, deploy_request.model)
    if not aim_model:
        raise NotFoundException(f"AIM model '{deploy_request.model}' not found")

    # Validate HF token requirement
    if aim_model.status.image_metadata.model.hf_token_required:
        if not deploy_request.hf_token:
            raise ValidationException("This model requires a Hugging Face token but none was provided")
        # Validate that the secret exists
        await get_secret_details(kube_client, namespace, deploy_request.hf_token)

    # Generate deterministic service name (UUID generated internally)
    aim_service_name = generate_aim_service_name()

    # Create cluster-auth group for this AIM deployment
    group_id = await _create_cluster_auth_group_for_aim(
        cluster_auth_client=cluster_auth_client,
        aim_model_name=aim_model.metadata.name,
        aim_service_name=aim_service_name,
    )

    created = await create_aim_service_in_k8s(
        kube_client=kube_client,
        namespace=namespace,
        aim=aim_model,
        deploy_request=deploy_request,
        submitter=submitter,
        service_name=aim_service_name,
        cluster_auth_group_id=group_id,
    )
    logger.info(f"Created AIMService {aim_service_name} in namespace {namespace}")
    return AIMServiceResponse.model_validate(created, from_attributes=True)


async def undeploy_aim(
    kube_client: KubernetesClient,
    id: UUID,
    namespace: str,
    cluster_auth_client: "ClusterAuthClient",
) -> None:
    """Undeploy an AIM by deleting its AIMService CRD from Kubernetes using service id.

    Args:
        kube_client: Kubernetes client
        id: AIM service ID
        namespace: Target namespace
        cluster_auth_client: Cluster-auth client for access control cleanup
    """
    try:
        # Get the service before deletion to access cluster-auth group annotation
        service = await get_aim_service_from_k8s(kube_client, namespace, id)
        if not service:
            raise NotFoundException(f"AIM service {id} not found in Kubernetes (may be deleted)")

        # Clean up cluster-auth group if it exists
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
    """List all RUNNING AIM services that support chat."""
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
        ValidationException: If AIM service is not running or does not support chat
    """
    aim_service = await get_aim_service_from_k8s(kube_client, namespace, id)
    if not aim_service:
        raise NotFoundException(f"AIM service {id} not found in Kubernetes (may be deleted)")

    # Check if service is chattable (must be RUNNING and have chat tag)
    if aim_service.status.status != AIMServiceStatus.RUNNING:
        raise ValidationException(f"AIM service {id} is not available for chat (status: {aim_service.status.status})")

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
