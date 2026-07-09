# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import re
from datetime import UTC, datetime
from uuid import UUID

import httpx
from loguru import logger
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.collections import PaginatedResult, paginate_list
from api_common.exceptions import ExternalServiceError, NotFoundException

from ..aims.constants import CLUSTER_AUTH_GROUP_ANNOTATION
from ..aims.service import get_aim_service
from ..cluster_auth.client import ClusterAuthClient
from ..config import AI_GW_REQUEST_DURATION_METRIC, AI_GW_TOKEN_USAGE_METRIC
from ..dispatch.kube_client import KubernetesClient
from ..metrics.constants import PROMETHEUS_NAN_STRING
from ..metrics.utils import (
    a_custom_query,
    a_custom_query_range,
    get_aggregation_lookback_for_metrics,
    get_step_for_range_query,
)
from .repository import create_api_key, delete_api_key, get_api_key_by_id, get_api_keys_for_namespace
from .schemas import (
    ApiKeyCreate,
    ApiKeyDetails,
    ApiKeyMetricsDataPoint,
    ApiKeyMetricsResponse,
    ApiKeyMetricsStats,
    ApiKeyRequestsTimeseries,
    ApiKeyResponse,
    ApiKeyTokensTimeseries,
    ApiKeyUpdate,
    ApiKeyWithFullKey,
    GroupResponse,
)


async def _bind_api_key_to_aim_groups(
    kube_client: KubernetesClient,
    namespace: str,
    cluster_auth_key_id: str,
    aim_ids: list[str],
    cluster_auth_client: ClusterAuthClient,
) -> None:
    """
    Bind an API key to cluster-auth groups associated with deployed AIMs.

    Fetches AIMService resources from Kubernetes and extracts their cluster-auth
    group IDs from the "cluster-auth/allowed-group" annotation, then binds the
    API key to those groups.

    Args:
        kube_client: Kubernetes client instance
        namespace: Kubernetes namespace where AIMs are deployed
        cluster_auth_key_id: The cluster-auth key ID to bind
        aim_ids: List of AIM service IDs (UUIDs as strings)
        cluster_auth_client: Cluster-auth client instance
    """
    logger.info(f"Binding API key {cluster_auth_key_id} to {len(aim_ids)} AIM(s)")

    # Resolve AIM IDs to cluster-auth group IDs
    group_ids = await _get_group_ids_for_aim_ids(kube_client, namespace, aim_ids)

    if not group_ids:
        logger.warning(f"No group IDs found for {len(aim_ids)} AIM(s) - no bindings will be created")
        return

    logger.info(f"Resolved {len(aim_ids)} AIM(s) to {len(group_ids)} group ID(s)")

    # Create tasks for all bind operations
    bind_tasks = [cluster_auth_client.bind_api_key_to_group(cluster_auth_key_id, group_id) for group_id in group_ids]

    # Run all bind operations concurrently
    if bind_tasks:
        bind_results = await asyncio.gather(*bind_tasks, return_exceptions=True)
        for group_id, result in zip(group_ids, bind_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to bind API key {cluster_auth_key_id} to group {group_id}: {result}")
            else:
                logger.info(f"Bound API key {cluster_auth_key_id} to group {group_id}")


async def _get_group_ids_for_aim_ids(
    kube_client: KubernetesClient,
    namespace: str,
    aim_ids: list[str],
) -> list[str]:
    """
    Get cluster-auth group IDs for deployed AIMs.

    Fetches AIMService resources from Kubernetes by their IDs and extracts
    the cluster-auth group ID from the "cluster-auth/allowed-group" annotation.

    Args:
        kube_client: Kubernetes client instance
        namespace: Kubernetes namespace where AIMs are deployed
        aim_ids: List of AIM service IDs (UUIDs as strings)

    Returns:
        List of cluster-auth group IDs extracted from AIMService annotations (deduplicated)
    """
    # Handle empty list case - no AIMs means no groups
    if not aim_ids:
        return []

    group_ids_set: set[str] = set()

    # Fetch each AIMService and extract its group ID from spec.routing.annotations
    for aim_id_str in aim_ids:
        try:
            aim_uuid = UUID(aim_id_str)
            aim_service = await get_aim_service(kube_client, namespace, aim_uuid)

            # Extract group ID from spec.routing.annotations
            routing_annotations = aim_service.spec.routing.get("annotations", {})
            group_id = routing_annotations.get(CLUSTER_AUTH_GROUP_ANNOTATION)
            if group_id:
                group_ids_set.add(group_id)
                logger.debug(f"Found group ID {group_id} for AIMService {aim_id_str}")
            else:
                logger.warning(
                    f"AIMService {aim_id_str} does not have '{CLUSTER_AUTH_GROUP_ANNOTATION}' in spec.routing.annotations"
                )

        except ValueError as e:
            logger.error(f"Invalid UUID format for AIM ID {aim_id_str}: {e}")
        except NotFoundException:
            logger.warning(f"AIMService {aim_id_str} not found in namespace {namespace}")
        except Exception as e:
            logger.error(f"Failed to fetch AIMService {aim_id_str}: {e}")

    return list(group_ids_set)


async def _sync_api_key_group_bindings(
    cluster_auth_key_id: str,
    current_groups: set[str],
    target_groups: set[str],
    cluster_auth_client: ClusterAuthClient,
) -> None:
    """
    Synchronize API key group bindings by adding/removing groups as needed.

    Args:
        cluster_auth_key_id: The cluster-auth key ID
        current_groups: Current set of group IDs
        target_groups: Desired set of group IDs
        cluster_auth_client: Cluster-auth client instance
    """
    groups_to_remove = current_groups - target_groups
    groups_to_add = target_groups - current_groups

    # Create tasks for all unbind operations
    unbind_tasks = [
        cluster_auth_client.unbind_api_key_from_group(cluster_auth_key_id, group_id) for group_id in groups_to_remove
    ]

    # Create tasks for all bind operations
    bind_tasks = [
        cluster_auth_client.bind_api_key_to_group(cluster_auth_key_id, group_id) for group_id in groups_to_add
    ]

    # Run unbind and bind operations in parallel
    unbind_task = asyncio.gather(*unbind_tasks, return_exceptions=True) if unbind_tasks else None
    bind_task = asyncio.gather(*bind_tasks, return_exceptions=True) if bind_tasks else None

    unbind_results: list[dict | BaseException] = []
    bind_results: list[dict | BaseException] = []

    if unbind_task and bind_task:
        results = await asyncio.gather(unbind_task, bind_task)
        unbind_results = results[0]
        bind_results = results[1]
    elif unbind_task:
        unbind_results = await unbind_task
    elif bind_task:
        bind_results = await bind_task

    # Check for unbind errors
    failed_unbinds = []
    for group_id, result in zip(groups_to_remove, unbind_results):
        if isinstance(result, Exception):
            logger.error(f"Failed to unbind API key from group {group_id}: {result}")
            failed_unbinds.append((group_id, result))
        else:
            logger.info(f"Unbound API key {cluster_auth_key_id} from group {group_id}")

    # Check for bind errors
    failed_binds = []
    for group_id, result in zip(groups_to_add, bind_results):
        if isinstance(result, Exception):
            logger.error(f"Failed to bind API key to group {group_id}: {result}")
            failed_binds.append((group_id, result))
        else:
            logger.info(f"Bound API key {cluster_auth_key_id} to group {group_id}")

    # Raise exception if any operations failed
    if failed_unbinds or failed_binds:
        error_details = []
        if failed_unbinds:
            error_details.append(f"Failed to unbind from {len(failed_unbinds)} group(s)")
        if failed_binds:
            error_details.append(f"Failed to bind to {len(failed_binds)} group(s)")
        raise ExternalServiceError(f"API key group synchronization failed: {', '.join(error_details)}")


def truncate_api_key(full_key: str) -> str:
    """
    Truncate an API key for safe display, preserving the prefix.

    Args:
        full_key: The full API key with prefix (e.g., "amd_aim_api_key_hvs.abc123def456")

    Returns:
        Truncated key for display (e.g., "amd_aim_api_key_••••••••6456")
    """
    prefix = "amd_aim_api_key_"

    # All API keys from cluster-auth have the prefix
    if not full_key.startswith(prefix):
        raise ValueError(f"API key must start with '{prefix}'")

    # Show prefix + masked middle + last 4 chars of the token part
    token_part = full_key[len(prefix) :]
    if len(token_part) <= 4:
        return full_key
    last_four = token_part[-4:]
    return f"{prefix}••••••••{last_four}"


async def create_api_key_with_cluster_auth(
    session: AsyncSession,
    kube_client: KubernetesClient,
    namespace: str,
    api_key_in: ApiKeyCreate,
    user: str,
    cluster_auth_client: ClusterAuthClient,
) -> ApiKeyWithFullKey:
    """
    Create an API key with cluster-auth integration.

    Args:
        session: Database session
        kube_client: Kubernetes client instance
        namespace: The namespace
        api_key_in: API key creation data
        user: Email of the user creating the key
        cluster_auth_client: Cluster-auth client instance

    Returns:
        The created API key with the full key (shown only once)
    """

    logger.info(f"Creating API key '{api_key_in.display_name}' for namespace {namespace}")

    cluster_auth_response = await cluster_auth_client.create_api_key(
        ttl=api_key_in.ttl,
        num_uses=api_key_in.num_uses,
        meta=api_key_in.meta,
        renewable=api_key_in.renewable,
        explicit_max_ttl=api_key_in.explicit_max_ttl,
        period=api_key_in.period,
        display_name=f"{namespace}-{api_key_in.display_name}",
    )

    full_key = cluster_auth_response["api_key"]
    truncated_key = truncate_api_key(full_key)
    cluster_auth_key_id = cluster_auth_response["key_id"]

    try:
        api_key_db = await create_api_key(
            session=session,
            display_name=api_key_in.display_name,
            truncated_key=truncated_key,
            cluster_auth_key_id=cluster_auth_key_id,
            namespace=namespace,
            creator=user,
        )

        # Fetch ttl, expires_at, renewable, and num_uses from cluster-auth (source of truth)
        cluster_auth_data = await cluster_auth_client.lookup_api_key(cluster_auth_key_id)

        # Bind API key to AIM groups if specified
        if api_key_in.aim_ids:
            await _bind_api_key_to_aim_groups(
                kube_client=kube_client,
                namespace=namespace,
                cluster_auth_key_id=cluster_auth_key_id,
                aim_ids=api_key_in.aim_ids,
                cluster_auth_client=cluster_auth_client,
            )
            # Refresh cluster auth data to get updated groups
            cluster_auth_data = await cluster_auth_client.lookup_api_key(cluster_auth_key_id)

    except Exception:
        # DB insert, cluster-auth lookup, or binding failed - revoke the key to prevent orphaning
        logger.error(
            f"Failed to create API key '{api_key_in.display_name}', revoking cluster-auth key {cluster_auth_key_id}"
        )
        try:
            await cluster_auth_client.revoke_api_key(cluster_auth_key_id)
            logger.info(f"Successfully revoked orphaned cluster-auth key {cluster_auth_key_id}")
        except Exception as revoke_error:
            logger.error(f"Failed to revoke orphaned cluster-auth key {cluster_auth_key_id}: {revoke_error}")
        raise

    return ApiKeyWithFullKey(
        id=api_key_db.id,
        display_name=api_key_db.display_name,
        truncated_key=api_key_db.truncated_key,
        namespace=api_key_db.namespace,
        expires_at=cluster_auth_data.get("expire_time"),
        renewable=cluster_auth_data.get("renewable", True),
        num_uses=cluster_auth_data.get("num_uses", 0),
        ttl=cluster_auth_data.get("ttl"),
        created_at=api_key_db.created_at,
        updated_at=api_key_db.updated_at,
        created_by=api_key_db.created_by,
        updated_by=api_key_db.updated_by,
        full_key=full_key,
    )


async def update_api_key_bindings_with_cluster_auth(
    session: AsyncSession,
    kube_client: KubernetesClient,
    namespace: str,
    api_key_id: UUID,
    api_key_update: ApiKeyUpdate,
    cluster_auth_client: ClusterAuthClient,
) -> ApiKeyDetails:
    """
    Update API key bindings to AIM groups.

    Args:
        session: Database session
        kube_client: Kubernetes client instance
        namespace: The namespace
        api_key_id: The ID of the API key to update
        api_key_update: API key update data containing aim_ids
        cluster_auth_client: Cluster-auth client instance

    Returns:
        Updated API key details

    Raises:
        NotFoundException: If the API key is not found
    """
    # Verify the API key exists
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    logger.info(f"Updating API key {api_key_id} bindings for {len(api_key_update.aim_ids)} AIM(s)")

    # Get current group bindings from cluster-auth
    try:
        cluster_auth_data = await cluster_auth_client.lookup_api_key(api_key.cluster_auth_key_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"API key {api_key.cluster_auth_key_id} not found in cluster-auth")
            await delete_api_key(session, api_key)
            raise NotFoundException(
                f"API key with ID {api_key_id} not found - orphaned database record has been cleaned up"
            )
        raise

    current_groups = set(cluster_auth_data.get("groups", []))

    # Get target groups from aim_ids
    target_group_ids = await _get_group_ids_for_aim_ids(
        kube_client=kube_client,
        namespace=namespace,
        aim_ids=api_key_update.aim_ids,
    )

    # Synchronize the group bindings
    await _sync_api_key_group_bindings(
        cluster_auth_key_id=api_key.cluster_auth_key_id,
        current_groups=current_groups,
        target_groups=set(target_group_ids),
        cluster_auth_client=cluster_auth_client,
    )

    # Return updated details
    return await get_api_key_details_from_cluster_auth(
        session=session,
        namespace=namespace,
        api_key_id=api_key_id,
        cluster_auth_client=cluster_auth_client,
    )


async def list_api_keys_for_namespace(
    session: AsyncSession,
    namespace: str,
    page: int = 1,
    page_size: int = 10,
) -> PaginatedResult[ApiKeyResponse]:
    """
    List all API keys for a namespace as a paginated result.

    Args:
        session: Database session
        namespace: The namespace
        page: 1-indexed page number
        page_size: Maximum number of items per page

    Returns:
        Paginated API keys (without ttl/expires_at - use get_details for those)
    """
    api_keys = await get_api_keys_for_namespace(session, namespace)

    responses = [
        ApiKeyResponse(
            id=key.id,
            display_name=key.display_name,
            truncated_key=key.truncated_key,
            namespace=key.namespace,
            created_at=key.created_at,
            updated_at=key.updated_at,
            created_by=key.created_by,
            updated_by=key.updated_by,
        )
        for key in api_keys
    ]
    # Paginate after building the full list so `total` reflects the full set.
    return paginate_list(responses, page=page, page_size=page_size)


async def get_api_key_details_from_cluster_auth(
    session: AsyncSession,
    namespace: str,
    api_key_id: UUID,
    cluster_auth_client: ClusterAuthClient,
) -> ApiKeyDetails:
    """
    Get detailed API key information including cluster-auth metadata.

    Args:
        session: Database session
        namespace: The namespace
        api_key_id: The ID of the API key
        cluster_auth_client: Cluster-auth client instance

    Returns:
        Detailed API key information

    Raises:
        NotFoundException: If the API key is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    try:
        cluster_auth_data = await cluster_auth_client.lookup_api_key(api_key.cluster_auth_key_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(
                f"API key {api_key.cluster_auth_key_id} not found in cluster-auth, deleting orphaned record from database"
            )
            await delete_api_key(session, api_key)
            raise NotFoundException(
                f"API key with ID {api_key_id} not found - orphaned database record has been cleaned up"
            )
        raise

    return ApiKeyDetails(
        id=api_key.id,
        display_name=api_key.display_name,
        truncated_key=api_key.truncated_key,
        namespace=api_key.namespace,
        renewable=cluster_auth_data.get("renewable", True),
        num_uses=cluster_auth_data.get("num_uses", 0),
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        created_by=api_key.created_by,
        updated_by=api_key.updated_by,
        ttl=cluster_auth_data.get("ttl"),
        expires_at=cluster_auth_data.get("expire_time"),
        groups=cluster_auth_data.get("groups", []),
        entity_id=cluster_auth_data.get("entity_id"),
        meta=cluster_auth_data.get("meta", {}),
    )


async def delete_api_key_from_cluster_auth(
    session: AsyncSession,
    namespace: str,
    api_key_id: UUID,
    cluster_auth_client: ClusterAuthClient,
) -> None:
    """
    Delete an API key and revoke it in cluster-auth.

    Args:
        session: Database session
        namespace: The namespace
        api_key_id: The ID of the API key
        cluster_auth_client: Cluster-auth client instance

    Raises:
        NotFoundException: If the API key is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    try:
        await cluster_auth_client.revoke_api_key(api_key.cluster_auth_key_id)
        logger.info(f"Revoked API key {api_key.cluster_auth_key_id} in cluster-auth")
    except httpx.HTTPStatusError as e:
        # 404 is tolerated so a missing cluster-auth key cannot block DB cleanup;
        # other status codes are real failures that must surface to the caller.
        if e.response.status_code != 404:
            raise
        logger.warning(
            f"API key {api_key.cluster_auth_key_id} not found in cluster-auth, proceeding with database deletion"
        )

    await delete_api_key(session, api_key)


async def renew_api_key_in_cluster_auth(
    session: AsyncSession,
    namespace: str,
    api_key_id: UUID,
    cluster_auth_client: ClusterAuthClient,
) -> dict:
    """
    Renew an API key in cluster-auth.

    Args:
        session: Database session
        namespace: The namespace
        api_key_id: The ID of the API key
        cluster_auth_client: Cluster-auth client instance

    Returns:
        dict with lease_duration

    Raises:
        NotFoundException: If the API key is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    try:
        result = await cluster_auth_client.renew_api_key(api_key.cluster_auth_key_id)
        logger.info(f"Renewed API key {api_key.cluster_auth_key_id} in cluster-auth")
        return result
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"Failed to renew API key {api_key.cluster_auth_key_id}: {e}")
            raise NotFoundException(f"Failed to renew API key: {e}")
        raise


async def list_api_key_group_memberships(
    session: AsyncSession,
    namespace: str,
    api_key_id: UUID,
    cluster_auth_client: ClusterAuthClient,
) -> list[str]:
    """
    List the cluster-auth groups this API key currently belongs to.

    Args:
        session: Database session
        namespace: The namespace
        api_key_id: The ID of the API key
        cluster_auth_client: Cluster-auth client instance

    Returns:
        List of group IDs the API key is a member of

    Raises:
        NotFoundException: If the API key is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    try:
        cluster_auth_data = await cluster_auth_client.lookup_api_key(api_key.cluster_auth_key_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(
                f"API key {api_key.cluster_auth_key_id} not found in cluster-auth, deleting orphaned record from database"
            )
            await delete_api_key(session, api_key)
            raise NotFoundException(
                f"API key with ID {api_key_id} not found - orphaned database record has been cleaned up"
            )
        raise

    return cluster_auth_data.get("groups", [])


async def add_api_key_group_membership(
    session: AsyncSession,
    namespace: str,
    api_key_id: UUID,
    group_id: str,
    cluster_auth_client: ClusterAuthClient,
) -> list[str]:
    """
    Add an API key to a cluster-auth group.

    Args:
        session: Database session
        namespace: The namespace
        api_key_id: The ID of the API key
        group_id: The ID of the group
        cluster_auth_client: Cluster-auth client instance

    Returns:
        Updated list of group IDs the API key is a member of

    Raises:
        NotFoundException: If the API key or group is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    try:
        result = await cluster_auth_client.bind_api_key_to_group(api_key.cluster_auth_key_id, group_id)
        logger.info(f"Added API key {api_key.cluster_auth_key_id} to group {group_id}")
        return result["groups"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"Failed to add API key to group: {e}")
            raise NotFoundException(f"Failed to add API key to group: {e}")
        raise


async def remove_api_key_group_membership(
    session: AsyncSession,
    namespace: str,
    api_key_id: UUID,
    group_id: str,
    cluster_auth_client: ClusterAuthClient,
) -> list[str]:
    """
    Remove an API key from a cluster-auth group.

    Args:
        session: Database session
        namespace: The namespace
        api_key_id: The ID of the API key
        group_id: The ID of the group
        cluster_auth_client: Cluster-auth client instance

    Returns:
        Updated list of group IDs the API key is a member of

    Raises:
        NotFoundException: If the API key or group is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    try:
        result = await cluster_auth_client.unbind_api_key_from_group(api_key.cluster_auth_key_id, group_id)
        logger.info(f"Removed API key {api_key.cluster_auth_key_id} from group {group_id}")
        return result["groups"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"API key or group not found: {e}")
            raise NotFoundException("API key or group not found")
        raise


async def create_group_in_cluster_auth(
    cluster_auth_client: ClusterAuthClient,
    name: str | None = None,
    group_id: str | None = None,
) -> GroupResponse:
    """
    Create a group in cluster-auth.

    Args:
        cluster_auth_client: Cluster-auth client instance
        name: Optional name for the group
        group_id: Optional ID for the group

    Returns:
        GroupResponse with id and name

    Note:
        Groups are managed at the cluster-auth level and are not scoped to namespaces.
    """

    try:
        result = await cluster_auth_client.create_group(name=name or "", group_id=group_id)
        logger.info(f"Created group {result['id']} with name {result['name']}")
        return GroupResponse(id=result["id"], name=result["name"])
    except Exception as e:
        logger.error(f"Failed to create group: {e}")
        raise


async def delete_group_from_cluster_auth(
    group_id: str,
    cluster_auth_client: ClusterAuthClient,
) -> None:
    """
    Delete a group from cluster-auth.

    Args:
        group_id: The ID of the group to delete
        cluster_auth_client: Cluster-auth client instance

    Raises:
        NotFoundException: If the group is not found

    Note:
        Groups are managed at the cluster-auth level and are not scoped to namespaces.
    """

    try:
        await cluster_auth_client.delete_group(group_id)
        logger.info(f"Deleted group {group_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Group {group_id} not found in cluster-auth")
            raise NotFoundException(f"Group with ID {group_id} not found")
        raise


def _pivot_to_wide(results: list[dict], services: list[str]) -> dict[str, dict[str, float]]:
    wide: dict[str, dict[str, float]] = {}
    for series in results:
        service = series["metric"].get("aim_service_id", "")
        if not service:
            continue
        for ts, val in series["values"]:
            iso = datetime.fromtimestamp(float(ts), tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            wide.setdefault(iso, {s: 0.0 for s in services})
            try:
                wide[iso][service] = wide[iso].get(service, 0.0) + float(val if val != PROMETHEUS_NAN_STRING else 0)
            except (ValueError, TypeError):
                pass
    return wide


def _wide_to_datapoints(wide: dict[str, dict[str, float]], services: list[str]) -> list[ApiKeyMetricsDataPoint]:
    return [{"date": iso, **{s: wide[iso].get(s, 0.0) for s in services}} for iso in sorted(wide)]


async def get_api_key_usage_metrics(
    session: AsyncSession,
    namespace: str,
    api_key_id: UUID,
    start: datetime,
    end: datetime,
    prometheus_client: PrometheusConnect,
) -> ApiKeyMetricsResponse:
    api_key = await get_api_key_by_id(session, api_key_id, namespace)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in namespace '{namespace}'")

    # OpenBao prefixes the token display_name with "token-" and sanitizes it
    # (replaces non-alphanumeric/hyphen chars with hyphens, lowercases).
    # This is what ends up as the api_key_id label in Prometheus metrics.
    prom_key_id = "token-" + re.sub(r"[^a-z0-9\-]", "-", f"{namespace}-{api_key.display_name}".lower())

    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)
    step_str = f"{int(step)}s"
    duration_s = f"{int((end - start).total_seconds())}s"

    # pod!="" deduplicates series scraped twice (PodMonitor vs ServiceMonitor)
    # from the same endpoint — both carry identical counter values.
    # error_type label is absent on successful requests and "_OTHER" on failures
    # (follows OTel GenAI semantic conventions).
    (
        token_results,
        request_results,
        failed_request_results,
        total_token_stat,
        total_request_stat,
        total_failed_stat,
    ) = await asyncio.gather(
        a_custom_query_range(
            prometheus_client,
            query=f'sum by (aim_service_id, gen_ai_token_type) (increase({AI_GW_TOKEN_USAGE_METRIC}{{api_key_id="{prom_key_id}",pod!=""}}[{lookback}]))',
            start_time=start,
            end_time=end,
            step=step_str,
        ),
        a_custom_query_range(
            prometheus_client,
            query=f'sum by (aim_service_id) (increase({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!="",error_type=""}}[{lookback}]))',
            start_time=start,
            end_time=end,
            step=step_str,
        ),
        a_custom_query_range(
            prometheus_client,
            query=f'sum by (aim_service_id) (increase({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!="",error_type!=""}}[{lookback}]))',
            start_time=start,
            end_time=end,
            step=step_str,
        ),
        a_custom_query(
            prometheus_client,
            # Offset subtraction instead of increase() so new counters (no prior scrape at 0)
            # still produce a non-zero total. OR fallback fires when offset window has no data.
            query=(
                f'sum({AI_GW_TOKEN_USAGE_METRIC}{{api_key_id="{prom_key_id}",pod!=""}})'
                f' - sum({AI_GW_TOKEN_USAGE_METRIC}{{api_key_id="{prom_key_id}",pod!=""}} offset {duration_s})'
                f' OR sum({AI_GW_TOKEN_USAGE_METRIC}{{api_key_id="{prom_key_id}",pod!=""}})'
            ),
        ),
        a_custom_query(
            prometheus_client,
            query=(
                f'sum({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!=""}})'
                f' - sum({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!=""}} offset {duration_s})'
                f' OR sum({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!=""}})'
            ),
        ),
        a_custom_query(
            prometheus_client,
            query=(
                f'sum({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!="",error_type!=""}})'
                f' - sum({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!="",error_type!=""}} offset {duration_s})'
                f' OR sum({AI_GW_REQUEST_DURATION_METRIC}{{api_key_id="{prom_key_id}",pod!="",error_type!=""}})'
            ),
        ),
    )

    services = sorted(
        {
            s["metric"].get("aim_service_id", "")
            for s in token_results + request_results + failed_request_results
            if s["metric"].get("aim_service_id")
        }
    )

    input_results = [s for s in token_results if s["metric"].get("gen_ai_token_type") == "input"]
    output_results = [s for s in token_results if s["metric"].get("gen_ai_token_type") == "output"]

    input_wide = _pivot_to_wide(input_results, services)
    output_wide = _pivot_to_wide(output_results, services)
    successful_request_wide = _pivot_to_wide(request_results, services)
    failed_request_wide = _pivot_to_wide(failed_request_results, services)

    total_token_wide = {
        iso: {s: input_wide.get(iso, {}).get(s, 0.0) + output_wide.get(iso, {}).get(s, 0.0) for s in services}
        for iso in sorted(set(input_wide) | set(output_wide))
    }

    all_timestamps = sorted(set(successful_request_wide) | set(failed_request_wide))
    total_request_wide = {
        iso: {
            s: successful_request_wide.get(iso, {}).get(s, 0.0) + failed_request_wide.get(iso, {}).get(s, 0.0)
            for s in services
        }
        for iso in all_timestamps
    }

    def _extract_stat(result: list[dict]) -> int:
        if result and result[0].get("value"):
            try:
                return max(0, int(float(result[0]["value"][1])))
            except (ValueError, TypeError, IndexError):
                pass
        return 0

    total_tokens = _extract_stat(total_token_stat)
    total_requests = _extract_stat(total_request_stat)
    failed_requests = _extract_stat(total_failed_stat)

    return ApiKeyMetricsResponse(
        stats=ApiKeyMetricsStats(
            total_requests=total_requests,
            successful_requests=max(0, total_requests - failed_requests),
            failed_requests=failed_requests,
            total_tokens=total_tokens,
            linked_deployments=len(services),
        ),
        services=services,
        requests_over_time=ApiKeyRequestsTimeseries(
            total=_wide_to_datapoints(total_request_wide, services),
            successful=_wide_to_datapoints(successful_request_wide, services),
            failed=_wide_to_datapoints(failed_request_wide, services),
        ),
        tokens_over_time=ApiKeyTokensTimeseries(
            total=_wide_to_datapoints(total_token_wide, services),
            input=_wide_to_datapoints(input_wide, services),
            output=_wide_to_datapoints(output_wide, services),
        ),
    )
