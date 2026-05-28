# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from api_common.secrets import SecretUseCase

from ..utilities.messaging import KubernetesMetadata
from .constants import EXTERNAL_SECRETS_API_GROUP, KUBERNETES_SECRET_API_VERSION
from .enums import ProjectSecretStatus, SecretKind, SecretScope


class ExternalSecretManifest(BaseModel):
    """
    Pydantic model for ExternalSecret manifest.
    Validates basic structure; full validation performed by Kubernetes client in dispatcher.
    """

    model_config = ConfigDict(extra="allow")  # Allow additional fields

    apiVersion: str
    kind: Literal["ExternalSecret"]  # Literal required for discriminated union
    metadata: KubernetesMetadata
    spec: dict[str, Any]  # Spec is validated by Kubernetes, keep flexible

    @field_validator("apiVersion")
    @classmethod
    def validate_api_version(cls, v: str) -> str:
        if not v.startswith(f"{EXTERNAL_SECRETS_API_GROUP}/"):
            raise ValueError(f"apiVersion must start with '{EXTERNAL_SECRETS_API_GROUP}/', got '{v}'")
        return v


class KubernetesSecretManifest(BaseModel):
    """
    Pydantic model for Kubernetes Secret manifest.
    Validates basic structure; full validation performed by Kubernetes client in dispatcher.
    """

    model_config = ConfigDict(extra="allow")  # Allow additional fields

    apiVersion: str
    kind: Literal["Secret"]
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


class ProjectSecretsCreateMessage(BaseModel):
    message_type: Literal["project_secrets_create"]
    manifest: Annotated[KubernetesSecretManifest | ExternalSecretManifest, Field(discriminator="kind")] = Field(
        description="The secret manifest as a Pydantic model."
    )
    secret_type: SecretKind = Field(description="The Kubernetes resource kind to manage for this secret.")


class ProjectSecretsDeleteMessage(BaseModel):
    message_type: Literal["project_secrets_delete"]
    project_secret_id: UUID = Field(description="The ID of the secret.")
    project_name: str = Field(description="The name of the project.")
    secret_type: SecretKind = Field(description="The Kubernetes resource kind to manage for this secret.")
    secret_scope: SecretScope = Field(description="The scope of the secret.")


class ProjectSecretsUpdateMessage(BaseModel):
    message_type: Literal["project_secrets_update"]
    project_secret_id: UUID = Field(description="The ID of the secret.")
    secret_scope: SecretScope | None = Field(None, description="The scope of the secret.")
    status: ProjectSecretStatus = Field(description="The status of the secret.")
    status_reason: str | None = Field(None, description="The reason for the update.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class AutoDiscoveredSecretMessage(BaseModel):
    message_type: Literal["auto_discovered_secret"]
    project_id: UUID = Field(description="The project ID.")
    secret_id: UUID = Field(description="The secret ID assigned by the webhook.")
    name: str = Field(description="The name of the secret.")
    kind: SecretKind = Field(description="The kind of the secret (KubernetesSecret or ExternalSecret).")
    use_case: SecretUseCase = Field(SecretUseCase.GENERIC, description="The use case of the secret.")
    submitter: str | None = Field(None, description="The user who created the secret, if known.", max_length=256)
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
