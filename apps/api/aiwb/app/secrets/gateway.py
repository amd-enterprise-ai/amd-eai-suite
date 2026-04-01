# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Gateway for accessing Secret resources from Kubernetes."""

from kubernetes_asyncio.client import ApiException, V1ObjectMeta, V1Secret
from loguru import logger

from ..config import SUBMITTER_ANNOTATION
from ..dispatch.kube_client import KubernetesClient
from .constants import USE_CASE_LABEL
from .crds import KubernetesSecretResource
from .enums import SecretUseCase


def _convert_v1secret_to_crd(v1_secret: V1Secret) -> KubernetesSecretResource:
    """Convert a Kubernetes V1Secret to a KubernetesSecretResource CRD model.

    Args:
        v1_secret: Kubernetes V1Secret object from the Python client

    Returns:
        KubernetesSecretResource CRD model
    """
    secret_dict = {
        "metadata": {
            "name": v1_secret.metadata.name,
            "namespace": v1_secret.metadata.namespace,
            "labels": v1_secret.metadata.labels or {},
            "annotations": v1_secret.metadata.annotations or {},
            "creationTimestamp": v1_secret.metadata.creation_timestamp,
            "ownerReferences": [ref.to_dict() for ref in v1_secret.metadata.owner_references]
            if v1_secret.metadata.owner_references
            else [],
        },
    }
    return KubernetesSecretResource.model_validate(secret_dict)


async def list_kubernetes_secrets(
    kube_client: KubernetesClient,
    namespace: str,
) -> list[KubernetesSecretResource]:
    """List all Kubernetes Secrets in a namespace.

    Args:
        kube_client: Kubernetes client
        namespace: Namespace to search in

    Returns:
        List of KubernetesSecretResource CRD models
    """
    try:
        result = await kube_client.core_v1.list_namespaced_secret(namespace=namespace)

        secrets = []
        for item in result.items:
            try:
                secret = _convert_v1secret_to_crd(item)
                secrets.append(secret)
            except Exception as e:
                logger.warning(f"Failed to parse K8s Secret {item.metadata.name}: {e}")

        return secrets

    except ApiException as e:
        logger.error(f"Failed to list Kubernetes Secrets in namespace {namespace}: {e}")
        return []


async def get_kubernetes_secret(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
) -> KubernetesSecretResource | None:
    """Get a single Kubernetes Secret by name.

    Args:
        kube_client: Kubernetes client
        namespace: Namespace the secret is in
        name: Name of the secret

    Returns:
        KubernetesSecretResource if found, None otherwise
    """
    try:
        secret = await kube_client.core_v1.read_namespaced_secret(name=name, namespace=namespace)
        return _convert_v1secret_to_crd(secret)

    except ApiException as e:
        if e.status == 404:
            logger.debug(f"Secret {name} not found in namespace {namespace}")
            return None
        else:
            logger.error(f"Failed to get Secret {name} in namespace {namespace}: {e}")
            return None


async def create_kubernetes_secret(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
    data: dict[str, str],
    use_case: SecretUseCase | None = None,
    submitter: str | None = None,
) -> KubernetesSecretResource:
    """Create a new Kubernetes Secret.

    Args:
        kube_client: Kubernetes client
        namespace: Namespace to create the secret in
        name: Name of the secret
        data: Secret data as key-value pairs (base64-encoded values expected from UI)
        use_case: Optional use case classification
        submitter: Optional user identifier (e.g. email) who submitted the secret

    Returns:
        Created KubernetesSecretResource

    Raises:
        ApiException: If creation fails
    """
    # Build labels and annotations
    labels = {}
    if use_case:
        labels[USE_CASE_LABEL] = use_case.value
    annotations = {}
    if submitter:
        annotations[SUBMITTER_ANNOTATION] = submitter

    # Create Secret object
    # Use 'data' field to accept pre-encoded base64 values from UI (backward compatibility with old AIRM)
    # Kubernetes expects base64-encoded values in the 'data' field and will not double-encode them
    secret_kwargs: dict = {
        "metadata": V1ObjectMeta(
            name=name,
            namespace=namespace,
            labels=labels if labels else None,
            annotations=annotations if annotations else None,
        ),
        "data": data,
    }
    if use_case == SecretUseCase.IMAGE_PULL_SECRET:
        secret_kwargs["type"] = "kubernetes.io/dockerconfigjson"
    secret = V1Secret(**secret_kwargs)

    # Create in Kubernetes
    created_secret = await kube_client.core_v1.create_namespaced_secret(namespace=namespace, body=secret)
    return _convert_v1secret_to_crd(created_secret)


async def delete_kubernetes_secret(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
) -> None:
    """Delete a Kubernetes Secret.

    Args:
        kube_client: Kubernetes client
        namespace: Namespace the secret is in
        name: Name of the secret

    Raises:
        ApiException: If deletion fails
    """
    await kube_client.core_v1.delete_namespaced_secret(name=name, namespace=namespace)
