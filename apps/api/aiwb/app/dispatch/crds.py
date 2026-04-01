# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Generic Kubernetes API response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class K8sMetadata(BaseModel):
    name: str
    namespace: str | None = None
    uid: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    creation_timestamp: datetime | None = Field(None, alias="creationTimestamp")
    owner_references: list[dict[str, Any]] = Field(default_factory=list, alias="ownerReferences")

    class Config:
        populate_by_name = True


class K8sListResponse(BaseModel):
    api_version: str = Field(alias="apiVersion")
    kind: str
    items: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
