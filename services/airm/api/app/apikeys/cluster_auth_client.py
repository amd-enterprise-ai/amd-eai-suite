# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import httpx
from fastapi import Request
from loguru import logger

from ..utilities.config import CLUSTER_AUTH_ADMIN_TOKEN, CLUSTER_AUTH_URL


class ClusterAuthClient:
    """
    Client for cluster-auth API service for API key management.

    This client communicates with the cluster-auth service which manages
    API keys, entities, and groups.
    """

    def __init__(self, base_url: str, admin_token: str):
        """
        Initialize the cluster-auth client.

        Args:
            base_url: Base URL of the cluster-auth service
            admin_token: Admin token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Admin-Token": self.admin_token},
            timeout=30.0,
        )

    async def create_api_key(
        self,
        ttl: str = "0",
        num_uses: int = 0,
        meta: dict | None = None,
        period: str = "",
        renewable: bool = True,
        explicit_max_ttl: str = "",
    ) -> dict:
        """
        Create a new API key with associated entity.

        Args:
            ttl: Time to live (e.g., "1h", "24h", "0" for never)
            num_uses: Number of uses allowed (0 = unlimited)
            meta: Metadata dictionary
            period: Renewal period
            renewable: Whether the key can be renewed
            explicit_max_ttl: Maximum TTL

        Returns:
            dict with api_key (prefixed with "amd_aim_api_key_"), key_id, and other metadata

        Note:
            The cluster-auth service automatically prefixes API keys with "amd_aim_api_key_"
            for better identification. The prefix is stripped during authentication.
        """
        payload = {
            "ttl": ttl,
            "num_uses": num_uses,
            "meta": meta or {},
            "period": period,
            "renewable": renewable,
            "explicit_max_ttl": explicit_max_ttl,
        }

        response = await self.client.post("/apikey/create", json=payload)
        response.raise_for_status()
        return response.json()

    async def revoke_api_key(self, key_id: str) -> None:
        """
        Revoke an API key.

        Args:
            key_id: The accessor/key_id of the API key to revoke

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        payload = {"key_id": key_id}
        response = await self.client.post("/apikey/revoke", json=payload)
        response.raise_for_status()

    async def renew_api_key(self, key_id: str, increment: str | None = None) -> dict:
        """
        Renew an API key's lease.

        Args:
            key_id: The accessor/key_id of the API key to renew
            increment: Optional TTL increment

        Returns:
            dict with lease_duration

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        payload = {"key_id": key_id}
        if increment:
            payload["increment"] = increment
        response = await self.client.post("/apikey/renew", json=payload)
        response.raise_for_status()
        return response.json()

    async def lookup_api_key(self, key_id: str) -> dict:
        """
        Get API key metadata.

        Args:
            key_id: The accessor/key_id of the API key

        Returns:
            dict with key metadata including groups

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        payload = {"key_id": key_id}
        response = await self.client.post("/apikey/lookup", json=payload)
        response.raise_for_status()
        return response.json()

    async def create_group(self, name: str, group_id: str | None = None) -> dict:
        """
        Create a new group in cluster-auth.

        Args:
            name: Name of the group
            group_id: Optional group ID (generated if not provided)

        Returns:
            dict with id and name

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        payload = {"name": name}
        if group_id:
            payload["id"] = group_id

        response = await self.client.post("/apikey/group", json=payload)
        response.raise_for_status()
        return response.json()

    async def delete_group(self, group_id: str) -> None:
        """
        Delete a group.

        Args:
            group_id: The ID of the group to delete

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        response = await self.client.delete("/apikey/group", params={"id": group_id})
        response.raise_for_status()

    async def bind_api_key_to_group(self, key_id: str, group_id: str) -> dict:
        """
        Bind an API key to a group by adding the key's entity to the group.

        Args:
            key_id: The accessor/key_id of the API key
            group_id: The ID of the group

        Returns:
            dict with updated groups list

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        payload = {"key_id": key_id, "group_id": group_id}
        response = await self.client.post("/apikey/bind", json=payload)
        response.raise_for_status()
        return response.json()

    async def unbind_api_key_from_group(self, key_id: str, group_id: str) -> dict:
        """
        Unbind an API key from a group by removing the key's entity from the group.

        Args:
            key_id: The accessor/key_id of the API key
            group_id: The ID of the group

        Returns:
            dict with updated groups list

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        payload = {"key_id": key_id, "group_id": group_id}
        response = await self.client.post("/apikey/unbind", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


def init_cluster_auth_client() -> ClusterAuthClient:
    """
    Initialize cluster-auth client.

    This will be called at application startup.

    Returns:
        ClusterAuthClient instance

    Raises:
        ValueError: If required configuration is missing
    """
    if not CLUSTER_AUTH_URL or not CLUSTER_AUTH_ADMIN_TOKEN:
        logger.error("Cluster-auth client not fully configured. Missing CLUSTER_AUTH_URL or CLUSTER_AUTH_ADMIN_TOKEN.")
        raise ValueError(
            "Cluster-auth client not fully configured. Missing CLUSTER_AUTH_URL or CLUSTER_AUTH_ADMIN_TOKEN."
        )

    client = ClusterAuthClient(base_url=CLUSTER_AUTH_URL, admin_token=CLUSTER_AUTH_ADMIN_TOKEN)
    logger.info(f"Connected to cluster-auth service at {CLUSTER_AUTH_URL}")
    return client


def get_cluster_auth_client(request: Request) -> ClusterAuthClient:
    """
    FastAPI dependency to get the initialized cluster-auth client from app.state.

    Args:
        request: FastAPI request object

    Returns:
        ClusterAuthClient instance

    Raises:
        RuntimeError: If the client is not initialized
    """
    if not hasattr(request.app.state, "cluster_auth_client") or request.app.state.cluster_auth_client is None:
        logger.error("Cluster-auth client not initialized in app.state. Check cluster-auth configuration.")
        raise RuntimeError(
            "Cluster-auth client not available. cluster-auth service may not be configured or initialization failed."
        )
    return request.app.state.cluster_auth_client
