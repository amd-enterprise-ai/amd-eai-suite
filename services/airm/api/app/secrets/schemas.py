# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from airm.messaging.schemas import ProjectSecretStatus, SecretKind, SecretScope

from ..utilities.schema import BaseEntityPublic
from .enums import SecretStatus, SecretUseCase


class BaseSecret(BaseModel):
    name: str = Field(
        description="The name of the secret.",
        min_length=2,
        max_length=253,
        # Validates Kubernetes DNS subdomain names. See: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names
        pattern="^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$",
    )
    type: SecretKind = Field(description="The type of the secret")
    scope: SecretScope = Field(description="The scope of the secret")

    model_config = ConfigDict(from_attributes=True)


class ProjectSecret(BaseEntityPublic):
    project_id: UUID = Field(description="The ID of the project")
    project_name: str = Field(description="The name of the project")
    status: ProjectSecretStatus = Field(description="The status of the project secret.")
    status_reason: str | None = Field(None, description="Details if any about the status")

    model_config = ConfigDict(from_attributes=True)


class SecretResponse(BaseSecret, BaseEntityPublic):
    status: SecretStatus = Field(description="The status of the secret")
    status_reason: str | None = Field(None, description="Details if any about the status")
    use_case: SecretUseCase | None = Field(default=None, description="The use case this secret is associated with.")


class SecretWithProjects(SecretResponse):
    project_secrets: list[ProjectSecret] = Field(description="The projects assigned to the secret")


class Secrets(BaseModel):
    secrets: list[SecretWithProjects] = Field(description="The secrets in the organization.")


class SecretIn(BaseSecret):
    project_ids: list[UUID] = Field(description="List of project IDs to assign the secret")
    manifest: str = Field(..., description="The YAML contents of the Kubernetes manifest.", min_length=2)
    use_case: SecretUseCase | None = Field(default=None, description="Optional use case classification for the secret.")


class ProjectSecretWithParentSecret(ProjectSecret):
    secret: SecretResponse = Field(description="The parent secret associated with the project secret.")


class ProjectSecretsWithParentSecret(BaseModel):
    project_secrets: list[ProjectSecretWithParentSecret] = Field(description="The secrets in a given project.")


class BaseSecretIn(BaseSecret):
    manifest: str = Field(description="The YAML contents of the Kubernetes manifest.", min_length=2)
    use_case: SecretUseCase | None = Field(default=None, description="Optional use case classification for the secret.")


class OrganizationSecretIn(BaseSecretIn):
    project_ids: list[UUID] = Field(description="List of project IDs to assign the secret")

    @field_validator("type")
    @classmethod
    def validate_type_for_organization_secrets(cls, v):
        if v == SecretKind.KUBERNETES_SECRET:
            raise ValueError("Kubernetes secrets are not allowed for organization-scoped secrets")
        return v


class ProjectSecretIn(BaseSecretIn):
    @field_validator("use_case")
    @classmethod
    def validate_use_case_for_project_secrets(cls, v):
        if v == SecretUseCase.S3:
            raise ValueError("S3 use case is not allowed for project-scoped secrets")
        return v
