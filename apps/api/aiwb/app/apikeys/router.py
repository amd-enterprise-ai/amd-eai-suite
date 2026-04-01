# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_email
from api_common.database import get_session
from api_common.schemas import ListResponse

from ..cluster_auth import get_cluster_auth_client
from ..cluster_auth.client import ClusterAuthClient
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..namespaces.security import ensure_access_to_workbench_namespace
from .schemas import (
    ApiKeyCreate,
    ApiKeyDetails,
    ApiKeyResponse,
    ApiKeyUpdate,
    ApiKeyWithFullKey,
    BindGroupRequest,
    GroupCreate,
    GroupResponse,
    RenewApiKeyResponse,
    UnbindGroupRequest,
)
from .service import (
    bind_api_key_to_group_in_cluster_auth,
    create_api_key_with_cluster_auth,
    create_group_in_cluster_auth,
    delete_api_key_from_cluster_auth,
    delete_group_from_cluster_auth,
    get_api_key_details_from_cluster_auth,
    list_api_keys_for_namespace,
    renew_api_key_in_cluster_auth,
    unbind_api_key_from_group_in_cluster_auth,
    update_api_key_bindings_with_cluster_auth,
)

router = APIRouter(tags=["API Keys"])


@router.get(
    "/namespaces/{namespace}/api-keys",
    operation_id="get_api_keys",
    summary="List API keys for a namespace",
    description=dedent("""List all API keys for a namespace.

    Returns truncated keys for security. Requires namespace access.
    API keys control access to deployed AIM inference endpoints and other namespace resources."""),
    status_code=status.HTTP_200_OK,
    response_model=ListResponse[ApiKeyResponse],
)
async def get_api_keys(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
) -> ListResponse[ApiKeyResponse]:
    """
    Get all API keys for a namespace.

    The user must have access to the namespace to view its API keys.
    API keys are returned with truncated values for security.
    """
    api_keys = await list_api_keys_for_namespace(session, namespace)
    return ListResponse(data=api_keys)


@router.post(
    "/namespaces/{namespace}/api-keys",
    operation_id="create_api_key",
    summary="Create a new API key",
    description=dedent("""Create a new API key for a namespace.

    The full API key is returned only once in the response and cannot be retrieved later.
    API keys can be bound to specific AIM deployments for scoped access control.
    Supports configurable TTL, renewability, and usage limits."""),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyWithFullKey,
)
async def create_api_key(
    api_key_in: ApiKeyCreate = Body(description="API key creation data"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    user: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> ApiKeyWithFullKey:
    """
    Create a new API key for a namespace.

    The full API key is returned in the response and should be saved by the client.
    It cannot be retrieved again later for security reasons.
    """
    return await create_api_key_with_cluster_auth(
        session, kube_client, namespace, api_key_in, user, cluster_auth_client
    )


@router.get(
    "/namespaces/{namespace}/api-keys/{api_key_id}",
    operation_id="get_api_key_details",
    summary="Get API key details",
    description=dedent("""Get detailed information about an API key.

    Includes metadata from Cluster Auth such as group bindings, TTL, expiration, and usage limits.
    Shows which AIM deployment groups the key can access. Requires namespace access."""),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyDetails,
)
async def get_api_key_details(
    api_key_id: UUID = Path(description="The ID of the API key"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> ApiKeyDetails:
    """
    Get detailed API key information.

    Includes metadata from both the database and Cluster Auth, such as group bindings.
    """
    return await get_api_key_details_from_cluster_auth(session, namespace, api_key_id, cluster_auth_client)


@router.patch(
    "/namespaces/{namespace}/api-keys/{api_key_id}",
    operation_id="update_api_key_bindings",
    summary="Update API key AIM deployment bindings",
    description=dedent("""Update which AIM deployments this API key can access.

    Provide a list of AIM IDs to bind the key to specific deployed models.
    Automatically manages underlying Cluster Auth group bindings.
    Replaces existing bindings - omit IDs to unbind from those deployments."""),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyDetails,
)
async def update_api_key_bindings(
    api_key_id: UUID = Path(description="The ID of the API key to update"),
    api_key_update: ApiKeyUpdate = Body(description="API key update data"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> ApiKeyDetails:
    """
    Update API key bindings to AIM groups.

    Accepts aim_ids and automatically manages the underlying group bindings in Cluster Auth.
    """
    api_key = await update_api_key_bindings_with_cluster_auth(
        session, kube_client, namespace, api_key_id, api_key_update, cluster_auth_client
    )
    return api_key


@router.delete(
    "/namespaces/{namespace}/api-keys/{api_key_id}",
    operation_id="delete_api_key",
    summary="Delete an API key",
    description=dedent("""Delete an API key and revoke it in Cluster Auth.

    This immediately revokes the key and removes it from all group bindings.
    The action cannot be undone. Requires namespace access."""),
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_api_key(
    api_key_id: UUID = Path(description="The ID of the API key to delete"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> None:
    """
    Delete an API key.

    The key will be revoked in Cluster Auth and removed from the database.
    """
    await delete_api_key_from_cluster_auth(session, namespace, api_key_id, cluster_auth_client)


@router.post(
    "/namespaces/{namespace}/api-keys/{api_key_id}/renew",
    operation_id="renew_api_key",
    summary="Renew an API key's lease",
    description=dedent("""Renew an API key's lease, extending its validity period.

    Only works for renewable keys.
    The key must not have exceeded its explicit_max_ttl if configured."""),
    status_code=status.HTTP_200_OK,
    response_model=RenewApiKeyResponse,
)
async def renew_api_key(
    api_key_id: UUID = Path(description="The ID of the API key to renew"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> RenewApiKeyResponse:
    """
    Renew an API key's lease.

    Extends the validity period of the API key if it is renewable.
    """
    result = await renew_api_key_in_cluster_auth(session, namespace, api_key_id, cluster_auth_client)
    return RenewApiKeyResponse(lease_duration=result["lease_duration"])


@router.post(
    "/namespaces/{namespace}/api-keys/{api_key_id}/bind-group",
    operation_id="bind_api_key_to_group",
    summary="Bind an API key to a Cluster Auth group",
    description=dedent("""Bind an API key to a Cluster Auth group.

    Low-level operation for direct group management. Consider using PATCH /namespaces/{namespace}/api-keys/{api_key_id}
    for AIM-based binding instead. Grants the API key access to resources associated with the group."""),
    status_code=status.HTTP_200_OK,
)
async def bind_api_key_to_group(
    api_key_id: UUID = Path(description="The ID of the API key"),
    bind_request: BindGroupRequest = Body(description="Group binding request"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> dict:
    """
    Bind an API key to a group.

    This allows the API key to access resources associated with the specified group.
    """
    return await bind_api_key_to_group_in_cluster_auth(
        session, namespace, api_key_id, bind_request.group_id, cluster_auth_client
    )


@router.post(
    "/namespaces/{namespace}/api-keys/{api_key_id}/unbind-group",
    operation_id="unbind_api_key_from_group",
    summary="Unbind an API key from a Cluster Auth group",
    description=dedent("""Remove an API key from a Cluster Auth group.

    Low-level operation for direct group management. Consider using PATCH /namespaces/{namespace}/api-keys/{api_key_id}
    for AIM-based binding instead. Revokes the API key's access to resources associated with the group."""),
    status_code=status.HTTP_200_OK,
)
async def unbind_api_key_from_group(
    api_key_id: UUID = Path(description="The ID of the API key"),
    unbind_request: UnbindGroupRequest = Body(description="Group unbinding request"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> dict:
    """
    Unbind an API key from a group.

    This revokes the API key's access to resources associated with the specified group.
    """
    return await unbind_api_key_from_group_in_cluster_auth(
        session, namespace, api_key_id, unbind_request.group_id, cluster_auth_client
    )


@router.post(
    "/api-keys/groups",
    operation_id="create_group",
    summary="Create or update a Cluster Auth group",
    description=dedent("""Create a new group or update an existing one in Cluster Auth.

    Groups control access to resources like AIM deployments. Typically managed automatically
    when deploying AIMs, but this endpoint allows manual group management for advanced use cases.

    - To create a new group: provide only the name (ID will be auto-generated)
    - To update an existing group: provide both name and the ID of the existing group"""),
    status_code=status.HTTP_200_OK,
    response_model=GroupResponse,
)
async def create_group(
    group_in: GroupCreate = Body(description="Group creation data"),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> GroupResponse:
    """
    Create a new group or update an existing one in Cluster Auth.

    Groups are used to bind API keys and control access to resources.
    Leave the ID empty to create a new group with an auto-generated ID.
    Provide an existing group ID to update that group's name.
    """
    return await create_group_in_cluster_auth(cluster_auth_client, group_in.name, group_in.id)


@router.delete(
    "/api-keys/groups/{group_id}",
    operation_id="delete_group",
    summary="Delete a Cluster Auth group",
    description=dedent("""Delete a group from Cluster Auth.

    This unbinds all API keys from the group and removes access to associated resources.
    AIM deployment groups are typically managed automatically during undeploy operations."""),
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_group(
    group_id: str = Path(description="The ID of the group to delete"),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> None:
    """
    Delete a group from Cluster Auth.

    This will remove the group and unbind all API keys that were associated with it.
    """
    await delete_group_from_cluster_auth(group_id, cluster_auth_client)
