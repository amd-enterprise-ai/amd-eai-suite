# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from collections import Counter
from uuid import UUID

from loguru import logger
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.collections import SortDirection, paginate_list, sort_list

from ..aims.repository import get_aim_service_by_id
from ..aims.service import list_aim_services, list_chattable_aim_services
from ..dispatch.kube_client import KubernetesClient
from ..metrics.service import get_gpu_utilization_by_workload_in_namespace, get_gpu_vram_by_workload_in_namespace
from ..workloads.constants import ACTIVE_WORKLOAD_STATUSES
from ..workloads.enums import WorkloadStatus, WorkloadType
from ..workloads.repository import get_workloads
from ..workloads.service import list_chattable_workloads
from ..workloads.utils import get_resource_type
from .crds import Namespace
from .gateway import get_namespaces
from .schemas import (
    ChattableResponse,
    NamespaceStatsCounts,
    NamespaceWorkloadMetrics,
    NamespaceWorkloadMetricsListPaginated,
    ResourceStatusCount,
    ResourceType,
)
from .security import is_valid_workbench_namespace
from .utils import AIM_TO_WORKLOAD_STATUS


async def get_accessible_namespaces(
    kube_client: KubernetesClient,
    user_groups: list[str],
) -> list[Namespace]:
    """Get workbench namespaces accessible to the user.

    Single API call, in-memory filtering.
    """
    all_namespaces = await get_namespaces(kube_client)
    return [ns for ns in all_namespaces if is_valid_workbench_namespace(ns, user_groups)]


async def get_chattable_resources(
    kube_client: KubernetesClient,
    session: AsyncSession,
    namespace: str,
) -> ChattableResponse:
    """Get all chattable resources (AIM services + workloads) in a namespace.

    Args:
        kube_client: Kubernetes client for AIM service queries
        session: Database session for workload queries
        namespace: Namespace to search in

    Returns:
        ChattableResponse containing both AIM services and workloads
    """
    aim_services = await list_chattable_aim_services(kube_client, namespace)
    workloads = await list_chattable_workloads(session, namespace)

    return ChattableResponse(
        aim_services=aim_services,
        workloads=workloads,
    )


async def _process_aim_services_to_metrics(
    aim_services_k8s: list,
    session: AsyncSession,
    namespace_name: str,
    gpu_counts: dict[str, int],
    vram_usage: dict[str, float],
) -> list[NamespaceWorkloadMetrics]:
    """Process AIM services from Kubernetes into NamespaceWorkloadMetrics.

    Args:
        aim_services_k8s: List of AIM services from Kubernetes
        session: Database session for fetching AIM service metadata
        namespace_name: Name of the namespace
        gpu_counts: GPU count by workload ID
        vram_usage: VRAM usage by workload ID

    Returns:
        List of NamespaceWorkloadMetrics for AIM services
    """
    metrics: list[NamespaceWorkloadMetrics] = []

    for aim_service in aim_services_k8s:
        aim_service_id = aim_service.id
        if not aim_service_id:
            continue

        try:
            aim_service_uuid = UUID(aim_service_id)
        except (ValueError, TypeError):
            continue

        aim_service_db = await get_aim_service_by_id(session, aim_service_uuid, namespace_name)
        created_at = aim_service_db.created_at if aim_service_db else None
        created_by = aim_service_db.created_by if aim_service_db else None

        status = AIM_TO_WORKLOAD_STATUS.get(aim_service.status.status, WorkloadStatus.UNKNOWN)

        gpu_count = gpu_counts.get(aim_service_id)
        vram = vram_usage.get(aim_service_id)

        display_name = aim_service.metadata.name
        if isinstance(aim_service.spec.model, dict):
            model_metadata = aim_service.spec.model.get("metadata", {})
            if isinstance(model_metadata, dict):
                display_name = model_metadata.get("title") or aim_service.metadata.name

        metrics.append(
            NamespaceWorkloadMetrics(
                id=aim_service_uuid,
                name=aim_service.metadata.name,
                display_name=display_name,
                type=WorkloadType.INFERENCE,
                status=status,
                resource_type=ResourceType.AIM_SERVICE,
                gpu_count=gpu_count,
                vram=vram,
                created_at=created_at,
                created_by=created_by,
            )
        )

    return metrics


async def _process_workloads_to_metrics(
    workloads_db: list,
    gpu_counts: dict[str, int],
    vram_usage: dict[str, float],
) -> list[NamespaceWorkloadMetrics]:
    """Process workloads from database into NamespaceWorkloadMetrics.

    Args:
        workloads_db: List of workloads from database
        gpu_counts: GPU count by workload ID
        vram_usage: VRAM usage by workload ID

    Returns:
        List of NamespaceWorkloadMetrics for workloads
    """
    metrics: list[NamespaceWorkloadMetrics] = []

    for workload in workloads_db:
        workload_id = str(workload.id)
        gpu_count = gpu_counts.get(workload_id)
        vram = vram_usage.get(workload_id)

        try:
            resource_type = get_resource_type(workload.manifest)
        except ValueError:
            resource_type = ResourceType.JOB if workload.type == WorkloadType.FINE_TUNING else ResourceType.DEPLOYMENT
            logger.warning(
                f"Workload {workload_id}: could not parse manifest, falling back to {resource_type} from type"
            )

        metrics.append(
            NamespaceWorkloadMetrics(
                id=workload.id,
                name=workload.name,
                display_name=workload.display_name,
                type=workload.type,
                status=workload.status,
                resource_type=resource_type,
                gpu_count=gpu_count,
                vram=vram,
                created_at=workload.created_at,
                created_by=workload.created_by,
            )
        )

    return metrics


async def get_namespace_workload_metrics_paginated(
    kube_client: KubernetesClient,
    session: AsyncSession,
    namespace: Namespace,
    prometheus_client: PrometheusConnect,
    page: int = 1,
    page_size: int = 20,
    workload_types: list[WorkloadType] | None = None,
    status_filter: list[WorkloadStatus] | None = None,
    sort_by: str | None = None,
    sort_order: SortDirection = SortDirection.desc,
) -> NamespaceWorkloadMetricsListPaginated:
    """Get paginated metrics for all resources in a namespace.

    Combines AIM services and workloads with their metrics.

    Args:
        kube_client: Kubernetes client for AIM service queries
        session: Database session for workload queries
        namespace: Namespace to search in
        prometheus_client: Prometheus client for GPU/VRAM metrics
        page: Page number (1-indexed)
        page_size: Number of items per page
        workload_types: Optional filter by workload type(s)
        status_filter: Optional filter by workload status(es)
        sort_by: Optional field to sort by
        sort_order: Sort direction (asc or desc)
    """
    # Convert user's WorkloadStatus filter to corresponding AIMServiceStatus values
    aim_status_filter = [
        aim for aim, ws in AIM_TO_WORKLOAD_STATUS.items() if status_filter is None or ws in status_filter
    ]
    workload_status_filter = status_filter if status_filter is not None else ACTIVE_WORKLOAD_STATUSES

    # Fetch all data in parallel
    aim_services_k8s, workloads_db, gpu_counts, vram_usage = await asyncio.gather(
        list_aim_services(kube_client, namespace.name, status_filter=aim_status_filter),
        get_workloads(
            session, namespace=namespace.name, workload_types=workload_types, status_filter=workload_status_filter
        ),
        get_gpu_utilization_by_workload_in_namespace(namespace, prometheus_client),
        get_gpu_vram_by_workload_in_namespace(namespace, prometheus_client),
    )

    aim_metrics, workload_metrics = await asyncio.gather(
        _process_aim_services_to_metrics(aim_services_k8s, session, namespace.name, gpu_counts, vram_usage),
        _process_workloads_to_metrics(workloads_db, gpu_counts, vram_usage),
    )

    metrics = aim_metrics + workload_metrics

    # Sort the full filtered data list before pagination
    metrics = sort_list(metrics, sort_by=sort_by, sort_order=sort_order)

    paginated = paginate_list(metrics, page=page, page_size=page_size)

    return NamespaceWorkloadMetricsListPaginated(
        data=paginated.items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


async def get_namespace_stats_counts(
    kube_client: KubernetesClient,
    session: AsyncSession,
    namespace: Namespace,
) -> NamespaceStatsCounts:
    """Get statistics counts for all resources in a namespace.

    Returns aggregated counts of resources (AIM services + workloads) grouped by status.
    This is a lightweight endpoint that only returns counts (no GPU/VRAM metrics).
    """
    # Fetch AIM services and workloads in parallel
    aim_services_k8s, workloads_db = await asyncio.gather(
        list_aim_services(kube_client, namespace.name, status_filter=list(AIM_TO_WORKLOAD_STATUS.keys())),
        get_workloads(session, namespace=namespace.name, status_filter=ACTIVE_WORKLOAD_STATUSES),
    )

    status_counter = Counter[WorkloadStatus]()

    # Count AIM service statuses
    for aim_service in aim_services_k8s:
        if not aim_service.id:
            continue
        status = AIM_TO_WORKLOAD_STATUS.get(aim_service.status.status, WorkloadStatus.UNKNOWN)
        status_counter[status] += 1

    # Count workload statuses (DELETED already filtered at repository)
    for workload in workloads_db:
        status_counter[workload.status] += 1

    # Create status counts list
    status_counts = [
        ResourceStatusCount(status=status, count=count) for status, count in sorted(status_counter.items())
    ]

    return NamespaceStatsCounts(
        namespace=namespace.name,
        total=sum(status_counter.values()),
        status_counts=status_counts,
    )
