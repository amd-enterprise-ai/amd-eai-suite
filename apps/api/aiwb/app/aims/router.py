# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import StreamingResponse
from prometheus_api_client import PrometheusConnect
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_email
from api_common.database import get_session
from api_common.schemas import ListResponse, QueryParam

from ..cluster_auth import get_cluster_auth_client
from ..cluster_auth.client import ClusterAuthClient
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..logs.client import get_loki_client
from ..logs.schemas import LogsQuery, WorkloadLogsResponse
from ..logs.service import get_logs_by_workload_id
from ..metrics.client import get_prometheus_client
from ..metrics.enums import MetricName
from ..metrics.schemas import MetricsScalar, MetricsScalarWithRange, MetricsTimeRange, MetricsTimeseries
from ..metrics.service import get_metric_by_workload_id
from ..namespaces.security import ensure_access_to_workbench_namespace
from .crds import AIMClusterServiceTemplateResource, AIMServiceTemplateResource
from .gateway import list_aim_service_replicas
from .schemas import (
    AIMDeployRequest,
    AIMResponse,
    AIMServiceHistoryResponse,
    AIMServiceListQuery,
    AIMServicePatchRequest,
    AIMServiceReplicaResponse,
    AIMServiceResponse,
    AIMServiceTemplateQuery,
)
from .service import (
    chat_with_aim_service,
    deploy_aim,
    get_aim_by_resource_name,
    get_aim_service,
    list_aim_cluster_service_templates,
    list_aim_services,
    list_aim_services_history,
    list_aims,
    list_chattable_aim_services,
    list_fine_tuned_aim_service_templates,
    undeploy_aim,
    update_aim_scaling_policy,
)

router = APIRouter(tags=["AIMs"])


@router.get(
    "/cluster/aims/models",
    response_model=ListResponse[AIMResponse],
    summary="List AIM cluster models",
    description=dedent("""
        List all available AIM cluster models (AIMClusterModels) from Kubernetes.
    """),
)
async def list_aims_endpoint(
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[AIMResponse]:
    aims = await list_aims(kube_client)
    return ListResponse(data=aims)


@router.get(
    "/cluster/aims/models/{resource_name}",
    response_model=AIMResponse,
    summary="Get an AIM cluster model by resource name",
    description=dedent("""
        Get a specific AIM cluster model (AIMClusterModel) from Kubernetes by its resource name.

        The resource_name is the Kubernetes metadata.name of the AIMClusterModel CRD.
    """),
)
async def get_aim_endpoint(
    resource_name: str = Path(..., description="The Kubernetes resource name of the AIMClusterModel"),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> AIMResponse:
    return await get_aim_by_resource_name(kube_client, resource_name)


@router.get(
    "/cluster/aims/templates",
    response_model=ListResponse[AIMClusterServiceTemplateResource],
    summary="List AIM cluster service templates",
    description=dedent("""
        Get available AIMClusterServiceTemplate resources for a specific AIM cluster model.
        Returns optimization configurations (latency/throughput) with GPU requirements and availability status.
    """),
)
async def list_aim_service_templates_endpoint(
    query: QueryParam[AIMServiceTemplateQuery],
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[AIMClusterServiceTemplateResource]:
    templates = await list_aim_cluster_service_templates(kube_client, query.aim_resource_name)
    return ListResponse(data=templates)


@router.post(
    "/namespaces/{namespace}/aims/services",
    response_model=AIMServiceResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Deploy an AIM",
    description=dedent("""
        Deploy an AIM by creating an AIMService in Kubernetes.

        The `model` field accepts either an AIMClusterModel name (cluster-scoped)
        or an AIMModel name (namespace-scoped fine-tuned model). The API auto-detects which type it is.
    """),
)
async def deploy_aim_endpoint(
    deploy_request: AIMDeployRequest = Body(...),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    submitter: str = Depends(get_user_email),
    kube_client: KubernetesClient = Depends(get_kube_client),
    cluster_auth_client: ClusterAuthClient | None = Depends(get_cluster_auth_client),
) -> AIMServiceResponse:
    return await deploy_aim(
        kube_client=kube_client,
        deploy_request=deploy_request,
        namespace=namespace,
        submitter=submitter,
        cluster_auth_client=cluster_auth_client,
    )


@router.delete(
    "/namespaces/{namespace}/aims/services/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Undeploy an AIM",
    description=dedent("""
        Undeploy an AIM by deleting its AIMService from Kubernetes using service ID.
    """),
)
async def undeploy_aim_endpoint(
    id: UUID = Path(..., description="Service ID (UUID) of the AIM service to undeploy"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
    cluster_auth_client: ClusterAuthClient | None = Depends(get_cluster_auth_client),
) -> None:
    await undeploy_aim(
        kube_client=kube_client,
        namespace=namespace,
        id=id,
        cluster_auth_client=cluster_auth_client,
    )


@router.get(
    "/namespaces/{namespace}/aims/services",
    response_model=ListResponse[AIMServiceResponse],
    summary="List AIMServices",
    description=dedent("""
        Get real-time list of AIMService deployments from Kubernetes.
        This endpoint queries K8s directly and returns current state without database lookup.
        Optionally filter by status.
    """),
)
async def list_aim_services_endpoint(
    query: QueryParam[AIMServiceListQuery],
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[AIMServiceResponse]:
    services = await list_aim_services(kube_client, namespace, status_filter=query.status_filter)
    return ListResponse(data=services)


@router.get(
    "/namespaces/{namespace}/aims/services/chattable",
    response_model=ListResponse[AIMServiceResponse],
    status_code=status.HTTP_200_OK,
    summary="List chattable AIM services",
    description="List AIM services with ready conditions that support chat functionality.",
)
async def get_chattable_aim_services(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[AIMServiceResponse]:
    """List all AIM services that support chat in a namespace."""
    services = await list_chattable_aim_services(kube_client, namespace)
    return ListResponse(data=services)


# NOTE: /history must be defined BEFORE /{id} so FastAPI doesn't match "history" as a UUID
@router.get(
    "/namespaces/{namespace}/aims/services/history",
    response_model=ListResponse[AIMServiceHistoryResponse],
    summary="List historical AIM deployments",
    description=dedent("""
        Get historical AIM service deployments from database.
        Returns all past and current AIM deployment records for analytics and tracking.
    """),
)
async def list_aim_services_history_endpoint(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
) -> ListResponse[AIMServiceHistoryResponse]:
    services = await list_aim_services_history(session, namespace)
    return ListResponse(data=services)


@router.get(
    "/namespaces/{namespace}/aims/services/{id}",
    response_model=AIMServiceResponse,
    summary="Get AIMService",
    description=dedent("""
        Get a single AIMService by ID.
        Validates the ID exists in database (historical records) then fetches live data from Kubernetes.
    """),
)
async def get_aim_service_endpoint(
    id: UUID = Path(description="The UUID of the AIM service"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> AIMServiceResponse:
    return await get_aim_service(kube_client, namespace, id)


@router.post(
    "/namespaces/{namespace}/aims/services/{id}/chat",
    summary="Chat with deployed AIM service",
    description=dedent("""
        Send chat messages to a deployed AIM service for interactive conversations.
        Requires namespace access and a running AIM service.
        Streams responses for real-time chat experience.
    """),
    response_class=StreamingResponse,
    responses={
        200: {"description": "Streaming chat response from the model"},
        404: {"description": "AIM service not found"},
        422: {"description": "AIM service is not running"},
    },
)
async def chat_with_aim_service_endpoint(
    request: Request,
    id: UUID = Path(description="The UUID of the AIM service to chat with"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> StreamingResponse:
    """Chat with a deployed AIM service."""
    return await chat_with_aim_service(
        kube_client=kube_client,
        namespace=namespace,
        id=id,
        request=request,
    )


@router.get(
    "/namespaces/{namespace}/aims/services/{id}/replicas",
    response_model=ListResponse[AIMServiceReplicaResponse],
    status_code=status.HTTP_200_OK,
    summary="List AIM service replicas",
    description=dedent("""
        Return Kubernetes pod data for each replica of an AIM service.
        The response is a fixed schema containing commonly needed pod fields.
    """),
)
async def get_aim_service_replicas_endpoint(
    id: UUID = Path(description="The UUID of the AIM service"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[AIMServiceReplicaResponse]:
    replicas = await list_aim_service_replicas(kube_client, namespace, id)
    return ListResponse(data=[AIMServiceReplicaResponse.model_validate(r) for r in replicas])


@router.get(
    "/namespaces/{namespace}/aims/services/{id}/metrics/{metric}",
    response_model=MetricsTimeseries | MetricsScalar | MetricsScalarWithRange,
    status_code=status.HTTP_200_OK,
    summary="Get a single AIM metric",
    description="Retrieve a single metric for an AIM service by querying Prometheus with service id.",
)
async def get_aim_metric_endpoint(
    id: UUID = Path(description="The UUID of the AIM service"),
    metric: MetricName = Path(description="Metric name to retrieve"),
    time_range: MetricsTimeRange = Depends(),
    pod_name: str | None = Query(
        None,
        alias=to_camel("pod_name"),
        pattern=r"^[a-z0-9][a-z0-9\-\.]{0,252}$",
        description="Optional pod name to scope metrics to a single replica. Omit to aggregate across all replicas.",
    ),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    _: str = Depends(ensure_access_to_workbench_namespace),
) -> MetricsTimeseries | MetricsScalar | MetricsScalarWithRange:
    return await get_metric_by_workload_id(
        workload_id=str(id),
        metric=metric,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
        pod_name=pod_name,
    )


@router.get(
    "/namespaces/{namespace}/aims/services/{id}/logs",
    response_model=WorkloadLogsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AIM logs",
    description="Retrieve logs for a specific AIM service from Loki, with pagination and filtering support.",
)
async def get_aim_logs_endpoint(
    params: QueryParam[LogsQuery],
    id: UUID = Path(description="The UUID of the AIM service"),
    loki_client: object = Depends(get_loki_client),
    _: str = Depends(ensure_access_to_workbench_namespace),
) -> WorkloadLogsResponse:
    """Get logs for an AIM service with optional filtering and pagination."""
    return await get_logs_by_workload_id(
        workload_id=str(id),
        loki_client=loki_client,
        start_date=params.start,
        end_date=params.end,
        page_token=params.page_token,
        limit=params.limit,
        level_filter=params.level,
        log_type=params.log_type,
        direction=params.direction,
    )


@router.patch(
    "/namespaces/{namespace}/aims/services/{id}",
    response_model=AIMServiceResponse,
    summary="Update AIMService",
    description=dedent("""
        Update an existing AIMService deployment.

        Allows modifying the service configuration without redeploying the model.
        Currently supports updating scaling policy (minReplicas, maxReplicas, autoScaling).
    """),
)
async def update_aim_service_endpoint(
    id: UUID = Path(..., description="UUID of the AIM service"),
    patch_request: AIMServicePatchRequest = Body(...),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> AIMServiceResponse:
    # Check if scaling policy update is requested (pydantic validates all three are set together)
    if patch_request.auto_scaling is not None:
        # These asserts are for type narrowing - pydantic model_validator guarantees they're set
        assert patch_request.min_replicas is not None
        assert patch_request.max_replicas is not None
        return await update_aim_scaling_policy(
            kube_client=kube_client,
            namespace=namespace,
            id=id,
            min_replicas=patch_request.min_replicas,
            max_replicas=patch_request.max_replicas,
            auto_scaling=patch_request.auto_scaling,
        )

    # No supported fields provided
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="All scaling fields must be provided: minReplicas, maxReplicas, autoScaling.",
    )


@router.get(
    "/namespaces/{namespace}/models/{model_name}/templates",
    response_model=ListResponse[AIMServiceTemplateResource],
    summary="List AIMServiceTemplates for a fine-tuned model",
    description=dedent("""
        List namespace-scoped AIMServiceTemplates for a fine-tuned model.
        The model_name is the AIMModel CR name in the namespace (equal to the model UUID).
    """),
)
async def get_fine_tuned_aim_service_templates(
    model_name: str = Path(..., description="Fine-tuned model resource name (AIMModel CR name)"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[AIMServiceTemplateResource]:
    templates = await list_fine_tuned_aim_service_templates(
        kube_client=kube_client,
        namespace=namespace,
        model_name=model_name,
    )
    return ListResponse(data=templates)
