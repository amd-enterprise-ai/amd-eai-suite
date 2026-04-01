# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from ..projects.schemas import ProjectAssignment
from ..utilities.schema import BaseEntityPublic
from .enums import StorageScope, StorageStatus, StorageType


class S3Spec(BaseModel):
    bucket_url: HttpUrl = Field(description="URL to the S3 or S3-compatible bucket.")
    access_key_name: str = Field(description="The Name of the secret key used for access key name.")
    secret_key_name: str = Field(description="The Name of the secret key that stores the secret access name.")


class BaseStorage(BaseModel):
    name: str = Field(
        description="The name of the storage.",
        min_length=2,
        max_length=253,
        pattern="^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$",
    )
    type: StorageType = Field(description="The type of the secret")
    scope: StorageScope = Field(description="The scope of the secret")
    secret_id: UUID = Field(description="The ID of the secret that holds the credentials for this storage.")

    model_config = ConfigDict(from_attributes=True)


class StorageResponse(BaseStorage, BaseEntityPublic):
    status: StorageStatus = Field(description="The status of the storage")
    status_reason: str | None = Field(None, description="Details if any about the status")

    model_config = ConfigDict(from_attributes=True)


class StorageWithProjects(StorageResponse):
    project_storages: list[ProjectAssignment] = Field(description="The projects assigned to the storage")


class Storages(BaseModel):
    data: list[StorageWithProjects] = Field(description="The list of storages.")


class StorageIn(BaseStorage):
    project_ids: list[UUID] = Field(description="List of project IDs to assign the storage")
    spec: S3Spec = Field(description="The storage specification.")


class ProjectStorageWithParentStorage(ProjectAssignment):
    storage: StorageResponse = Field(description="The parent secret associated with the project storage.")


class ProjectStoragesWithParentStorage(BaseModel):
    data: list[ProjectStorageWithParentStorage] = Field(description="The storages in a given project.")
