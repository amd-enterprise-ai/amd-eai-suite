# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..managed_workloads.enums import WorkloadStatus
from ..managed_workloads.repository import select_workloads
from ..organizations.models import Organization
from ..projects.models import Project
from ..utilities.exceptions import ExternalServiceError, NotFoundException
from ..workloads.enums import WorkloadType
from .cluster_auth_client import ClusterAuthClient
from .repository import create_api_key, delete_api_key, get_api_key_by_id, get_api_keys_for_project
from .schemas import ApiKeyCreate, ApiKeyDetails, ApiKeyResponse, ApiKeyUpdate, ApiKeyWithFullKey, GroupResponse


async def _bind_api_key_to_aim_groups(
    session: AsyncSession,
    project: Project,
    cluster_auth_key_id: str,
    aim_ids: list[UUID],
    cluster_auth_client: ClusterAuthClient,
) -> None:
    """
    Bind an API key to cluster-auth groups associated with deployed AIMs.

    Args:
        session: Database session
        project: The project containing the AIMs
        cluster_auth_key_id: The cluster-auth key ID to bind
        aim_ids: List of AIM IDs to bind to
        cluster_auth_client: Cluster-auth client instance
    """
    logger.info(f"Binding API key {cluster_auth_key_id} to {len(aim_ids)} AIM(s)")

    # Get deployed AIM workloads with cluster-auth groups
    workloads = await select_workloads(
        session=session,
        project_id=project.id,
        type=[WorkloadType.INFERENCE],
        status=[WorkloadStatus.RUNNING, WorkloadStatus.PENDING],
        aim_ids=aim_ids,
    )

    # Filter for workloads that have cluster-auth group IDs
    deployed_aims = [w for w in workloads if w.cluster_auth_group_id]

    # Create tasks for all bind operations
    bind_tasks = [
        cluster_auth_client.bind_api_key_to_group(cluster_auth_key_id, workload.cluster_auth_group_id)
        for workload in deployed_aims
    ]

    # Run all bind operations concurrently
    if bind_tasks:
        bind_results = await asyncio.gather(*bind_tasks, return_exceptions=True)
        for workload, result in zip(deployed_aims, bind_results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to bind API key {cluster_auth_key_id} to group {workload.cluster_auth_group_id}: {result}"
                )
            else:
                logger.info(
                    f"Bound API key {cluster_auth_key_id} to group {workload.cluster_auth_group_id} for AIM {workload.aim_id}"
                )


async def _get_group_ids_for_aim_ids(
    session: AsyncSession,
    project: Project,
    aim_ids: list[UUID],
) -> set[str]:
    """
    Get cluster-auth group IDs for deployed AIMs.

    Args:
        session: Database session
        project: The project containing the AIMs
        aim_ids: List of AIM IDs to get groups for

    Returns:
        Set of cluster-auth group IDs
    """
    # Handle empty list case - no AIMs means no groups
    if not aim_ids:
        return set()

    workloads = await select_workloads(
        session=session,
        project_id=project.id,
        type=[WorkloadType.INFERENCE],
        status=[WorkloadStatus.RUNNING, WorkloadStatus.PENDING],
        aim_ids=aim_ids,
    )

    # Filter for workloads that have cluster-auth group IDs
    deployed_aims = [w for w in workloads if w.cluster_auth_group_id]
    return {w.cluster_auth_group_id for w in deployed_aims}


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
    organization: Organization,
    project: Project,
    api_key_in: ApiKeyCreate,
    user: str,
    cluster_auth_client: ClusterAuthClient,
) -> ApiKeyWithFullKey:
    """
    Create an API key with cluster-auth integration.

    Args:
        session: Database session
        organization: The organization
        project: The project
        api_key_in: API key creation data
        user: Email of the user creating the key
        cluster_auth_client: Cluster-auth client instance

    Returns:
        The created API key with the full key (shown only once)
    """

    logger.info(f"Creating API key '{api_key_in.name}' for project {project.id}")

    cluster_auth_response = await cluster_auth_client.create_api_key(
        ttl=api_key_in.ttl,
        num_uses=api_key_in.num_uses,
        meta=api_key_in.meta,
        renewable=api_key_in.renewable,
        explicit_max_ttl=api_key_in.explicit_max_ttl,
        period=api_key_in.period,
    )

    full_key = cluster_auth_response["api_key"]
    truncated_key = truncate_api_key(full_key)
    cluster_auth_key_id = cluster_auth_response["key_id"]

    try:
        api_key_db = await create_api_key(
            session=session,
            name=api_key_in.name,
            truncated_key=truncated_key,
            cluster_auth_key_id=cluster_auth_key_id,
            project_id=project.id,
            creator=user,
        )

        # Fetch ttl, expires_at, renewable, and num_uses from cluster-auth (source of truth)
        cluster_auth_data = await cluster_auth_client.lookup_api_key(cluster_auth_key_id)

        # Bind API key to AIM groups if specified
        if api_key_in.aim_ids:
            await _bind_api_key_to_aim_groups(
                session=session,
                project=project,
                cluster_auth_key_id=cluster_auth_key_id,
                aim_ids=api_key_in.aim_ids,
                cluster_auth_client=cluster_auth_client,
            )
            # Refresh cluster auth data to get updated groups
            cluster_auth_data = await cluster_auth_client.lookup_api_key(cluster_auth_key_id)

    except Exception:
        # DB insert, cluster-auth lookup, or binding failed - revoke the key to prevent orphaning
        logger.error(f"Failed to create API key '{api_key_in.name}', revoking cluster-auth key {cluster_auth_key_id}")
        try:
            await cluster_auth_client.revoke_api_key(cluster_auth_key_id)
            logger.info(f"Successfully revoked orphaned cluster-auth key {cluster_auth_key_id}")
        except Exception as revoke_error:
            logger.error(f"Failed to revoke orphaned cluster-auth key {cluster_auth_key_id}: {revoke_error}")
        raise

    return ApiKeyWithFullKey(
        id=api_key_db.id,
        name=api_key_db.name,
        truncated_key=api_key_db.truncated_key,
        project_id=api_key_db.project_id,
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
    organization: Organization,
    project: Project,
    api_key_id: UUID,
    api_key_update: ApiKeyUpdate,
    cluster_auth_client: ClusterAuthClient,
) -> ApiKeyDetails:
    """
    Update API key bindings to AIM groups.

    Args:
        session: Database session
        organization: The organization
        project: The project
        api_key_id: The ID of the API key to update
        api_key_update: API key update data containing aim_ids
        cluster_auth_client: Cluster-auth client instance

    Returns:
        Updated API key details

    Raises:
        NotFoundException: If the API key is not found
    """
    # Verify the API key exists
    api_key = await get_api_key_by_id(session, api_key_id, project.id)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in your project")

    logger.info(f"Updating API key {api_key_id} bindings for {len(api_key_update.aim_ids)} AIM(s)")

    # Get current group bindings from cluster-auth
    try:
        cluster_auth_data = await cluster_auth_client.lookup_api_key(api_key.cluster_auth_key_id)
    except KeyError:
        logger.warning(f"API key {api_key.cluster_auth_key_id} not found in cluster-auth")
        await delete_api_key(session, api_key)
        raise NotFoundException(
            f"API key with ID {api_key_id} not found - orphaned database record has been cleaned up"
        )

    current_groups = set(cluster_auth_data.get("groups", []))

    # Get target groups from aim_ids
    target_groups = await _get_group_ids_for_aim_ids(
        session=session,
        project=project,
        aim_ids=api_key_update.aim_ids,
    )

    # Synchronize the group bindings
    await _sync_api_key_group_bindings(
        cluster_auth_key_id=api_key.cluster_auth_key_id,
        current_groups=current_groups,
        target_groups=target_groups,
        cluster_auth_client=cluster_auth_client,
    )

    # Return updated details
    return await get_api_key_details_from_cluster_auth(
        session=session,
        organization=organization,
        project=project,
        api_key_id=api_key_id,
        cluster_auth_client=cluster_auth_client,
    )


async def list_api_keys_for_project(
    session: AsyncSession,
    organization: Organization,
    project: Project,
) -> list[ApiKeyResponse]:
    """
    List all API keys for a project.

    Args:
        session: Database session
        organization: The organization (unused, kept for API compatibility)
        project: The project

    Returns:
        List of API keys (without ttl/expires_at - use get_details for those)
    """
    api_keys = await get_api_keys_for_project(session, project.id)

    return [
        ApiKeyResponse(
            id=key.id,
            name=key.name,
            truncated_key=key.truncated_key,
            project_id=key.project_id,
            created_at=key.created_at,
            updated_at=key.updated_at,
            created_by=key.created_by,
            updated_by=key.updated_by,
        )
        for key in api_keys
    ]


async def get_api_key_details_from_cluster_auth(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    api_key_id: UUID,
    cluster_auth_client: ClusterAuthClient,
) -> ApiKeyDetails:
    """
    Get detailed API key information including cluster-auth metadata.

    Args:
        session: Database session
        organization: The organization (unused, kept for API compatibility)
        project: The project
        api_key_id: The ID of the API key
        cluster_auth_client: Cluster-auth client instance

    Returns:
        Detailed API key information

    Raises:
        NotFoundException: If the API key is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, project.id)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in your project")

    try:
        cluster_auth_data = await cluster_auth_client.lookup_api_key(api_key.cluster_auth_key_id)
    except KeyError:
        logger.warning(
            f"API key {api_key.cluster_auth_key_id} not found in cluster-auth, deleting orphaned record from database"
        )
        await delete_api_key(session, api_key)
        raise NotFoundException(
            f"API key with ID {api_key_id} not found - orphaned database record has been cleaned up"
        )

    return ApiKeyDetails(
        id=api_key.id,
        name=api_key.name,
        truncated_key=api_key.truncated_key,
        project_id=api_key.project_id,
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
    organization: Organization,
    project: Project,
    api_key_id: UUID,
    cluster_auth_client: ClusterAuthClient,
) -> None:
    """
    Delete an API key and revoke it in cluster-auth.

    Args:
        session: Database session
        organization: The organization (unused, kept for API compatibility)
        project: The project
        api_key_id: The ID of the API key
        cluster_auth_client: Cluster-auth client instance

    Raises:
        NotFoundException: If the API key is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, project.id)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in your project")

    try:
        await cluster_auth_client.revoke_api_key(api_key.cluster_auth_key_id)
        logger.info(f"Revoked API key {api_key.cluster_auth_key_id} in cluster-auth")
    except KeyError:
        logger.warning(
            f"API key {api_key.cluster_auth_key_id} not found in cluster-auth, proceeding with database deletion"
        )

    await delete_api_key(session, api_key)


async def renew_api_key_in_cluster_auth(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    api_key_id: UUID,
    cluster_auth_client: ClusterAuthClient,
    increment: str | None = None,
) -> dict:
    """
    Renew an API key in cluster-auth.

    Args:
        session: Database session
        organization: The organization (unused, kept for API compatibility)
        project: The project
        api_key_id: The ID of the API key
        cluster_auth_client: Cluster-auth client instance
        increment: Optional TTL increment

    Returns:
        dict with lease_duration

    Raises:
        NotFoundException: If the API key is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, project.id)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in your project")

    try:
        result = await cluster_auth_client.renew_api_key(api_key.cluster_auth_key_id, increment)
        logger.info(f"Renewed API key {api_key.cluster_auth_key_id} in cluster-auth")
        return result
    except (KeyError, ValueError) as e:
        logger.error(f"Failed to renew API key {api_key.cluster_auth_key_id}: {e}")
        raise NotFoundException(f"Failed to renew API key: {e}")


async def bind_api_key_to_group_in_cluster_auth(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    api_key_id: UUID,
    group_id: str,
    cluster_auth_client: ClusterAuthClient,
) -> dict:
    """
    Bind an API key to a group in cluster-auth.

    Args:
        session: Database session
        organization: The organization (unused, kept for API compatibility)
        project: The project
        api_key_id: The ID of the API key
        group_id: The ID of the group
        cluster_auth_client: Cluster-auth client instance

    Returns:
        dict with updated groups list

    Raises:
        NotFoundException: If the API key or group is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, project.id)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in your project")

    try:
        result = await cluster_auth_client.bind_api_key_to_group(api_key.cluster_auth_key_id, group_id)
        logger.info(f"Bound API key {api_key.cluster_auth_key_id} to group {group_id}")
        return result
    except KeyError as e:
        logger.error(f"Failed to bind API key to group: {e}")
        raise NotFoundException(f"Failed to bind API key to group: {e}")


async def unbind_api_key_from_group_in_cluster_auth(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    api_key_id: UUID,
    group_id: str,
    cluster_auth_client: ClusterAuthClient,
) -> dict:
    """
    Unbind an API key from a group in cluster-auth.

    Args:
        session: Database session
        organization: The organization (unused, kept for API compatibility)
        project: The project
        api_key_id: The ID of the API key
        group_id: The ID of the group
        cluster_auth_client: Cluster-auth client instance

    Returns:
        dict with updated groups list

    Raises:
        NotFoundException: If the API key or group is not found
    """
    api_key = await get_api_key_by_id(session, api_key_id, project.id)
    if not api_key:
        raise NotFoundException(f"API key with ID {api_key_id} not found in your project")

    try:
        result = await cluster_auth_client.unbind_api_key_from_group(api_key.cluster_auth_key_id, group_id)
        logger.info(f"Unbound API key {api_key.cluster_auth_key_id} from group {group_id}")
        return result
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"API key or group not found: {e}")
            raise NotFoundException("API key or group not found")
        raise
    except KeyError as e:
        logger.error(f"Failed to unbind API key from group: {e}")
        raise NotFoundException(f"Failed to unbind API key from group: {e}")


async def create_group_in_cluster_auth(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    cluster_auth_client: ClusterAuthClient,
    name: str | None = None,
    group_id: str | None = None,
) -> GroupResponse:
    """
    Create a group in cluster-auth.

    Args:
        session: Database session (unused, kept for API compatibility)
        organization: The organization (unused, kept for API compatibility)
        project: The project (unused, kept for API compatibility)
        cluster_auth_client: Cluster-auth client instance
        name: Optional name for the group
        group_id: Optional ID for the group

    Returns:
        GroupResponse with id and name

    Note:
        Groups are managed at the cluster-auth level and are not scoped to
        organizations or projects in this implementation.
    """

    try:
        result = await cluster_auth_client.create_group(name=name or "", group_id=group_id)
        logger.info(f"Created group {result['id']} with name {result['name']}")
        return GroupResponse(id=result["id"], name=result["name"])
    except Exception as e:
        logger.error(f"Failed to create group: {e}")
        raise


async def delete_group_from_cluster_auth(
    session: AsyncSession,
    organization: Organization,
    project: Project,
    group_id: str,
    cluster_auth_client: ClusterAuthClient,
) -> None:
    """
    Delete a group from cluster-auth.

    Args:
        session: Database session (unused, kept for API compatibility)
        organization: The organization (unused, kept for API compatibility)
        project: The project (unused, kept for API compatibility)
        group_id: The ID of the group to delete
        cluster_auth_client: Cluster-auth client instance

    Raises:
        NotFoundException: If the group is not found

    Note:
        Groups are managed at the cluster-auth level and are not scoped to
        organizations or projects in this implementation.
    """

    try:
        await cluster_auth_client.delete_group(group_id)
        logger.info(f"Deleted group {group_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Group {group_id} not found in cluster-auth")
            raise NotFoundException(f"Group with ID {group_id} not found")
        raise
    except KeyError:
        logger.warning(f"Group {group_id} not found in cluster-auth")
        raise NotFoundException(f"Group with ID {group_id} not found")
