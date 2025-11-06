# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, Field


class NamespaceBase(BaseModel):
    name: str = Field(description="The name of the namespace")
    cluster_id: UUID = Field(description="The ID of the cluster this namespace belongs to")
    project_id: UUID = Field(description="The ID of the project this namespace belongs to")


class NamespaceResponse(NamespaceBase):
    status: str | None = Field(description="The current status of the namespace")
    status_reason: str | None = Field(None, description="Reason for the current status")

    class Config:
        from_attributes = True


class ClusterNamespaces(BaseModel):
    cluster_id: UUID = Field(description="The ID of the cluster")
    namespaces: list[NamespaceResponse] = Field(description="List of namespaces in this cluster")


class ClustersWithNamespaces(BaseModel):
    clusters_namespaces: list[ClusterNamespaces] = Field(description="Namespaces grouped by cluster")
