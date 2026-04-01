# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Cluster resources router for AIWB API."""

from textwrap import dedent

from fastapi import APIRouter, Depends, status

from ..dispatch.kube_client import KubernetesClient, get_kube_client
from .schemas import ClusterResourcesResponse
from .service import get_cluster_resources as get_cluster_resources_service

router = APIRouter(prefix="/cluster", tags=["Cluster"])


@router.get(
    "/resources",
    response_model=ClusterResourcesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get cluster resources",
    description=dedent("""
        Get available cluster resources including CPU, memory, ephemeral storage, and GPU count.

        This endpoint queries the Kubernetes cluster to determine the total available resources
        across all ready nodes. The resources returned are:

        - **CPU**: Available CPU in milli-cores (1 core = 1000 milli-cores)
        - **Memory**: Available memory in bytes
        - **Ephemeral Storage**: Available ephemeral storage in bytes
        - **GPU Count**: Total number of GPUs available
        - **Total Node Count**: Number of ready nodes in the cluster

        This information can be used by the UI to display resource limits when deploying workloads.
    """),
)
async def get_cluster_resources(
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ClusterResourcesResponse:
    """Get cluster resource availability."""
    return await get_cluster_resources_service(kube_client)
