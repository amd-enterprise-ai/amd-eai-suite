# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from ..clusters.schemas import ClusterResponse, ClusterWithResources
from ..quotas.schemas import (
    QuotaResponse,  # noqa: E402
    QuotaUpdate,  # noqa: E402
)
from ..utilities.schema import BaseEntityPublic
from .constants import MAX_PROJECT_NAME_LENGTH, RESTRICTED_PROJECT_NAMES
from .enums import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(
        description="The name of the project.",
        min_length=2,
        max_length=MAX_PROJECT_NAME_LENGTH,
        pattern="^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
    )
    description: str = Field(description="The description of the project.", min_length=2, max_length=1024)
    cluster_id: UUID = Field(description="The cluster ID the project belongs to")

    @field_validator("name")
    @classmethod
    def disallow_restricted_project_name(cls, v):
        if v in RESTRICTED_PROJECT_NAMES:
            raise ValueError(f"{v} is a restricted project name.")
        return v

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(ProjectBase, BaseEntityPublic):
    status: ProjectStatus = Field(description="The status of the project.")
    status_reason: str | None = Field(None, description="The reason for the project's status.")

    model_config = ConfigDict(from_attributes=True)


class ProjectEdit(BaseModel):
    description: str = Field(description="The description of the project.", min_length=2, max_length=1024)
    quota: QuotaUpdate = Field(description="The quota for the project.")

    model_config = ConfigDict(extra="forbid")


class ProjectCreate(ProjectBase):
    quota: QuotaUpdate = Field(description="The quota for the project.")

    model_config = ConfigDict(from_attributes=True)


class ProjectWithClusterAndQuota(ProjectResponse):
    quota: QuotaResponse = Field(description="The quota assigned to the project.")
    cluster: ClusterResponse = Field(description="The cluster the project belongs to.")

    model_config = ConfigDict(from_attributes=True)


class ProjectWithResourceAllocation(ProjectResponse):
    quota: QuotaResponse = Field(description="The quota assigned to the project.")
    cluster: ClusterWithResources = Field(description="The cluster the project belongs to with resource information.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gpu_allocation_percentage(self) -> float:
        """GPU allocation percentage."""
        allocated = self.quota.gpu_count
        available = self.cluster.available_resources.gpu_count
        return (allocated / available * 100) if available > 0 else 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gpu_allocation_exceeded(self) -> bool:
        """True if GPU allocation exceeds available resources."""
        return self.quota.gpu_count > self.cluster.available_resources.gpu_count

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cpu_allocation_percentage(self) -> float:
        """CPU allocation percentage."""
        allocated = self.quota.cpu_milli_cores
        available = self.cluster.available_resources.cpu_milli_cores
        return (allocated / available * 100) if available > 0 else 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cpu_allocation_exceeded(self) -> bool:
        """True if CPU allocation exceeds available resources."""
        return self.quota.cpu_milli_cores > self.cluster.available_resources.cpu_milli_cores

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memory_allocation_percentage(self) -> float:
        """Memory allocation percentage."""
        allocated = self.quota.memory_bytes
        available = self.cluster.available_resources.memory_bytes
        return (allocated / available * 100) if available > 0 else 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memory_allocation_exceeded(self) -> bool:
        """True if memory allocation exceeds available resources."""
        return self.quota.memory_bytes > self.cluster.available_resources.memory_bytes

    model_config = ConfigDict(from_attributes=True)


from ..users.schemas import InvitedUser, UserResponse  # noqa: E402


class ProjectWithUsers(ProjectWithClusterAndQuota):
    users: list["UserResponse"] = Field(description="The users in the project.")
    invited_users: list["InvitedUser"] = Field(description="The invited users to the project.")


class ProjectsWithResourceAllocation(BaseModel):
    projects: list[ProjectWithResourceAllocation] = Field(
        description="The projects present in the organization with resource allocation information."
    )


class Projects(BaseModel):
    projects: list[ProjectWithClusterAndQuota] = Field(description="The projects present in the organization.")


class ProjectAddUsers(BaseModel):
    user_ids: list[UUID] = Field(description="The IDs of the users to be added to the project.", max_length=100)


ProjectWithUsers.update_forward_refs()


class ProjectAssignments(BaseModel):
    project_ids: list[UUID] = Field(description="List of project IDs to assigned the storage to.", max_length=100)


# Circular dependencies:
# https://github.com/pydantic/pydantic/issues/1873
# https://github.com/fastapi/fastapi/issues/153
