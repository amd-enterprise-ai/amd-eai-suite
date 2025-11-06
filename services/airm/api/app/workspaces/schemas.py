# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, Field


class DevelopmentWorkspaceRequest(BaseModel):
    image: str = Field(
        default="rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0",
        description="Container image to use for the workspace",
    )
    imagePullSecrets: list | None = Field(default_factory=list, description="List of custom imagePullSecrets")
    gpus: int = Field(default=1, description="Number of GPUs to allocate to the workspace", ge=0, le=8)
    memory_per_gpu: float = Field(default=128, description="Memory per GPU in Gi", ge=0.01)
    cpu_per_gpu: float = Field(default=4, description="CPU per GPU in vCPUs", ge=1)
