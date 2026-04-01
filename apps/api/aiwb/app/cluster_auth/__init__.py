# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Cluster-auth client for API key management."""

from .client import ClusterAuthClient
from .config import CLUSTER_AUTH_ADMIN_TOKEN, CLUSTER_AUTH_URL


def get_cluster_auth_client() -> ClusterAuthClient:
    """
    Dependency injection for cluster-auth client.

    Returns:
        ClusterAuthClient instance configured with environment variables
    """
    return ClusterAuthClient(CLUSTER_AUTH_URL, CLUSTER_AUTH_ADMIN_TOKEN)


__all__ = ["ClusterAuthClient", "get_cluster_auth_client"]
