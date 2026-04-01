# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import base64
import json

from kubernetes_asyncio.client import ApiException
from loguru import logger

from api_common.exceptions import ConflictException, NotFoundException, ValidationException

from ..dispatch.kube_client import KubernetesClient
from .enums import SecretUseCase
from .gateway import (
    create_kubernetes_secret,
    delete_kubernetes_secret,
    get_kubernetes_secret,
    list_kubernetes_secrets,
)
from .schemas import SecretCreate, SecretResponse


async def list_secrets_for_namespace(
    kube_client: KubernetesClient,
    namespace: str,
    use_case: SecretUseCase | None = None,
) -> list[SecretResponse]:
    """
    List all Kubernetes Secrets in a namespace.

    Returns:
        List of secrets
    """
    secrets_crds = await list_kubernetes_secrets(kube_client=kube_client, namespace=namespace)
    secrets = [SecretResponse.model_validate(crd.model_dump()) for crd in secrets_crds]

    # Filter by use case if specified
    if use_case:
        secrets = [s for s in secrets if s.use_case == use_case]

    logger.debug(f"Found {len(secrets)} secrets in namespace {namespace}")
    return secrets


async def get_secret_details(
    kube_client: KubernetesClient,
    namespace: str,
    secret_name: str,
) -> SecretResponse:
    """
    Get detailed information about a specific secret.

    Returns:
        Detailed secret information

    Raises:
        NotFoundException: If the secret doesn't exist
    """
    secret_crd = await get_kubernetes_secret(kube_client=kube_client, namespace=namespace, name=secret_name)

    if not secret_crd:
        raise NotFoundException(f"Secret '{secret_name}' not found in namespace '{namespace}'")

    return SecretResponse.model_validate(secret_crd.model_dump())


async def create_secret(
    kube_client: KubernetesClient,
    namespace: str,
    secret_in: SecretCreate,
    submitter: str | None = None,
) -> SecretResponse:
    """
    Create a new Kubernetes Secret.

    Returns:
        Created secret

    Raises:
        ConflictException: If a secret with the same name already exists
        ValidationException: If image pull secret value is not valid JSON
    """
    if secret_in.use_case == SecretUseCase.IMAGE_PULL_SECRET:
        dockerconfig_b64 = secret_in.data.get(".dockerconfigjson")
        if dockerconfig_b64:
            try:
                payload = base64.b64decode(dockerconfig_b64, validate=True)
                json.loads(payload.decode("utf-8"))
            except (ValueError, json.JSONDecodeError) as e:
                raise ValidationException(
                    message='Image pull secret value must be valid Docker config JSON (e.g. {"auths":{"<registry>":{"username":"...","password":"...","auth":"..."}}}). Paste the JSON content, not YAML or other formats.',
                    detail=str(e),
                ) from e

    try:
        secret_crd = await create_kubernetes_secret(
            kube_client=kube_client,
            namespace=namespace,
            name=secret_in.name,
            data=secret_in.data,
            use_case=secret_in.use_case,
            submitter=submitter,
        )
        logger.info(f"Created secret '{secret_in.name}' in namespace '{namespace}'")
        return SecretResponse.model_validate(secret_crd.model_dump())
    except ApiException as e:
        if e.status == 409:
            raise ConflictException(f"Secret '{secret_in.name}' already exists in namespace '{namespace}'")
        raise


async def delete_secret(
    kube_client: KubernetesClient,
    namespace: str,
    secret_name: str,
) -> None:
    """
    Delete a Kubernetes Secret.

    Raises:
        NotFoundException: If the secret doesn't exist
        ConflictException: If the secret has an ownerReference
    """
    # First, get the secret to check if it has owner references
    secret_crd = await get_kubernetes_secret(kube_client=kube_client, namespace=namespace, name=secret_name)

    if not secret_crd:
        raise NotFoundException(f"Secret '{secret_name}' not found in namespace '{namespace}'")

    # Check if secret has owner references
    if secret_crd.metadata.owner_references:
        raise ConflictException(
            f"Cannot delete secret '{secret_name}' as it is managed by another resource. "
            f"Secrets with ownerReferences must be deleted by their owner."
        )

    try:
        await delete_kubernetes_secret(
            kube_client=kube_client,
            namespace=namespace,
            name=secret_name,
        )
        logger.info(f"Deleted secret '{secret_name}' from namespace '{namespace}'")
    except ApiException as e:
        if e.status == 404:
            raise NotFoundException(f"Secret '{secret_name}' not found in namespace '{namespace}'")
        raise
