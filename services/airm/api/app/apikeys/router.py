# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..organizations.models import Organization
from ..projects.models import Project
from ..utilities.database import get_session
from ..utilities.security import get_user_email, get_user_organization, validate_and_get_project_from_query
from .cluster_auth_client import ClusterAuthClient, get_cluster_auth_client
from .schemas import (
    ApiKeyCreate,
    ApiKeyDetails,
    ApiKeysResponse,
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
    list_api_keys_for_project,
    renew_api_key_in_cluster_auth,
    unbind_api_key_from_group_in_cluster_auth,
    update_api_key_bindings_with_cluster_auth,
)

router = APIRouter(tags=["API Keys"])


@router.get(
    "/api-keys",
    operation_id="get_api_keys",
    summary="List API keys for a project",
    description="""List all API keys for a project.

    Returns truncated keys for security. Requires project membership.
    API keys control access to deployed AIM inference endpoints and other project resources.""",
    status_code=status.HTTP_200_OK,
    response_model=ApiKeysResponse,
)
async def get_api_keys(
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
) -> ApiKeysResponse:
    """
    Get all API keys for a project.

    The user must be a member of the project to access its API keys.
    API keys are returned with truncated values for security.
    """
    api_keys = await list_api_keys_for_project(session, organization, project)
    return ApiKeysResponse(data=api_keys)


@router.post(
    "/api-keys",
    operation_id="create_api_key",
    summary="Create a new API key",
    description="""Create a new API key for a project.

    The full API key is returned only once in the response and cannot be retrieved later.
    API keys can be bound to specific AIM deployments for scoped access control.
    Supports configurable TTL, renewability, and usage limits.""",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyWithFullKey,
)
async def create_api_key(
    api_key_in: ApiKeyCreate = Body(description="API key creation data"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    user: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> ApiKeyWithFullKey:
    """
    Create a new API key for a project.

    The full API key is returned in the response and should be saved by the client.
    It cannot be retrieved again later for security reasons.
    """
    return await create_api_key_with_cluster_auth(session, organization, project, api_key_in, user, cluster_auth_client)


@router.get(
    "/api-keys/{api_key_id}",
    operation_id="get_api_key_details",
    summary="Get API key details",
    description="""Get detailed information about an API key.

    Includes metadata from Cluster Auth such as group bindings, TTL, expiration, and usage limits.
    Shows which AIM deployment groups the key can access. Requires project membership.""",
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyDetails,
)
async def get_api_key_details(
    api_key_id: UUID = Path(description="The ID of the API key"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> ApiKeyDetails:
    """
    Get detailed API key information.

    Includes metadata from both the database and Cluster Auth, such as group bindings.
    """
    return await get_api_key_details_from_cluster_auth(session, organization, project, api_key_id, cluster_auth_client)


@router.patch(
    "/api-keys/{api_key_id}",
    operation_id="update_api_key_bindings",
    summary="Update API key AIM deployment bindings",
    description="""Update which AIM deployments this API key can access.

    Provide a list of AIM IDs to bind the key to specific deployed models.
    Automatically manages underlying Cluster Auth group bindings.
    Replaces existing bindings - omit IDs to unbind from those deployments.""",
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyDetails,
)
async def update_api_key_bindings(
    api_key_id: UUID = Path(description="The ID of the API key to update"),
    api_key_update: ApiKeyUpdate = Body(description="API key update data"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> ApiKeyDetails:
    """
    Update API key bindings to AIM groups.

    Accepts aim_ids and automatically manages the underlying group bindings in Cluster Auth.
    """
    api_key = await update_api_key_bindings_with_cluster_auth(
        session, organization, project, api_key_id, api_key_update, cluster_auth_client
    )
    return api_key


@router.delete(
    "/api-keys/{api_key_id}",
    operation_id="delete_api_key",
    summary="Delete an API key",
    description="""Delete an API key and revoke it in Cluster Auth.

    This immediately revokes the key and removes it from all group bindings.
    The action cannot be undone. Requires project membership.""",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_api_key(
    api_key_id: UUID = Path(description="The ID of the API key to delete"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> None:
    """
    Delete an API key.

    The key will be revoked in Cluster Auth and removed from the database.
    """
    await delete_api_key_from_cluster_auth(session, organization, project, api_key_id, cluster_auth_client)


@router.post(
    "/api-keys/{api_key_id}/renew",
    operation_id="renew_api_key",
    summary="Renew an API key's lease",
    description="""Renew an API key's lease, extending its validity period.

    Only works for renewable keys. Optionally provide a TTL increment (e.g., '1h', '24h').
    The key must not have exceeded its explicit_max_ttl if configured.""",
    status_code=status.HTTP_200_OK,
    response_model=RenewApiKeyResponse,
)
async def renew_api_key(
    api_key_id: UUID = Path(description="The ID of the API key to renew"),
    increment: str | None = Query(None, description="Optional TTL increment (e.g., '1h', '24h')"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> RenewApiKeyResponse:
    """
    Renew an API key's lease.

    Extends the validity period of the API key if it is renewable.
    """
    result = await renew_api_key_in_cluster_auth(
        session, organization, project, api_key_id, cluster_auth_client, increment
    )
    return RenewApiKeyResponse(lease_duration=result["lease_duration"])


@router.post(
    "/api-keys/{api_key_id}/bind-group",
    operation_id="bind_api_key_to_group",
    summary="Bind an API key to a Cluster Auth group",
    description="""Bind an API key to a Cluster Auth group.

    Low-level operation for direct group management. Consider using PATCH /api-keys/{api_key_id}
    for AIM-based binding instead. Grants the API key access to resources associated with the group.""",
    status_code=status.HTTP_200_OK,
)
async def bind_api_key_to_group(
    api_key_id: UUID = Path(description="The ID of the API key"),
    bind_request: BindGroupRequest = Body(description="Group binding request"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> dict:
    """
    Bind an API key to a group.

    This allows the API key to access resources associated with the specified group.
    """
    return await bind_api_key_to_group_in_cluster_auth(
        session, organization, project, api_key_id, bind_request.group_id, cluster_auth_client
    )


@router.post(
    "/api-keys/{api_key_id}/unbind-group",
    operation_id="unbind_api_key_from_group",
    summary="Unbind an API key from a Cluster Auth group",
    description="""Remove an API key from a Cluster Auth group.

    Low-level operation for direct group management. Consider using PATCH /api-keys/{api_key_id}
    for AIM-based binding instead. Revokes the API key's access to resources associated with the group.""",
    status_code=status.HTTP_200_OK,
)
async def unbind_api_key_from_group(
    api_key_id: UUID = Path(description="The ID of the API key"),
    unbind_request: UnbindGroupRequest = Body(description="Group unbinding request"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> dict:
    """
    Unbind an API key from a group.

    This revokes the API key's access to resources associated with the specified group.
    """
    return await unbind_api_key_from_group_in_cluster_auth(
        session, organization, project, api_key_id, unbind_request.group_id, cluster_auth_client
    )


@router.post(
    "/api-keys/groups",
    operation_id="create_group",
    summary="Create a Cluster Auth group",
    description="""Create a new group in Cluster Auth for binding API keys.

    Groups control access to resources like AIM deployments. Typically managed automatically
    when deploying AIMs, but this endpoint allows manual group creation for advanced use cases.""",
    status_code=status.HTTP_201_CREATED,
    response_model=GroupResponse,
)
async def create_group(
    group_in: GroupCreate = Body(description="Group creation data"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> GroupResponse:
    """
    Create a new group in Cluster Auth.

    Groups are used to bind API keys and control access to resources.
    The name is required. The ID will be auto-generated if not provided.
    """
    return await create_group_in_cluster_auth(
        session, organization, project, cluster_auth_client, group_in.name, group_in.id
    )


@router.delete(
    "/api-keys/groups/{group_id}",
    operation_id="delete_group",
    summary="Delete a Cluster Auth group",
    description="""Delete a group from Cluster Auth.

    This unbinds all API keys from the group and removes access to associated resources.
    AIM deployment groups are typically managed automatically during undeploy operations.""",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_group(
    group_id: str = Path(description="The ID of the group to delete"),
    project: Project = Depends(validate_and_get_project_from_query),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(get_cluster_auth_client),
) -> None:
    """
    Delete a group from Cluster Auth.

    This will remove the group and unbind all API keys that were associated with it.
    """
    await delete_group_from_cluster_auth(session, organization, project, group_id, cluster_auth_client)
