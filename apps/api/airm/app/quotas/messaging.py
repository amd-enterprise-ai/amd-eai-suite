# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from ..clusters.messaging import PriorityClass
from ..utilities.enums import GPUVendor


class ClusterQuotaAllocation(BaseModel):
    cpu_milli_cores: int = Field(description="The guaranteed number of CPU milli cores.")
    gpu_count: int = Field(description="The guaranteed number of GPUs.")
    memory_bytes: int = Field(description="The guaranteed memory in bytes.")
    ephemeral_storage_bytes: int = Field(description="The guaranteed ephemeral storage in bytes.")
    quota_name: str = Field(description="The quota name to uniquely identify the quota in the cluster.")
    namespaces: list[str] = Field(description="The list of namespaces to which the quota applies.")


class ClusterQuotasAllocationMessage(BaseModel):
    message_type: Literal["cluster_quotas_allocation"]
    gpu_vendor: GPUVendor | None = Field(None, description="The vendor of the GPU in the cluster")
    quota_allocations: list[ClusterQuotaAllocation] = Field(description="The list of quota allocations to apply.")
    priority_classes: list[PriorityClass] = Field(description="The list of priority classes to configure.")


class ClusterQuotasStatusMessage(BaseModel):
    message_type: Literal["cluster_quotas_status"]
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
    quota_allocations: list[ClusterQuotaAllocation] = Field(description="The list of quota allocations.")


class ClusterQuotasFailureMessage(BaseModel):
    message_type: Literal["cluster_quotas_failure"]
    reason: str | None = Field(None, description="The reason for the failure.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
