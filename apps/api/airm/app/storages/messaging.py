# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from ..utilities.messaging import KubernetesMetadata
from ..workloads.enums import ConfigMapStatus


class StorageInfoConfigMapManifest(BaseModel):
    """
    Pydantic model for Kubernetes ConfigMap manifest (storage info).
    Used in project_s3_storage_create messages.
    """

    model_config = ConfigDict(extra="allow")

    apiVersion: str = "v1"
    kind: Literal["ConfigMap"] = "ConfigMap"
    metadata: KubernetesMetadata
    data: dict[str, str]


class ProjectS3StorageCreateMessage(BaseModel):
    message_type: Literal["project_s3_storage_create"]
    project_storage_id: UUID = Field(description="The ID of the storage.")
    project_name: str = Field(description="The name of the project.")
    manifest: str = Field(description="The ConfigMap manifest as YAML.")


class ProjectStorageDeleteMessage(BaseModel):
    message_type: Literal["project_storage_delete"]
    project_storage_id: UUID = Field(description="The ID of the storage.")
    project_name: str = Field(description="The name of the project.")


class ProjectStorageUpdateMessage(BaseModel):
    message_type: Literal["project_storage_update"]
    project_storage_id: UUID = Field(description="The ID of the storage.")
    status: ConfigMapStatus = Field(description="The status of the storage.")
    status_reason: str | None = Field(None, description="The reason for the update.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
