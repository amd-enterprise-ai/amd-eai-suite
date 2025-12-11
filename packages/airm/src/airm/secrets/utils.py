# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from airm.messaging.schemas import SecretKind

from .constants import (
    EXTERNAL_SECRETS_API_GROUP,
    EXTERNAL_SECRETS_KIND,
    KUBERNETES_SECRET_API_VERSION,
    KUBERNETES_SECRET_KIND,
)


class KubernetesMetadata(BaseModel):
    """Kubernetes metadata section."""

    name: str | None = None
    namespace: str | None = None
    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None

    class Config:
        extra = "allow"  # Allow additional fields like resourceVersion, uid, etc.


class ExternalSecretManifest(BaseModel):
    """
    Pydantic model for ExternalSecret manifest.
    Validates basic structure; full validation performed by Kubernetes client in dispatcher.
    """

    apiVersion: str
    kind: str
    metadata: KubernetesMetadata
    spec: dict[str, Any]  # Spec is validated by Kubernetes, keep flexible

    @field_validator("apiVersion")
    @classmethod
    def validate_api_version(cls, v: str) -> str:
        if not v.startswith(f"{EXTERNAL_SECRETS_API_GROUP}/"):
            raise ValueError(f"apiVersion must start with '{EXTERNAL_SECRETS_API_GROUP}/', got '{v}'")
        return v

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v != EXTERNAL_SECRETS_KIND:
            raise ValueError(f"kind must be '{EXTERNAL_SECRETS_KIND}', got '{v}'")
        return v

    class Config:
        extra = "allow"  # Allow additional fields


class KubernetesSecretManifest(BaseModel):
    """
    Pydantic model for Kubernetes Secret manifest.
    Validates basic structure; full validation performed by Kubernetes client in dispatcher.
    """

    apiVersion: str
    kind: str
    metadata: KubernetesMetadata
    data: dict[str, str] | None = None
    stringData: dict[str, str] | None = None
    type: str | None = Field(default="Opaque")

    @field_validator("apiVersion")
    @classmethod
    def validate_api_version(cls, v: str) -> str:
        if v != KUBERNETES_SECRET_API_VERSION:
            raise ValueError(f"apiVersion must be '{KUBERNETES_SECRET_API_VERSION}', got '{v}'")
        return v

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v != KUBERNETES_SECRET_KIND:
            raise ValueError(f"kind must be '{KUBERNETES_SECRET_KIND}', got '{v}'")
        return v

    class Config:
        extra = "allow"  # Allow additional fields


def _load_single_manifest(manifest_yaml: str) -> dict:
    """Load and parse a single YAML manifest."""
    try:
        manifests = list(yaml.safe_load_all(manifest_yaml))
    except yaml.YAMLError as e:
        raise Exception(f"Failed to load YAML: {e}")

    if len(manifests) != 1:
        raise Exception(f"Expected 1 manifest, but got {len(manifests)}")

    manifest = manifests[0]

    if not isinstance(manifest, dict):
        raise Exception("Manifest is malformed")

    return manifest


def validate_external_secret_manifest(manifest_yaml: str) -> dict:
    """
    Parses and validates an ExternalSecret manifest from YAML.

    Uses Pydantic for basic structure validation. Full validation is performed
    by the Kubernetes client in the dispatcher for comprehensive schema validation.

    Args:
        manifest_yaml: YAML string containing the manifest

    Returns:
        dict: Validated manifest as dictionary for Kubernetes client

    Raises:
        Exception: if YAML is invalid or validation fails
    """
    manifest_dict = _load_single_manifest(manifest_yaml)

    try:
        # Parse and validate with Pydantic
        manifest_model = ExternalSecretManifest(**manifest_dict)
        # Return as dict for downstream Kubernetes client usage
        return manifest_model.model_dump(by_alias=True, exclude_none=True)
    except Exception as e:
        raise Exception(f"Invalid ExternalSecret manifest: {e}")


def validate_kubernetes_secret_manifest(manifest_yaml: str) -> dict:
    """
    Parses and validates a Kubernetes Secret manifest from YAML.

    Uses Pydantic for basic structure validation. Full validation is performed
    by the Kubernetes client in the dispatcher for comprehensive schema validation.

    Args:
        manifest_yaml: YAML string containing the manifest

    Returns:
        dict: Validated manifest as dictionary for Kubernetes client

    Raises:
        Exception: if YAML is invalid or validation fails
    """
    manifest_dict = _load_single_manifest(manifest_yaml)

    try:
        # Parse and validate with Pydantic
        manifest_model = KubernetesSecretManifest(**manifest_dict)
        # Return as dict for downstream Kubernetes client usage
        return manifest_model.model_dump(by_alias=True, exclude_none=True)
    except Exception as e:
        raise Exception(f"Invalid Kubernetes Secret manifest: {e}")


def validate_secret_manifest(manifest_yaml: str, component_kind: SecretKind) -> dict:
    """
    Universal validator for secret manifests.

    Routes to the appropriate validator based on the component kind.
    This is the package-level validator that should be used by both API and dispatcher.

    Args:
        manifest_yaml: YAML string containing the manifest
        component_kind: The SecretKind enum value

    Returns:
        dict: Validated manifest as dictionary for Kubernetes client

    Raises:
        Exception: if YAML is invalid or validation fails
        ValueError: if component_kind is unsupported
    """
    match component_kind:
        case SecretKind.EXTERNAL_SECRET:
            return validate_external_secret_manifest(manifest_yaml)
        case SecretKind.KUBERNETES_SECRET:
            return validate_kubernetes_secret_manifest(manifest_yaml)
        case _:
            raise ValueError(f"Unsupported component kind: {component_kind}")


def get_kubernetes_kind(component_kind: SecretKind) -> str:
    """
    Maps SecretKind enum values to actual Kubernetes resource kinds.

    This is needed because the enum uses "KubernetesSecret" but the Kubernetes API
    expects "Secret" for native Kubernetes secrets.

    Args:
        component_kind: The SecretKind enum value

    Returns:
        str: The actual Kubernetes resource kind string

    Raises:
        ValueError: if component_kind is unsupported
    """
    match component_kind:
        case SecretKind.EXTERNAL_SECRET:
            return EXTERNAL_SECRETS_KIND
        case SecretKind.KUBERNETES_SECRET:
            return KUBERNETES_SECRET_KIND
        case _:
            raise ValueError(f"Unsupported component kind: {component_kind}")
