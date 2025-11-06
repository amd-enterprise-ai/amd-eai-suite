# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field

from ..managed_workloads.schemas import AIMWorkloadResponse
from ..utilities.schema import BaseEntityPublic


class AIMBase(BaseEntityPublic):
    """Basic AIM information to avoid circular dependency."""

    image_name: str = Field(..., description="The AIM image name")
    image_tag: str = Field(..., description="The AIM image tag")
    labels: dict[str, str] = Field(default_factory=dict, description="AIM labels")

    model_config = ConfigDict(from_attributes=True)


class AIMResponse(AIMBase):
    """Schema for AIM responses with optional workload deployment info."""

    workload: AIMWorkloadResponse | None = Field(
        None, description="The active workload deployment for this AIM (None if not deployed)"
    )


class AIMDeployRequest(BaseModel):
    """Schema for deploying an AIM."""

    cache_model: bool = Field(
        True,
        description="Request that model sources be cached when starting the service.",
    )
    replicas: int = Field(
        1,
        ge=1,
        le=8,
        description="Number of replicas for this service.",
    )
    image_pull_secrets: list[str] | None = Field(
        None, description="Names of the secrets for pulling AIM container images."
    )
    hf_token: str | None = Field(
        None,
        description="Hugging Face token for accessing private models (if required).",
    )
