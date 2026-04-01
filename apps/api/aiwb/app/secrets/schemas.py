# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, Field, computed_field

from .constants import AIRM_USE_CASE_LABEL, USE_CASE_LABEL
from .crds import KubernetesSecretResource
from .enums import SecretUseCase


class SecretResponse(KubernetesSecretResource):
    """Schema for secret read from Kubernetes - extends CRD with computed use_case."""

    @computed_field
    def use_case(self) -> SecretUseCase | None:
        """Extract use_case from labels, checking both AIWB and AIRM label keys."""
        use_case_str = self.metadata.labels.get(USE_CASE_LABEL) or self.metadata.labels.get(AIRM_USE_CASE_LABEL)
        return SecretUseCase(use_case_str) if use_case_str else None


class SecretCreate(BaseModel):
    """Schema for creating a new Kubernetes Secret."""

    name: str = Field(
        description="The name of the secret",
        min_length=2,
        max_length=253,
        pattern="^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$",
    )
    data: dict[str, str] = Field(
        description="Secret data as key-value pairs; values must be valid for the Kubernetes Secret `data` field (for example, base64-encoded strings) and are passed through without modification"
    )
    use_case: SecretUseCase | None = Field(default=None, description="Optional use case classification for the secret")
