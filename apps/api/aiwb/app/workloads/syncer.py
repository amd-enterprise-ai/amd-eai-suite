# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workload syncer for polling framework."""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..dispatch.kube_client import KubernetesClient
from .config import WORKLOAD_UPDATE_GRACE_PERIOD
from .constants import (
    DEPLOYMENT_RESOURCE_PLURAL,
    JOB_RESOURCE_PLURAL,
    WORKLOAD_ID_LABEL,
)
from .enums import WorkloadStatus
from .models import Workload
from .repository import get_workloads
from .utils import derive_deployment_status, derive_job_status


async def _get_workload_status(
    kube_client: KubernetesClient, workload_id: str, namespace: str
) -> tuple[WorkloadStatus | None, str | None]:
    """Get the status from the workload's Deployment or Job in Kubernetes.

    Checks Deployments first (higher precedence), then Jobs.
    Returns a tuple of (status, resource_type) where resource_type is 'deployments' or 'jobs'.
    Returns (None, None) if no resource exists.
    """
    label_selector = f"{WORKLOAD_ID_LABEL}={workload_id}"

    try:
        deployments = await kube_client.apps_v1.list_namespaced_deployment(
            namespace=namespace,
            label_selector=label_selector,
        )
        if deployments.items:
            return derive_deployment_status(deployments.items[0].status), DEPLOYMENT_RESOURCE_PLURAL
    except Exception:
        logger.exception(f"Error reading deployment status for workload {workload_id}")

    try:
        jobs = await kube_client.batch_v1.list_namespaced_job(
            namespace=namespace,
            label_selector=label_selector,
        )
        if jobs.items:
            return derive_job_status(jobs.items[0].status), JOB_RESOURCE_PLURAL
    except Exception:
        logger.exception(f"Error reading job status for workload {workload_id}")

    return None, None


async def _update_workload_status_from_k8s(
    session: AsyncSession, workload: Workload, kube_client: KubernetesClient
) -> str | None:
    """Update workload status based on Kubernetes resource state.

    Reads status from Deployments/Jobs and updates the database accordingly.
    If no resource exists and the workload is not already DELETED, mark it as DELETED.

    Returns the resource type if a resource was found, None otherwise.
    """
    workload_id = str(workload.id)

    workload = await session.merge(workload)

    new_status, resource_type = await _get_workload_status(kube_client, workload_id, workload.namespace)

    if new_status:
        try:
            if workload.status != new_status:
                logger.info(
                    f"Updating workload {workload_id} status: {workload.status} -> {new_status} "
                    f"(resource: {resource_type})"
                )
                if new_status == WorkloadStatus.DELETED:
                    if datetime.now(UTC) < workload.created_at + timedelta(seconds=WORKLOAD_UPDATE_GRACE_PERIOD):
                        logger.debug(
                            f"Workload {workload_id} marked as DELETED too soon after creation; "
                            f"keeping status as {workload.status}"
                        )
                        return resource_type
                workload.status = new_status
                await session.flush()
        except Exception as e:
            logger.warning(f"Error updating status for workload {workload_id}: {e}")
        return resource_type
    else:
        if workload.status != WorkloadStatus.DELETED:
            logger.info(f"Resource not found for workload {workload_id} - marking as DELETED")
            workload.status = WorkloadStatus.DELETED
            await session.flush()
        return None


async def sync_workloads(session: AsyncSession, kube_client: KubernetesClient) -> None:
    """Synchronize workload statuses with Kubernetes cluster state.

    Reads status from Deployments/Jobs and updates the database.
    If a resource no longer exists and the workload is not already DELETED, marks it as DELETED.
    """
    workloads = await get_workloads(session)
    if not workloads:
        return

    resource_counts = {DEPLOYMENT_RESOURCE_PLURAL: 0, JOB_RESOURCE_PLURAL: 0}

    for workload in workloads:
        try:
            resource_type = await _update_workload_status_from_k8s(session, workload, kube_client)
            if resource_type:
                resource_counts[resource_type] += 1
        except Exception:
            logger.exception(f"Error synchronizing workload {workload.id}")

    await session.commit()

    logger.debug(
        f"Workload sync: {resource_counts[DEPLOYMENT_RESOURCE_PLURAL]} deployments, "
        f"{resource_counts[JOB_RESOURCE_PLURAL]} jobs in K8s"
    )
