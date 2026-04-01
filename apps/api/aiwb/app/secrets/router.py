# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent

from fastapi import APIRouter, Body, Depends, Path, Query, status

from api_common.auth.security import get_user_email
from api_common.schemas import ListResponse

from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..namespaces.security import ensure_access_to_workbench_namespace
from .enums import SecretUseCase
from .schemas import SecretCreate, SecretResponse
from .service import create_secret, delete_secret, get_secret_details, list_secrets_for_namespace

router = APIRouter(tags=["Secrets"])


@router.get(
    "/namespaces/{namespace}/secrets",
    operation_id="get_secrets",
    summary="List secrets for a namespace",
    description=dedent("""
        List all Kubernetes Secrets in a namespace.

        Returns all secrets from the namespace, read directly from Kubernetes on-demand.
        Optionally filter by use case if the secret has the appropriate label.

        Note: Only native Kubernetes Secrets are returned, not ExternalSecrets or other CRDs.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ListResponse[SecretResponse],
)
async def get_secrets(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
    use_case: SecretUseCase | None = Query(None, description="Filter by use case"),
) -> ListResponse[SecretResponse]:
    """
    Get all secrets for a namespace.

    Reads all secrets directly from Kubernetes.
    """
    secrets = await list_secrets_for_namespace(
        kube_client=kube_client,
        namespace=namespace,
        use_case=use_case,
    )
    return ListResponse(data=secrets)


@router.post(
    "/namespaces/{namespace}/secrets",
    operation_id="create_secret",
    summary="Create a new secret",
    description=dedent("""
        Create a new Kubernetes Secret in a namespace.

        The secret will be created with AIWB management labels automatically.
        Secret data values are base64-encoded automatically by Kubernetes.

        Example use case: Creating a HuggingFace token secret.
    """),
    status_code=status.HTTP_201_CREATED,
    response_model=SecretResponse,
)
async def create_secret_endpoint(
    secret_in: SecretCreate = Body(description="Secret data to create"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
    submitter: str = Depends(get_user_email),
) -> SecretResponse:
    """
    Create a new secret in the namespace.

    The secret will be created directly in Kubernetes with AIWB management labels
    and annotations, including airm.silogen.ai/submitter (annotation) to identify the submitting user.
    """
    return await create_secret(
        kube_client=kube_client,
        namespace=namespace,
        secret_in=secret_in,
        submitter=submitter,
    )


@router.get(
    "/namespaces/{namespace}/secrets/{secret_name}",
    operation_id="get_secret_details",
    summary="Get secret details",
    description=dedent("""
        Get detailed information about a specific secret.

        Returns metadata about the secret.
    """),
    status_code=status.HTTP_200_OK,
    response_model=SecretResponse,
)
async def get_secret(
    secret_name: str = Path(description="The name of the secret"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> SecretResponse:
    """
    Get detailed secret information.

    Returns metadata about the secret.
    """
    return await get_secret_details(
        kube_client=kube_client,
        namespace=namespace,
        secret_name=secret_name,
    )


@router.delete(
    "/namespaces/{namespace}/secrets/{secret_name}",
    operation_id="delete_secret",
    summary="Delete a secret",
    description=dedent("""
        Delete a Kubernetes Secret.

        This removes the Secret resource from Kubernetes.
        This action cannot be undone.
    """),
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_secret_endpoint(
    secret_name: str = Path(description="The name of the secret to delete"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> None:
    """
    Delete a secret from Kubernetes.

    The secret will be permanently removed.
    """
    await delete_secret(
        kube_client=kube_client,
        namespace=namespace,
        secret_name=secret_name,
    )
