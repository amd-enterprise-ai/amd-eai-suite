# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent

from fastapi import APIRouter, Body, Depends, Path, status

from api_common.auth.security import get_user_email
from api_common.collections import PaginationMetadata, paginate_list
from api_common.schemas import QueryParam

from ..common_responses import PROJECT_ACCESS_RESPONSES
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..projects.security import ensure_access_to_project
from .schemas import SecretCreate, SecretListQuery, SecretResponse, SecretsList
from .service import create_secret, delete_secret, get_secret_details, list_secrets_for_namespace

router = APIRouter(tags=["Secrets"])


@router.get(
    "/projects/{project}/secrets",
    operation_id="get_secrets",
    summary="List secrets for a project",
    description=dedent("""
        List Kubernetes Secrets in a project as a paginated envelope
        (default page size 10, max 100). Use `?page=` and `?pageSize=` to
        navigate; the response includes a `pagination` object with `page`,
        `pageSize`, and `total` alongside `data`.

        Returns all secrets in the project, read directly from Kubernetes on-demand
        (no DB-backed cache). Optionally filter by use case (e.g. `?useCase=hfToken`)
        when the secret has the matching AIWB label. Pagination is applied after
        filtering, so `total` reflects the filtered set.

        Note: only native Kubernetes Secrets are returned — ExternalSecrets and other
        secret-management CRDs are not surfaced through this endpoint. Secret values
        are never returned, only metadata (name, labels, annotations, data keys).
    """),
    status_code=status.HTTP_200_OK,
    response_model=SecretsList,
    responses={
        **PROJECT_ACCESS_RESPONSES,
    },
)
async def get_secrets(
    query: QueryParam[SecretListQuery],
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> SecretsList:
    secrets = await list_secrets_for_namespace(
        kube_client=kube_client,
        namespace=project,
        use_case=query.use_case,
    )
    result = paginate_list(secrets, page=query.page, page_size=query.page_size)
    return SecretsList(
        data=result.items,
        pagination=PaginationMetadata(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
        ),
    )


@router.post(
    "/projects/{project}/secrets",
    operation_id="create_secret",
    summary="Create a secret",
    description=dedent("""
        Create a new Kubernetes Secret in a project.

        Secret names must be unique within the project namespace and conform to
        Kubernetes DNS subdomain rules (lowercase, digits, dashes; see
        the `name` field pattern for the exact regex).

        Values supplied in `data` are stored verbatim — provide them already
        base64-encoded if the consumer expects raw bytes (the Kubernetes Secret
        `data` field requires base64). The secret is tagged with AIWB
        management labels and a `submitter` annotation derived from the JWT.

        For image-pull-secret use cases, the `.dockerconfigjson` value must
        decode to valid Docker config JSON or the request is rejected with 400.

        Secrets are not versioned by this API: a duplicate name returns 409
        rather than overwriting; delete-and-recreate to rotate values.
    """),
    status_code=status.HTTP_201_CREATED,
    response_model=SecretResponse,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        400: {"description": "Invalid `.dockerconfigjson` payload for an image-pull-secret."},
        409: {"description": "A secret with this name already exists in the project."},
        422: {"description": "Secret name does not match the required pattern."},
    },
)
async def create_secret_endpoint(
    secret_in: SecretCreate = Body(description="Secret data to create"),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
    submitter: str = Depends(get_user_email),
) -> SecretResponse:
    """
    Create a new secret in the project.

    The secret will be created directly in Kubernetes with AIWB management labels
    and annotations, including airm.silogen.ai/submitter (annotation) to identify the submitting user.
    """
    return await create_secret(
        kube_client=kube_client,
        namespace=project,
        secret_in=secret_in,
        submitter=submitter,
    )


@router.get(
    "/projects/{project}/secrets/{secret_name}",
    operation_id="get_secret_details",
    summary="Get a secret",
    description=dedent("""
        Get metadata about a specific Kubernetes Secret in the project.

        Returns the secret's metadata (name, labels, annotations, data keys)
        but never the secret values themselves — secret material is only ever
        consumed in-cluster by the workloads that mount it.
    """),
    status_code=status.HTTP_200_OK,
    response_model=SecretResponse,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "Project or namespace not found, or secret not found."},
    },
)
async def get_secret(
    secret_name: str = Path(description="The name of the secret"),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> SecretResponse:
    """
    Get detailed secret information.

    Returns metadata about the secret.
    """
    return await get_secret_details(
        kube_client=kube_client,
        namespace=project,
        secret_name=secret_name,
    )


@router.delete(
    "/projects/{project}/secrets/{secret_name}",
    operation_id="delete_secret",
    summary="Delete a secret",
    description=dedent("""
        Delete a Kubernetes Secret from the project.

        This is a hard delete and cannot be undone. Secrets owned by another
        Kubernetes resource (i.e. carrying an `ownerReference`, typically from
        an AIWB-managed workload) cannot be deleted directly via this endpoint
        — delete the owning resource instead, and the secret will be
        garbage-collected. Such cases surface as 409.
    """),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "Project or namespace not found, or secret not found."},
        409: {
            "description": (
                "Secret cannot be deleted (e.g., still referenced by an AIWB-managed resource via an ownerReference)."
            )
        },
    },
)
async def delete_secret_endpoint(
    secret_name: str = Path(description="The name of the secret to delete"),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> None:
    """
    Delete a secret from Kubernetes.

    The secret will be permanently removed.
    """
    await delete_secret(
        kube_client=kube_client,
        namespace=project,
        secret_name=secret_name,
    )
