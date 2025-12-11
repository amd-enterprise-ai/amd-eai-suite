# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..utilities.schema import BaseEntityPublic


class OverlayResponse(BaseEntityPublic):
    canonical_name: str | None = Field(
        description="Optional canonical name for a model which this overlay is compatible with. Used to identify overlays for models of the same origin.",
        examples=["meta-llama/Llama-3.1-8B"],
    )
    chart_id: UUID
    overlay: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class OverlayUpdate(BaseModel):
    """Request schema for updating an overlay."""

    chart_id: UUID | None = Field(
        None,
        description="The ID of the chart this overlay is associated with.",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    overlay: dict[str, Any] | None = Field(
        None,
        description="The overlay data in YAML format.",
        examples=[{"key": "value", "another_key": "another_value"}],
    )
    canonical_name: str | None = Field(
        None,
        description="Optional canonical name to associate the overlay with a model type, for example 'meta-llama/Llama-3.1-8B'.",
        examples=["meta-llama/Llama-3.1-8B"],
    )
    updated_by: str = Field(description="Email of the user who updated the overlay.")


class OverlaysResponse(BaseModel):
    """Wrapper for collection of overlays."""

    data: list[OverlayResponse] = Field(description="List of overlays")
