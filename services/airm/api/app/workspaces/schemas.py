# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class DevelopmentWorkspaceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image: str | None = Field(default=None, description="A custom container image to use for the workspace")
    image_pull_secrets: list[str] = Field(default=[], description="List of custom imagePullSecrets")
    gpus: int = Field(default=1, description="Number of GPUs to allocate to the workspace", ge=0, le=8)
    memory_per_gpu: float = Field(default=128, description="Memory per GPU in Gi", ge=0.01)
    cpu_per_gpu: float = Field(default=4, description="CPU per GPU in vCPUs", ge=1)
