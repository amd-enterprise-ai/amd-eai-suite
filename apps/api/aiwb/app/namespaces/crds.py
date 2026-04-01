# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from .constants import NAMESPACE_ID_LABEL


class Namespace(BaseModel):
    """Kubernetes namespace with metadata."""

    name: str = Field(..., description="Kubernetes namespace name")
    labels: dict[str, str] = Field(default_factory=dict, description="Namespace labels")
    annotations: dict[str, str] = Field(default_factory=dict, description="Namespace annotations")
    created_at: datetime | None = Field(None, description="Namespace creation timestamp")

    model_config = {"from_attributes": True}

    @computed_field
    def id(self) -> str | None:
        return self.labels.get(NAMESPACE_ID_LABEL)
