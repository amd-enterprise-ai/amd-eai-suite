# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import ast
from typing import Any

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, computed_field

from ..managed_workloads.schemas import AIMWorkloadResponse
from ..utilities.schema import BaseEntityPublic


class AIMBase(BaseEntityPublic):
    """Basic AIM information from AIMClusterModel."""

    image_reference: str = Field(..., description="Full image reference (e.g., registry/repo:tag)")
    labels: dict[str, Any] = Field(default_factory=dict, description="Image metadata labels from Kaiwo")
    status: str = Field(..., description="Status of the AIMClusterModel (e.g., Ready, Pending)")

    model_config = ConfigDict(from_attributes=True)


class AIMResponse(AIMBase):
    """Schema for AIM responses with optional workload deployment info."""

    workload: AIMWorkloadResponse | None = Field(
        None, description="The active workload deployment for this AIM (None if not deployed)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_name(self) -> str:
        """Extract image name from image_reference."""
        ref_without_tag = (
            self.image_reference.rsplit(":", 1)[0] if ":" in self.image_reference else self.image_reference
        )
        return ref_without_tag.rsplit("/", 1)[-1]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_tag(self) -> str:
        """Extract image tag from image_reference."""
        return self.image_reference.rsplit(":", 1)[-1] if ":" in self.image_reference else "latest"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def canonical_name(self) -> str | None:
        """Extract canonical name from labels, checking for any matching suffix."""
        for key, value in self.labels.items():
            if key.endswith(".canonicalName"):
                return value
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def recommended_deployments(self) -> list[dict[str, Any]]:
        for key, value in self.labels.items():
            if key.endswith(".model.recommendedDeployments"):
                try:
                    parsed = ast.literal_eval(value)
                    # Handle tuple (legacy format without brackets)
                    if isinstance(parsed, tuple):
                        return list(parsed)
                    # Ensure it's always a list
                    return parsed if isinstance(parsed, list) else [parsed]
                except (ValueError, SyntaxError) as e:
                    logger.warning(f"Failed to parse recommended deployments: {e}")
                    return []
        return []


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
    metric: str | None = Field(
        None,
        description="Performance optimization metric (latency or throughput).",
    )
    allow_unoptimized: bool = Field(
        False,
        description="Allow unoptimized deployment configurations if available in the cluster.",
    )


class AIMsResponse(BaseModel):
    """Wrapper for collection of AIMs."""

    data: list[AIMResponse] = Field(description="List of AIMs")
    metric: str | None = Field(
        None,
        description="Performance optimization metric (latency or throughput).",
    )
