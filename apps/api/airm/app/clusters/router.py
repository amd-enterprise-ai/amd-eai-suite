# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..metrics.schemas import (
    GpuDeviceSingleMetricResponse,
    MetricsTimeRange,
    MetricsTimeseries,
    NodeGpuDevicesResponse,
    NodeWorkloadsWithMetrics,
    WorkloadsWithMetrics,
)
from ..metrics.service import (
    get_gpu_device_utilization_timeseries_for_cluster as get_gpu_device_utilization_timeseries_for_cluster_from_ds,
)
from ..metrics.service import (
    get_node_gpu_clock_speed,
    get_node_gpu_devices_with_metrics,
    get_node_gpu_junction_temperature,
    get_node_gpu_memory_temperature,
    get_node_gpu_utilization,
    get_node_gpu_vram_utilization,
    get_node_power_usage,
    get_pcie_bandwidth_timeseries_for_node,
    get_pcie_efficiency_timeseries_for_node,
    get_prometheus_client,
    get_workloads_metrics_by_cluster,
    get_workloads_metrics_by_node,
)
from ..projects.models import Project
from ..projects.schemas import (
    ProjectsWithResourceAllocation,
)
from ..projects.service import (
    get_projects_in_cluster_with_resource_allocation,
)
from ..utilities.collections.dependencies import (
    get_filter_query_params,
    get_pagination_query_params,
    get_sort_query_params,
)
from ..utilities.collections.schemas import FilterCondition, PaginationConditions, SortCondition
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException
from ..utilities.keycloak_admin import (
    KeycloakAdmin,
    get_kc_admin,
)
from ..utilities.security import (
    Roles,
    auth_token_claimset,
    ensure_platform_administrator,
    ensure_user_can_view_cluster,
    get_projects_accessible_to_user,
    get_user_email,
    is_user_in_role,
)
from ..workloads.schemas import WorkloadStatusStats
from ..workloads.service import get_status_stats_for_workloads_in_cluster
from .schemas import (
    ClusterIn,
    ClusterKubeConfig,
    ClusterNodeResponse,
    ClusterNodes,
    Clusters,
    ClustersStats,
    ClusterWithResources,
    ClusterWithUserSecret,
)
from .service import create_cluster as create_cluster_and_queues
from .service import delete_cluster as delete_cluster_from_db
from .service import (
    get_cluster_and_node_by_ids,
    get_cluster_by_id,
    get_cluster_kubeconfig_as_yaml,
    get_cluster_with_resources,
    get_clusters_accessible_to_user_with_resources,
    get_clusters_with_resources,
    get_stats_for_clusters_accessible_to_user,
    validate_cluster_accessible_to_user,
)
from .service import get_cluster_node as get_cluster_node_from_db
from .service import get_cluster_nodes as get_cluster_nodes_in_db
from .service import get_clusters_stats as get_clusters_stats_from_db
from .service import update_cluster as update_cluster_service

router = APIRouter(tags=["Clusters"])


@router.post(
    "/clusters",
    operation_id="create_cluster",
    summary="Create a new cluster",
    description="""
        Create a new GPU cluster for AI/ML workloads. Requires platform administrator
        role. Sets up infrastructure needed for running containerized workloads like
        training jobs, inference services, and development environments.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClusterWithUserSecret,
)
async def create_cluster(
    _: None = Depends(ensure_platform_administrator),
    user: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    cluster_create: ClusterIn = Body(description="The cluster data to create"),
) -> ClusterWithUserSecret:
    return await create_cluster_and_queues(session, creator=user, cluster_create=cluster_create)


@router.get(
    "/clusters/stats",
    operation_id="get_clusters_stats",
    summary="Get stats for all clusters",
    description="""
        Retrieve aggregate statistics across all GPU clusters including total nodes,
        GPU counts, and resource utilization summaries. Platform administrators see statistics for
        all clusters. Regular users see statistics only for clusters accessible through their project memberships.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClustersStats,
)
async def get_clusters_stats(
    session: AsyncSession = Depends(get_session),
    claimset: dict = Depends(auth_token_claimset),
) -> ClustersStats:
    if is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        return await get_clusters_stats_from_db(session)
    else:
        accessible_projects = await get_projects_accessible_to_user(claimset, session)
        return await get_stats_for_clusters_accessible_to_user(session, accessible_projects)


@router.get(
    "/clusters",
    operation_id="get_clusters",
    summary="List all accessible clusters",
    description="""
        List GPU clusters accessible to the authenticated user. Platform administrators
        see all clusters with detailed resource information. Regular users see only clusters
        accessible through project memberships.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Clusters,
)
async def get_clusters(
    session: AsyncSession = Depends(get_session),
    claimset: dict = Depends(auth_token_claimset),
) -> Clusters:
    if is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        return await get_clusters_with_resources(session)
    else:
        accessible_projects = await get_projects_accessible_to_user(claimset, session)
        return await get_clusters_accessible_to_user_with_resources(session, accessible_projects)


@router.get(
    "/clusters/{cluster_id}",
    operation_id="get_cluster",
    summary="Get detailed cluster information",
    description="""
        Get detailed information about a specific cluster including resource allocation,
        node details, and workload distribution. Requires either platform administrator role
        or the user must belong to a project on the cluster.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClusterWithResources,
)
async def get_cluster(
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to be retrieved"),
    claimset: dict = Depends(auth_token_claimset),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
) -> ClusterWithResources:
    if not is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        await validate_cluster_accessible_to_user(accessible_projects, cluster_id)
    cluster = await get_cluster_by_id(session, cluster_id)
    return await get_cluster_with_resources(session, cluster)


@router.put(
    "/clusters/{cluster_id}",
    operation_id="update_cluster",
    summary="Update a cluster by ID",
    description="""
        Update cluster configuration including name, description, and resource settings.
        Requires platform administrator role. Modifies cluster metadata without affecting
        running workloads.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClusterWithResources,
)
async def update_cluster(
    _: None = Depends(ensure_platform_administrator),
    user: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to be updated"),
    cluster_update: ClusterIn = Body(description="The cluster data to update"),
) -> ClusterWithResources:
    cluster = await get_cluster_by_id(session, cluster_id)
    updated_cluster = await update_cluster_service(session, cluster, cluster_update, user)
    return await get_cluster_with_resources(session, updated_cluster)


@router.delete(
    "/clusters/{cluster_id}",
    operation_id="delete_cluster",
    summary="Delete a cluster by ID",
    description="""
        Remove a cluster from the platform. Requires platform administrator role.
        Deletes cluster configuration and associated metadata. Running workloads
        should be terminated before cluster deletion.
    """,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cluster(
    _: None = Depends(ensure_platform_administrator),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to be deleted"),
) -> None:
    cluster = await get_cluster_by_id(session, cluster_id)
    await delete_cluster_from_db(session, cluster)


@router.get(
    "/clusters/{cluster_id}/kube-config",
    operation_id="get_kube_config",
    summary="Get the kubeconfig for the cluster as YAML string",
    description="""
        Get the kubeconfig for accessing a specific cluster. This kubeconfig uses OIDC
        authentication via Keycloak with kubectl oidc-login plugin. The response contains
        a YAML string that can be displayed in the UI or saved as a file.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClusterKubeConfig,
)
async def get_cluster_kubeconfig(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
    cluster_id: UUID = Path(description="The ID of the cluster to get kubeconfig for"),
) -> ClusterKubeConfig:
    cluster = await get_cluster_by_id(session, cluster_id)
    return await get_cluster_kubeconfig_as_yaml(cluster, kc_admin)


@router.get(
    "/clusters/{cluster_id}/nodes",
    operation_id="get_cluster_nodes",
    summary="Get all nodes for a cluster",
    description="""
        List all compute nodes in a specific cluster with hardware details including
        GPU type, count, memory, and current status.
        Requires either platform administrator role or the user must belong to a project on the cluster.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClusterNodes,
)
async def get_cluster_nodes(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to get nodes for"),
) -> ClusterNodes:
    cluster = await get_cluster_by_id(session, cluster_id)
    return await get_cluster_nodes_in_db(session, cluster)


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}",
    operation_id="get_cluster_node",
    summary="Get a node for a cluster",
    description="""
        Get a single compute node in a specific cluster with hardware details including
        GPU type, count, memory, and current status.
        Requires either platform administrator role or the user must belong to a project on the cluster.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClusterNodeResponse,
)
async def get_cluster_node(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster"),
    node_id: UUID = Path(description="The ID of the node"),
) -> ClusterNodeResponse:
    cluster = await get_cluster_by_id(session, cluster_id)
    return await get_cluster_node_from_db(session, cluster, node_id)


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/pcie/bandwidth",
    operation_id="get_node_pcie_bandwidth_timeseries",
    summary="Get PCIe bandwidth timeseries for a cluster node",
    description="""
        Retrieve PCIe bandwidth usage over time for each GPU on a specific node.
        Supports time range via start/end query parameters (e.g. 1h, 24h, 7d).
        Requires either platform administrator role or the user must belong to a project on the cluster.
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_pcie_bandwidth(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster"),
    node_id: UUID = Path(description="The ID of the node"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_pcie_bandwidth_timeseries_for_node(
        cluster_name=cluster.name,
        node_hostname=node.name,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/pcie/efficiency",
    operation_id="get_node_pcie_efficiency_timeseries",
    summary="Get PCIe efficiency timeseries for a cluster node",
    description="""
        Retrieve PCIe efficiency (link speed / max speed as percentage) over time for each GPU on a specific node.
        Supports time range via start/end query parameters (e.g. 1h, 24h, 7d).
        Requires either platform administrator role or the user must belong to a project on the cluster.
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_pcie_efficiency(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster"),
    node_id: UUID = Path(description="The ID of the node"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_pcie_efficiency_timeseries_for_node(
        cluster_name=cluster.name,
        node_hostname=node.name,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/projects",
    operation_id="get_cluster_projects",
    summary="Get projects for the cluster",
    description="""
        Get all projects in a specific cluster with resource allocation information.
        Shows GPU allocation, CPU allocation with percentages, and memory allocation with percentages.
        Requires either platform administrator role or the user must belong to a project on the cluster.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ProjectsWithResourceAllocation,
)
async def get_cluster_projects(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster for which to retrieve projects"),
) -> ProjectsWithResourceAllocation:
    cluster = await get_cluster_by_id(session, cluster_id)

    return await get_projects_in_cluster_with_resource_allocation(session, cluster)


@router.get(
    "/clusters/{cluster_id}/workloads/stats",
    operation_id="get_cluster_workload_stats",
    summary="Get workload statistics for a specific cluster",
    description="""
        Retrieve workload statistics for a specific cluster, including counts
        grouped by workload status (running, pending, failed, complete, etc.).
        Similar to project-level stats but aggregated across all projects in the cluster.
    """,
    status_code=status.HTTP_200_OK,
    response_model=WorkloadStatusStats,
)
async def get_cluster_workload_stats(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster from which to retrieve workload statistics"),
) -> WorkloadStatusStats:
    cluster = await get_cluster_by_id(session, cluster_id)
    if not cluster:
        raise NotFoundException(f"Cluster with ID {cluster_id} not found.")

    return await get_status_stats_for_workloads_in_cluster(session, cluster)


@router.get(
    "/clusters/{cluster_id}/workloads/metrics",
    operation_id="get_cluster_workloads_metrics",
    summary="Get cluster workload metrics",
    description="""
        Retrieve comprehensive metrics for all workloads in a specific cluster.
        Includes resource usage, execution times, and performance statistics.
        Essential for cluster-level resource optimization and workload analysis.
    """,
    status_code=status.HTTP_200_OK,
    response_model=WorkloadsWithMetrics,
)
async def get_cluster_workloads_metrics(
    _: None = Depends(ensure_platform_administrator),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The unique ID of the cluster to retrieve workloads for"),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    pagination_params: PaginationConditions = Depends(get_pagination_query_params),
    sort_params: list[SortCondition] = Depends(get_sort_query_params),
    filter_params: list[FilterCondition] = Depends(get_filter_query_params),
) -> WorkloadsWithMetrics:
    cluster = await get_cluster_by_id(session, cluster_id)
    if not cluster:
        raise NotFoundException("Cluster not found")

    return await get_workloads_metrics_by_cluster(
        session,
        cluster.id,
        cluster.name,
        prometheus_client,
        pagination_params,
        sort_params,
        filter_params,
    )


@router.get(
    "/clusters/{cluster_id}/metrics/gpu_device_utilization",
    operation_id="get_gpu_device_utilization_timeseries_for_cluster",
    summary="Get cluster GPU utilization timeseries",
    description="""
        Retrieve GPU compute utilization metrics for a specific cluster over time.
        Shows aggregate GPU usage across all workloads running on the cluster.
        Essential for cluster capacity planning and performance monitoring.
    """,
    status_code=status.HTTP_200_OK,
    response_model=MetricsTimeseries,
)
async def get_gpu_device_utilization_timeseries_for_cluster(
    _: None = Depends(ensure_user_can_view_cluster),
    cluster_id: UUID = Path(description="The ID of the cluster for which to return metrics"),
    time_range: MetricsTimeRange = Depends(),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries:
    cluster = await get_cluster_by_id(session, cluster_id)
    if not cluster:
        raise NotFoundException("Cluster not found")

    return await get_gpu_device_utilization_timeseries_for_cluster_from_ds(
        session=session,
        start=time_range.start,
        end=time_range.end,
        cluster_name=cluster.name,
        prometheus_client=prometheus_client,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/core-utilization",
    operation_id="get_node_gpu_utilization",
    summary="Get per-GPU core utilization timeseries for a cluster node",
    description="""
        Retrieve GPU core activity (gpu_gfx_activity) percentage over time for each
        GPU device on the specified node. Returns per-device timeseries data.
        Requires cluster view access (platform administrator or project membership on the cluster).
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_gpu_utilization_metrics(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get GPU utilization metrics for"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_node_gpu_utilization(
        node_name=node.name,
        cluster_name=cluster.name,
        prometheus_client=prometheus_client,
        start=time_range.start,
        end=time_range.end,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/memory-utilization",
    operation_id="get_node_gpu_memory_utilization",
    summary="Get per-GPU VRAM utilization timeseries for a cluster node",
    description="""
        Retrieve GPU VRAM utilization percentage over time for each GPU device on the specified node.
        Returns per-device timeseries data calculated as (used_vram / total_vram) * 100.
        Requires cluster view access (platform administrator or project membership on the cluster).
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_gpu_memory_utilization_metrics(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get GPU memory utilization metrics for"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_node_gpu_vram_utilization(
        node_name=node.name,
        cluster_name=cluster.name,
        prometheus_client=prometheus_client,
        start=time_range.start,
        end=time_range.end,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/gpu-utilization/clock-speed",
    operation_id="get_node_gpu_clock_speed",
    summary="Get per-GPU system clock speed timeseries for a cluster node",
    description="""
        Retrieve GPU system clock speed (MHz) over time for each GPU device on the specified node.
        Returns per-device timeseries data using the GPU_CLOCK_TYPE_SYSTEM clock type.
        Requires cluster view access (platform administrator or project membership on the cluster).
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_gpu_clock_speed_metrics(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get GPU clock speed metrics for"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_node_gpu_clock_speed(
        node_name=node.name,
        cluster_name=cluster.name,
        prometheus_client=prometheus_client,
        start=time_range.start,
        end=time_range.end,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/power-usage",
    operation_id="get_node_power_usage",
    summary="Get per-GPU power usage timeseries for a cluster node",
    description="""
        Retrieve GPU power draw (watts) over time for each GPU device on the specified node.
        Returns per-device timeseries data from the gpu_package_power Prometheus metric.
        Requires cluster view access (platform administrator or project membership on the cluster).
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_power_usage_metrics(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get GPU power usage metrics for"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_node_power_usage(
        node_name=node.name,
        cluster_name=cluster.name,
        prometheus_client=prometheus_client,
        start=time_range.start,
        end=time_range.end,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/junction",
    operation_id="get_node_gpu_junction_temperature",
    summary="Get per-GPU junction temperature timeseries for a cluster node",
    description="""
        Retrieve GPU junction temperature (Celsius) over time for each GPU device on the specified node.
        Returns per-device timeseries data from the gpu_junction_temperature Prometheus metric.
        Requires cluster view access (platform administrator or project membership on the cluster).
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_junction_temperature_metrics(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get GPU junction temperature metrics for"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_node_gpu_junction_temperature(
        node_name=node.name,
        cluster_name=cluster.name,
        prometheus_client=prometheus_client,
        start=time_range.start,
        end=time_range.end,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/metrics/temperature/memory",
    operation_id="get_node_gpu_memory_temperature",
    summary="Get per-GPU memory temperature timeseries for a cluster node",
    description="""
        Retrieve GPU memory temperature (Celsius) over time for each GPU device on the specified node.
        Returns per-device timeseries data from the gpu_memory_temperature Prometheus metric.
        Requires cluster view access (platform administrator or project membership on the cluster).
    """,
    status_code=status.HTTP_200_OK,
    response_model=GpuDeviceSingleMetricResponse,
)
async def get_node_memory_temperature_metrics(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get GPU memory temperature metrics for"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> GpuDeviceSingleMetricResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_node_gpu_memory_temperature(
        node_name=node.name,
        cluster_name=cluster.name,
        prometheus_client=prometheus_client,
        start=time_range.start,
        end=time_range.end,
        step=time_range.step,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/gpu-devices",
    operation_id="get_node_gpu_devices",
    summary="Get latest GPU device metrics for a cluster node",
    description="""
        Retrieve the most recent snapshot of per-GPU device metrics on the specified node,
        including junction temperature, power consumption, VRAM utilization, and health status.
        Requires cluster view access (platform administrator or project membership on the cluster).
    """,
    status_code=status.HTTP_200_OK,
    response_model=NodeGpuDevicesResponse,
)
async def get_node_gpu_devices_metrics(
    _: None = Depends(ensure_user_can_view_cluster),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get GPU device metrics for"),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> NodeGpuDevicesResponse:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_node_gpu_devices_with_metrics(
        node_name=node.name,
        cluster_name=cluster.name,
        gpu_product_name=node.gpu_product_name,
        prometheus_client=prometheus_client,
    )


@router.get(
    "/clusters/{cluster_id}/nodes/{node_id}/workloads/metrics",
    operation_id="get_node_workloads_metrics",
    summary="Get workload metrics for a cluster node",
    description="""
        Retrieve workloads that have GPU activity on the specified node, including
        per-workload GPU device assignments across the entire cluster. Useful for
        understanding which workloads consume resources on a node and which GPU
        devices they span.
        Restricted to platform administrators, as workloads may span projects the requesting
        user does not belong to.
    """,
    status_code=status.HTTP_200_OK,
    response_model=NodeWorkloadsWithMetrics,
)
async def get_node_workloads_metrics(
    _: None = Depends(ensure_platform_administrator),
    session: AsyncSession = Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster the node belongs to"),
    node_id: UUID = Path(description="The ID of the node to get workload metrics for"),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> NodeWorkloadsWithMetrics:
    cluster, node = await get_cluster_and_node_by_ids(session, cluster_id, node_id)

    return await get_workloads_metrics_by_node(
        session=session,
        cluster_id=cluster.id,
        cluster_name=cluster.name,
        node_name=node.name,
        prometheus_client=prometheus_client,
    )
