# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Cluster resource schemas for AIWB API."""

from pydantic import BaseModel, Field


class AvailableResources(BaseModel):
    """Available cluster resources."""

    cpu_milli_cores: int = Field(
        ...,
        description="Available CPU in milli-cores (1 core = 1000 milli-cores)",
    )
    memory_bytes: int = Field(
        ...,
        description="Available memory in bytes",
    )
    ephemeral_storage_bytes: int = Field(
        ...,
        description="Available ephemeral storage in bytes",
    )
    gpu_count: int = Field(
        ...,
        description="Total number of GPUs available",
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
    )


class ClusterResourcesResponse(BaseModel):
    """Response model for cluster resources endpoint."""

    data: ClusterResourcesData = Field(
        ...,
        description="Cluster resources data",
    )
