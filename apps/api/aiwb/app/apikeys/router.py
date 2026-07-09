# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_email
from api_common.collections import PaginationMetadata
from api_common.database import get_session
from api_common.exceptions import UnhealthyException
from api_common.schemas import ListResponse, QueryParam

from ..cluster_auth import get_cluster_auth_client
from ..cluster_auth.client import ClusterAuthClient
from ..common_responses import CLUSTER_AUTH_RESPONSES, PROJECT_ACCESS_RESPONSES
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..metrics.client import get_prometheus_client
from ..metrics.schemas import MetricsTimeRange
from ..projects.security import ensure_access_to_project
from .schemas import (
    AddGroupMembershipRequest,
    ApiKeyCreate,
    ApiKeyDetails,
    ApiKeyMetricsResponse,
    ApiKeysList,
    ApiKeyUpdate,
    ApiKeyWithFullKey,
    GroupCreate,
    GroupResponse,
    ListApiKeysQuery,
    RenewApiKeyResponse,
)
from .service import (
    add_api_key_group_membership,
    create_api_key_with_cluster_auth,
    create_group_in_cluster_auth,
    delete_api_key_from_cluster_auth,
    delete_group_from_cluster_auth,
    get_api_key_details_from_cluster_auth,
    get_api_key_usage_metrics,
    list_api_key_group_memberships,
    list_api_keys_for_namespace,
    remove_api_key_group_membership,
    renew_api_key_in_cluster_auth,
    update_api_key_bindings_with_cluster_auth,
)

router = APIRouter(tags=["API Keys"])


def require_cluster_auth(
    cluster_auth_client: ClusterAuthClient | None = Depends(get_cluster_auth_client),
) -> ClusterAuthClient:
    """Raises 503 when cluster-auth is disabled or unavailable."""
    if cluster_auth_client is None:
        raise UnhealthyException(
            "API key operations require cluster-auth, which is currently disabled. "
            "Set CLUSTER_AUTH_ENABLED=true to enable this feature."
        )
    return cluster_auth_client


@router.get(
    "/projects/{project}/api-keys",
    operation_id="get_api_keys",
    summary="List API keys for a project",
    description=dedent("""
        List the API keys that belong to a project as a paginated envelope
        (default page size 10, max 100). Use `?page=` and `?pageSize=` to
        navigate; the response includes a `pagination` object with `page`,
        `pageSize`, and `total` alongside `data`.

        Each entry includes a truncated form of the key suitable for display
        (the full secret value is only ever returned once at creation). Use
        `GET /projects/{project}/api-keys/{apiKeyId}` to fetch the metadata
        and group bindings for a single key. All API key operations require
        cluster-auth to be enabled on the deployment.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeysList,
    responses={**PROJECT_ACCESS_RESPONSES, **CLUSTER_AUTH_RESPONSES},
)
async def get_api_keys(
    query: QueryParam[ListApiKeysQuery],
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
) -> ApiKeysList:
    paginated = await list_api_keys_for_namespace(session, project, page=query.page, page_size=query.page_size)
    return ApiKeysList(
        data=paginated.items,
        pagination=PaginationMetadata(
            page=paginated.page,
            page_size=paginated.page_size,
            total=paginated.total,
        ),
    )


@router.post(
    "/projects/{project}/api-keys",
    operation_id="create_api_key",
    summary="Create an API key",
    description=dedent("""
        Create a new API key for the project.

        The response includes the full secret value in `fullKey`; this is
        the only opportunity to read it. Once the response is consumed only
        the truncated key, metadata, and group bindings are retrievable.
        Persist the secret on the client side at this point.

        Optional `aimIds` bind the new key to specific deployed AIM
        inference services via the corresponding cluster-auth groups, so
        the key can only be used against those endpoints. `ttl`,
        `renewable`, `numUses`, `explicitMaxTtl`, and `period` map directly
        onto cluster-auth lease semantics. Cluster-auth must be enabled on
        the deployment.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyWithFullKey,
    response_description="Created key with the full secret value; persist it now — only the metadata is retrievable later.",
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        409: {"description": "An API key with this name already exists in the project."},
        502: {"description": "Cluster-auth synchronization failed while creating the key."},
    },
)
async def create_api_key(
    api_key_in: ApiKeyCreate = Body(description="API key creation data"),
    project: str = Depends(ensure_access_to_project),
    user: str = Depends(get_user_email),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> ApiKeyWithFullKey:
    return await create_api_key_with_cluster_auth(session, kube_client, project, api_key_in, user, cluster_auth_client)


@router.get(
    "/projects/{project}/api-keys/{api_key_id}",
    operation_id="get_api_key_details",
    summary="Get API key details",
    description=dedent("""
        Get the metadata and current lease state for one API key in the
        project.

        The response merges the DB record (name, namespace, truncated key)
        with live cluster-auth data: `ttl`, `expiresAt`, `renewable`,
        `numUses`, and the groups the key is bound to. Use this in place of
        the list endpoint when you need group bindings or the current
        expiry. The full secret value is never returned here.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyDetails,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        404: {"description": "Project or namespace not found, or API key not found in the project."},
    },
)
async def get_api_key_details(
    api_key_id: UUID = Path(description="The ID of the API key"),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> ApiKeyDetails:
    return await get_api_key_details_from_cluster_auth(session, project, api_key_id, cluster_auth_client)


@router.patch(
    "/projects/{project}/api-keys/{api_key_id}",
    operation_id="update_api_key_bindings",
    summary="Update API key AIM deployment bindings",
    description=dedent("""
        Update the API key's bindings, replacing the set of AIM deployments
        it is permitted to call.

        `aimIds` is treated as the complete desired set: AIMs present in
        the request are bound (the corresponding cluster-auth groups are
        added), and AIMs that were previously bound but absent from the
        request are unbound. To revoke all bindings, send an empty list.
        For fine-grained group control (raw cluster-auth group IDs rather
        than AIM IDs), use the `/{apiKeyId}/groups` sub-resource instead.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyDetails,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        404: {"description": "Project or namespace not found, or API key not found in the project."},
        502: {"description": "Cluster-auth group binding update failed."},
    },
)
async def update_api_key_bindings(
    api_key_id: UUID = Path(description="The ID of the API key to update"),
    api_key_update: ApiKeyUpdate = Body(description="API key update data"),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> ApiKeyDetails:
    return await update_api_key_bindings_with_cluster_auth(
        session, kube_client, project, api_key_id, api_key_update, cluster_auth_client
    )


@router.delete(
    "/projects/{project}/api-keys/{api_key_id}",
    operation_id="delete_api_key",
    summary="Delete an API key",
    description=dedent("""
        Permanently delete an API key.

        The key is revoked in cluster-auth, removed from every group it was
        bound to, and the corresponding DB record is deleted. Existing
        clients holding the secret will receive 401 from inference
        endpoints on the next request. The operation cannot be undone.
    """),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        404: {"description": "Project or namespace not found, or API key not found."},
    },
)
async def delete_api_key(
    api_key_id: UUID = Path(description="The ID of the API key to delete"),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> None:
    await delete_api_key_from_cluster_auth(session, project, api_key_id, cluster_auth_client)


@router.post(
    "/projects/{project}/api-keys/{api_key_id}/renew",
    operation_id="renew_api_key",
    summary="Renew an API key's lease",
    description=dedent("""
        Extend the lease on an API key so it remains valid past its current
        expiry.

        Only keys created with `renewable=true` can be renewed. The new
        lease duration is bounded by the key's `explicitMaxTtl` (if set at
        creation): once a renewal would cross that ceiling, cluster-auth
        rejects the request and the endpoint returns 404. Periodic keys
        (created with `period`) renew for a fresh `period` each time and
        do not accrue toward a max TTL.
    """),
    status_code=status.HTTP_200_OK,
    response_model=RenewApiKeyResponse,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        404: {
            "description": "Project or namespace not found, or API key not found, or renewal rejected by cluster-auth (e.g., explicit_max_ttl reached)."
        },
    },
)
async def renew_api_key(
    api_key_id: UUID = Path(description="The ID of the API key to renew"),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> RenewApiKeyResponse:
    result = await renew_api_key_in_cluster_auth(session, project, api_key_id, cluster_auth_client)
    return RenewApiKeyResponse(lease_duration=result["lease_duration"])


@router.get(
    "/projects/{project}/api-keys/{api_key_id}/groups",
    operation_id="list_api_key_groups",
    summary="List the cluster-auth groups this API key belongs to",
    description=dedent("""
        List the raw cluster-auth group IDs the API key is currently a
        member of.

        Returns group IDs rather than AIM IDs — use this when you need to
        inspect or manage memberships at the cluster-auth layer directly.
        For the higher-level AIM-deployment binding view, prefer the
        `aimIds` field returned by `GET /projects/{project}/api-keys/{apiKeyId}`.
        For lifecycle of the group entities themselves (create / delete),
        see `/api-keys/groups`.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ListResponse[str],
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        404: {"description": "Project or namespace not found, or API key not found."},
    },
)
async def list_api_key_groups(
    api_key_id: UUID = Path(description="The ID of the API key"),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> ListResponse[str]:
    groups = await list_api_key_group_memberships(session, project, api_key_id, cluster_auth_client)
    return ListResponse(data=groups)


@router.post(
    "/projects/{project}/api-keys/{api_key_id}/groups",
    operation_id="add_api_key_to_group",
    summary="Add this API key to a cluster-auth group",
    description=dedent("""
        Add the API key to a single cluster-auth group, granting it access
        to whatever resources that group permits.

        This is the low-level counterpart to PATCHing `aimIds` on the key.
        Use it when you need to bind to a group that does not correspond to
        an AIM deployment (e.g., a manually managed group), or when
        composing memberships incrementally. The returned list is the full
        current set of group memberships after the addition. Group
        entities are created via `POST /api-keys/groups`.
    """),
    status_code=status.HTTP_201_CREATED,
    response_model=ListResponse[str],
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        404: {"description": "Project or namespace not found, or API key or group not found."},
    },
)
async def add_api_key_to_group(
    api_key_id: UUID = Path(description="The ID of the API key"),
    add_request: AddGroupMembershipRequest = Body(description="Group membership request"),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> ListResponse[str]:
    groups = await add_api_key_group_membership(session, project, api_key_id, add_request.group_id, cluster_auth_client)
    return ListResponse(data=groups)


@router.delete(
    "/projects/{project}/api-keys/{api_key_id}/groups/{group_id}",
    operation_id="remove_api_key_from_group",
    summary="Remove this API key from a cluster-auth group",
    description=dedent("""
        Revoke the API key's membership in a single cluster-auth group.

        After removal the key can no longer access resources gated only by
        that group. Other memberships are untouched. This endpoint operates
        on the membership relationship; the group entity itself remains
        and is deleted via `DELETE /api-keys/groups/{groupId}`.
    """),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        **CLUSTER_AUTH_RESPONSES,
        404: {
            "description": "Project or namespace not found, or API key or group not found, or membership did not exist."
        },
    },
)
async def remove_api_key_from_group(
    api_key_id: UUID = Path(description="The ID of the API key"),
    group_id: str = Path(description="The ID of the group to remove the API key from"),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> None:
    await remove_api_key_group_membership(session, project, api_key_id, group_id, cluster_auth_client)


@router.post(
    "/api-keys/groups",
    operation_id="create_group",
    summary="Create or rename a cluster-auth group",
    description=dedent("""
        Create a new cluster-auth group, or rename an existing one.

        Provide only `name` to create a new group; cluster-auth allocates
        the group ID and returns it. Provide both `id` and `name` to update
        the display name of an existing group in place.

        AIM-deployment groups are normally managed automatically when
        deploying or undeploying AIMs — use this endpoint for advanced or
        manual cluster-auth group management. To add an API key to an
        existing group, use
        `POST /projects/{project}/api-keys/{apiKeyId}/groups` instead.
    """),
    status_code=status.HTTP_200_OK,
    response_model=GroupResponse,
    responses={
        **CLUSTER_AUTH_RESPONSES,
        404: {"description": "Group ID supplied but not found in cluster-auth."},
    },
)
async def create_group(
    group_in: GroupCreate = Body(description="Group creation data"),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> GroupResponse:
    return await create_group_in_cluster_auth(cluster_auth_client, group_in.name, group_in.id)


@router.delete(
    "/api-keys/groups/{group_id}",
    operation_id="delete_group",
    summary="Delete a cluster-auth group",
    description=dedent("""
        Delete a cluster-auth group entity.

        Every API key that was a member of the group loses that membership
        as part of the same operation; the keys themselves are not
        deleted. AIM-deployment groups are normally cleaned up automatically
        on undeploy — use this endpoint for manual or stranded groups. To
        remove a single API key from a group without deleting the group,
        use `DELETE /projects/{project}/api-keys/{apiKeyId}/groups/{groupId}`.
    """),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **CLUSTER_AUTH_RESPONSES,
        404: {"description": "Group not found."},
    },
)
async def delete_group(
    group_id: str = Path(description="The ID of the group to delete"),
    cluster_auth_client: ClusterAuthClient = Depends(require_cluster_auth),
) -> None:
    await delete_group_from_cluster_auth(group_id, cluster_auth_client)


@router.get(
    "/projects/{project}/api-keys/{api_key_id}/metrics",
    operation_id="get_api_key_metrics",
    summary="Get usage metrics for an API key",
    description=dedent("""
        Get aggregated usage metrics for an API key over a time range.

        Returns token consumption and request counts broken down by AIM service and time bucket.
        Sourced from AI Gateway ext-proc metrics via Prometheus.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ApiKeyMetricsResponse,
    responses={**PROJECT_ACCESS_RESPONSES},
)
async def get_api_key_metrics_endpoint(
    api_key_id: UUID = Path(description="The ID of the API key"),
    time_range: MetricsTimeRange = Depends(),
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> ApiKeyMetricsResponse:
    return await get_api_key_usage_metrics(
        session=session,
        namespace=project,
        api_key_id=api_key_id,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
    )
