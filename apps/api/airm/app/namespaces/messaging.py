# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..projects.schemas import GpuPreemptionConfig
from ..utilities.messaging import KubernetesMetadata
from .enums import NamespaceStatus


class NamespaceManifest(BaseModel):
    """
    Pydantic model for Kubernetes Namespace manifest.
    Used in project_namespace_create and project_namespace_update messages.
    Validates basic structure; full validation performed by Kubernetes client in agent.
    """

    model_config = ConfigDict(extra="allow")

    apiVersion: str = "v1"
    kind: Literal["Namespace"] = "Namespace"
    metadata: KubernetesMetadata


class ProjectNamespaceCreateMessage(BaseModel):
    message_type: Literal["project_namespace_create"]
    namespace_manifest: NamespaceManifest = Field(description="The namespace manifest to create.")


class ProjectNamespaceDeleteMessage(BaseModel):
    message_type: Literal["project_namespace_delete"]
    name: str = Field(description="The name of the namespace to delete.")
    project_id: UUID = Field(description="The ID of the project associated with the namespace.")


class ProjectNamespaceUpdateMessage(BaseModel):
    message_type: Literal["project_namespace_update"]
    namespace_manifest: NamespaceManifest = Field(description="The updated namespace manifest.")


class ProjectNamespaceStatusMessage(BaseModel):
    message_type: Literal["project_namespace_status"]
    project_id: UUID = Field(description="The ID of the project.")
    status: NamespaceStatus = Field(description="The status of the namespace.")
    status_reason: str | None = Field(None, description="The reason for the status.")
    gpu_preemption: GpuPreemptionConfig | None = Field(
        None,
        description=(
            "Observed GPU preemption config read from namespace annotations. "
            "Absent when sent by older agents — DB state is preserved in that case."
        ),
    )


class UnmanagedNamespaceMessage(BaseModel):
    message_type: Literal["unmanaged_namespace"]
    namespace_name: str = Field(description="The name of the unmanaged namespace detected in the cluster.")
    namespace_status: NamespaceStatus = Field(description="The status of the namespace.")


class NamespaceDeletedMessage(BaseModel):
    message_type: Literal["namespace_deleted"]
    namespace_name: str = Field(description="The name of the namespace that was deleted from the cluster.")
