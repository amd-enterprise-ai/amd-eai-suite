# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from ..utilities.enums import Roles
from ..utilities.schema import BaseEntityPublic


class UserBase(BaseEntityPublic):
    email: str = Field(
        description="The user's email/user name", pattern=r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    )
    role: str = Field(description="The highest role the user has in the organization")


class UserResponse(UserBase):
    first_name: str = Field(description="The user's first name", min_length=2, max_length=64)
    last_name: str = Field(description="The user's last name", min_length=2, max_length=64)
    last_active_at: AwareDatetime | None = Field(description="The timestamp the user was last active", default=None)


class InvitedUser(UserBase):
    invited_at: AwareDatetime = Field(description="The timestamp the user was invited")
    invited_by: str = Field(description="The user who invited this user")


class UserWithProjects(UserResponse):
    projects: list["ProjectResponse"] = Field(description="Projects the user belongs to", default_factory=list)


class InvitedUserWithProjects(InvitedUser):
    projects: list["ProjectResponse"] = Field(description="Projects the invited user belongs to", default_factory=list)


class Users(BaseModel):
    users: list[UserResponse]


class InvitedUsers(BaseModel):
    invited_users: list[InvitedUserWithProjects]


class UserRoleEnum(StrEnum):
    PLATFORM_ADMIN = Roles.PLATFORM_ADMINISTRATOR.value


class UserRolesUpdate(BaseModel):
    roles: list[UserRoleEnum] = Field(description="The roles to be assigned to the user", max_length=64)


class InviteUser(BaseModel):
    email: str = Field(
        description="The user's email/user name", pattern=r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    )
    roles: list[UserRoleEnum] = Field(description="The roles to be assigned to the user", min_items=0)
    project_ids: list[UUID] | None = Field(
        default=None, description="The IDs of the project to be assigned to the user."
    )


class UserDetailsUpdate(BaseModel):
    first_name: str = Field(description="The user's first name", min_length=2, max_length=64)
    last_name: str = Field(description="The user's last name", min_length=2, max_length=64)


from ..projects.schemas import ProjectResponse  # noqa: E402

# Circular dependencies:
# https://github.com/pydantic/pydantic/issues/1873
# https://github.com/fastapi/fastapi/issues/153


UserWithProjects.update_forward_refs()
InvitedUserWithProjects.update_forward_refs()
