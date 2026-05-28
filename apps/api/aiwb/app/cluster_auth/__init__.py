# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Cluster-auth client for API key management."""

from fastapi import Request
from loguru import logger

from .client import ClusterAuthClient
from .config import CLUSTER_AUTH_ENABLED


def get_cluster_auth_client(request: Request) -> ClusterAuthClient | None:
    """
    FastAPI dependency that returns the cluster-auth client from app state.

    Returns None when cluster-auth is disabled (CLUSTER_AUTH_ENABLED=false)
    or when the client failed to initialize at startup.
    """
    if not CLUSTER_AUTH_ENABLED:
        return None
    client = getattr(request.app.state, "cluster_auth_client", None)
    if client is None:
        logger.warning("cluster-auth client not available in app.state")
    return client


__all__ = ["ClusterAuthClient", "get_cluster_auth_client"]
