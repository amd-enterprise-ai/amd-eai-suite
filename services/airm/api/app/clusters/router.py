# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from pydantic import AwareDatetime

from ..metrics.schemas import MetricsTimeseries
from ..metrics.service import (
    get_gpu_device_utilization_timeseries_for_cluster as get_gpu_device_utilization_timeseries_for_cluster_from_ds,
)
from ..metrics.service import (
    get_prometheus_client,
)
from ..metrics.utils import validate_datetime_range
from ..projects.models import Project
from ..projects.schemas import (
    ProjectsWithResourceAllocation,
)
from ..projects.service import (
    get_projects_in_cluster_with_resource_allocation,
)
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException
from ..utilities.security import (
    Roles,
    auth_token_claimset,
    ensure_platform_administrator,
    get_projects_accessible_to_user,
    get_user_email,
    get_user_organization,
    is_user_in_role,
)
from ..workloads.schemas import WorkloadsStats
from ..workloads.service import get_stats_for_workloads_in_cluster
from .repository import get_cluster_in_organization
from .schemas import (
    ClusterIn,
    ClusterNodes,
    Clusters,
    ClustersStats,
    ClusterWithResources,
    ClusterWithUserSecret,
)
from .service import create_cluster as create_cluster_and_queues
from .service import delete_cluster as delete_cluster_for_organization
from .service import (
    get_cluster_by_id,
    get_cluster_with_resources,
    get_clusters_with_resources,
    validate_cluster_accessible_to_user,
)
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
    status_code=status.HTTP_201_CREATED,
    response_model=ClusterWithUserSecret,
)
async def create_cluster(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    user=Depends(get_user_email),
    session=Depends(get_session),
    cluster_create: ClusterIn = Body(description="The cluster data to create"),
) -> ClusterWithUserSecret:
    return await create_cluster_and_queues(
        session, organization_id=organization.id, creator=user, cluster_create=cluster_create
    )


@router.get(
    "/clusters/stats",
    operation_id="get_clusters_stats",
    summary="Get stats for all clusters in an organization",
    status_code=status.HTTP_200_OK,
    response_model=ClustersStats,
)
async def get_clusters_stats(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
) -> ClustersStats:
    return await get_clusters_stats_from_db(session=session, organization_id=organization.id)


@router.get(
    "/clusters",
    operation_id="get_clusters",
    summary="List all available clusters",
    description="""
        List GPU clusters accessible to the authenticated user. Platform administrators
        see all organization clusters with detailed resource information. Regular users
        see only clusters accessible through project memberships.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Clusters,
)
async def get_clusters(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
) -> Clusters:
    return await get_clusters_with_resources(session, organization)


@router.get(
    "/clusters/{cluster_id}",
    operation_id="get_cluster",
    summary="Get detailed cluster information",
    description="""
        Get detailed information about a specific cluster including resource allocation,
        node details, and workload distribution. Requires either platform administrator role
        or the user must belong to a project on the cluster, and cluster must exist in
        user's organization.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ClusterWithResources,
)
async def get_cluster(
    organization=Depends(get_user_organization),
    session=Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to be retrieved"),
    claimset=Depends(auth_token_claimset),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
) -> ClusterWithResources:
    if not is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        await validate_cluster_accessible_to_user(accessible_projects, cluster_id)
    cluster = await get_cluster_by_id(session, organization.id, cluster_id)
    return await get_cluster_with_resources(session, cluster)


@router.put(
    "/clusters/{cluster_id}",
    operation_id="update_cluster",
    summary="Update a cluster by ID",
    status_code=status.HTTP_200_OK,
    response_model=ClusterWithResources,
)
async def update_cluster(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    user=Depends(get_user_email),
    session=Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to be updated"),
    cluster_update: ClusterIn = Body(description="The cluster data to update"),
) -> ClusterWithResources:
    cluster = await get_cluster_by_id(session, organization.id, cluster_id)
    updated_cluster = await update_cluster_service(session, cluster, cluster_update, user)
    return await get_cluster_with_resources(session, updated_cluster)


@router.delete(
    "/clusters/{cluster_id}",
    operation_id="delete_cluster",
    summary="Delete a cluster by ID",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cluster(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to be deleted"),
) -> None:
    cluster = await get_cluster_by_id(session, organization.id, cluster_id)
    await delete_cluster_for_organization(session, cluster)


@router.get(
    "/clusters/{cluster_id}/nodes",
    operation_id="get_cluster_nodes",
    summary="Get all nodes for a cluster",
    status_code=status.HTTP_200_OK,
    response_model=ClusterNodes,
)
async def get_cluster_nodes(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster to get nodes for"),
) -> ClusterNodes:
    cluster = await get_cluster_by_id(session, organization.id, cluster_id)
    return await get_cluster_nodes_in_db(session, cluster)


@router.get(
    "/clusters/{cluster_id}/projects",
    operation_id="get_cluster_projects",
    summary="Get projects for the cluster",
    description="""
        Get all projects in a specific cluster with resource allocation information.
        Shows GPU allocation, CPU allocation with percentages, and memory allocation with percentages.
        Requires platform administrator role.
    """,
    status_code=status.HTTP_200_OK,
    response_model=ProjectsWithResourceAllocation,
)
async def get_cluster_projects(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster for which to retrieve projects"),
) -> ProjectsWithResourceAllocation:
    cluster = await get_cluster_by_id(session, organization.id, cluster_id)

    return await get_projects_in_cluster_with_resource_allocation(session, cluster)


@router.get(
    "/clusters/{cluster_id}/workloads/stats",
    operation_id="get_cluster_workload_stats",
    summary="Get workload stats for the cluster",
    status_code=status.HTTP_200_OK,
    response_model=WorkloadsStats,
)
async def get_cluster_workload_stats(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
    cluster_id: UUID = Path(description="The ID of the cluster from which to retrieve workload stats"),
) -> WorkloadsStats:
    cluster = await get_cluster_in_organization(session, organization.id, cluster_id)
    if not cluster:
        raise NotFoundException(f"Cluster with ID {cluster_id} not found in your organization")

    return await get_stats_for_workloads_in_cluster(session, cluster)


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
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    cluster_id: UUID = Path(description="The ID of the cluster for which to return metrics"),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsTimeseries:
    cluster = await get_cluster_in_organization(session, organization.id, cluster_id)
    if not cluster:
        raise NotFoundException("Cluster not found")

    validate_datetime_range(start, end)

    return await get_gpu_device_utilization_timeseries_for_cluster_from_ds(
        session=session,
        start=start,
        end=end,
        cluster_name=cluster.name,
        organization_id=organization.id,
        prometheus_client=prometheus_client,
    )
