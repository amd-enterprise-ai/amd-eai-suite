# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Cluster resource schemas for AIWB API."""

from pydantic import Field

from api_common.schemas import BaseModel


class AvailableResources(BaseModel):
    """Available cluster resources."""

    cpu_milli_cores: int = Field(
        ...,
        description="Available CPU in milli-cores (1 core = 1000 milli-cores)",
        examples=[64000],
    )
    memory_bytes: int = Field(
        ...,
        description="Available memory in bytes",
        examples=[549755813888],
    )
    ephemeral_storage_bytes: int = Field(
        ...,
        description="Available ephemeral storage in bytes",
        examples=[10995116277760],
    )
    gpu_count: int = Field(
        ...,
        description="Total number of GPUs available",
        examples=[8],
    )


class ClusterResourcesData(BaseModel):
    """Cluster resources data."""

    available_resources: AvailableResources = Field(
        ...,
        description="Available cluster resources",
    )
    total_node_count: int = Field(
        ...,
        description="Total number of nodes in the cluster",
        examples=[4],
    )


class ClusterResourcesResponse(BaseModel):
    """Response model for cluster resources endpoint."""

    data: ClusterResourcesData = Field(
        ...,
        description="Cluster resources data",
    )


class AimImageFamily(BaseModel):
    """A supported aim-engine container image family for runtime profile selection."""

    family_id: str = Field(
        ...,
        description="Stable catalog key for the image family (e.g. 'automatic', 'aim-base'), not a UUID.",
        examples=["automatic", "aim-base"],
    )
    display_name: str = Field(
        ...,
        description="Human-readable label for UI dropdowns.",
        examples=["Automatic", "aim-base"],
    )
    repository: str | None = Field(
        None,
        description="Container repository without tag. Null for the Automatic entry.",
        examples=["amdenterpriseai/aim-base"],
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Available image tags/versions for this family.",
        examples=[["0.11"], []],
    )


class ClusterAccelerator(BaseModel):
    """An accelerator product available on the cluster."""

    device_id: str = Field(
        ...,
        description="AMD GPU device type ID from node labels (e.g. MI300X hex id).",
        examples=["74a1"],
    )
    product_name: str = Field(
        ...,
        description="Display name from amd.com/gpu.product-name, or device_id when absent.",
        examples=["AMD Instinct MI300X"],
    )
    allocatable_count: int = Field(
        ...,
        ge=0,
        description="Total allocatable amd.com/gpu units across ready nodes for this device id.",
        examples=[8],
    )
