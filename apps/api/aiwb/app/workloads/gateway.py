# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Gateway for accessing workload resources from Kubernetes."""

import asyncio

from kubernetes_asyncio.client import ApiException
from loguru import logger

from ..dispatch.kube_client import get_dynamic_client
from .constants import WORKLOAD_ID_LABEL, WORKLOAD_RESOURCES


async def delete_workload_resources(
    namespace: str,
    workload_id: str,
) -> None:
    """Delete all Kubernetes resources with the workload-id label.

    Deletes Deployments, Jobs, and any supporting resources (ConfigMaps, Services, HTTPRoutes)
    created by AIWB workload manifests.

    Raises:
        RuntimeError: If any resource deletion fails (excluding 404 not found)
    """
    label_selector = f"{WORKLOAD_ID_LABEL}={workload_id}"

    dynamic_client = await asyncio.to_thread(get_dynamic_client)

    for resource in WORKLOAD_RESOURCES:
        try:
            await asyncio.to_thread(
                dynamic_client.resources.get(api_version=resource.api_version, kind=resource.kind).delete,
                namespace=namespace,
                label_selector=label_selector,
            )
            logger.debug(f"Deleted {resource.plural} with label {label_selector} from namespace {namespace}")
        except ApiException as e:
            if e.status == 404:
                logger.debug(f"No {resource.plural} found with label {label_selector}")
            else:
                logger.error(f"Failed to delete {resource.plural}: {e}")
                raise RuntimeError(
                    f"Failed to delete Kubernetes resources for workload {workload_id}. Please try again. Error: {e}"
                ) from e

    logger.info(f"Deleted all resources for workload {workload_id} in namespace {namespace}")
