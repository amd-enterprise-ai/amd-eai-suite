# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Kubernetes configuration loader - following dispatcher pattern."""

import os

from kubernetes_asyncio import config as k8s_config
from loguru import logger

# Kubernetes-specific config
USE_LOCAL_KUBE_CONTEXT = os.getenv("USE_LOCAL_KUBE_CONTEXT", "false").lower() == "true"

# Polling configuration for all syncers (workloads, aims)
POLLING_INTERVAL_SECONDS = int(os.getenv("SYNCER_POLLING_INTERVAL_SECONDS", "5"))


async def load_k8s_config() -> None:
    """
    Load Kubernetes configuration from the cluster or local kubeconfig.

    Uses in-cluster config in production and kubeconfig for local development.
    This should be called once at application startup before creating KubernetesClient.
    """
    if USE_LOCAL_KUBE_CONTEXT:
        await k8s_config.load_kube_config()
        logger.info("Loaded kubeconfig for local development")
    else:
        k8s_config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
