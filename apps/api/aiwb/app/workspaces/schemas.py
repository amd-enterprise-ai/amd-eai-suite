# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import Field

from api_common.schemas import BaseModel

from .enums import WorkspaceType


class DevelopmentWorkspaceRequest(BaseModel):
    """Request schema for creating a development workspace."""

    workspace_type: WorkspaceType = Field(description="Type of workspace to create")
    image: str | None = Field(
        default=None,
        description="A custom container image to use for the workspace",
        examples=["jupyter/datascience-notebook:latest"],
    )
    image_pull_secrets: list[str] = Field(
        default_factory=list,
        description="List of image pull secrets",
        examples=[["registry-credentials"]],
    )
    gpus: int = Field(
        default=1,
        description="Number of GPUs to allocate to the workspace",
        ge=0,
        le=8,
        examples=[1],
    )
    memory_per_gpu: float = Field(
        default=128,
        description="Memory per GPU in Gi",
        ge=0.01,
        examples=[128.0],
    )
    cpu_per_gpu: float = Field(
        default=4,
        description="CPU per GPU in vCPUs",
        ge=1,
        examples=[4.0],
    )
