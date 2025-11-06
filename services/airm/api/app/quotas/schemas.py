# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from airm.messaging.schemas import QuotaStatus

from ..utilities.schema import BaseEntityPublic


class QuotaBase(BaseModel):
    cpu_milli_cores: int = Field(description="The number of CPU milli-cores assigned in the quota.")
    memory_bytes: int = Field(description="The amount of memory assigned in the quota.")
    ephemeral_storage_bytes: int = Field(description="The amount of ephemeral storage assigned in the quota.")
    gpu_count: int = Field(description="The number of GPUs assigned in the quota.")

    model_config = ConfigDict(from_attributes=True)


class QuotaCreate(QuotaBase):
    cluster_id: UUID = Field(description="The ID of the cluster.")
    project_id: UUID = Field(description="The ID of the project.")

    model_config = ConfigDict(from_attributes=True)


class QuotaUpdate(QuotaBase):
    pass

    model_config = ConfigDict(extra="forbid")


class QuotaResponse(QuotaBase, BaseEntityPublic):
    status: QuotaStatus = Field(description="The status of the quota.")
    status_reason: str | None = Field(None, description="The reason for the status of the quota, if any.")

    model_config = ConfigDict(from_attributes=True)
