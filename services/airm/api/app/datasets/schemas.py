# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field

from ..utilities.config import DATASETS_PATH
from ..utilities.schema import BaseEntityPublic
from .models import DatasetType


class DatasetCreate(BaseModel):
    """
    Schema for registering an existing dataset at a given S3 path.
    The dataset name will be automatically derived from the path.

    The name derivation process:
    1. Extract the filename component from the path
    2. Remove common extensions (.jsonl, .json, .csv, .txt)
    3. Replace hyphens and underscores with spaces
    4. Capitalize each word for better readability

    Example:
    - Path: "project-x/datasets/customer-feedback-2023.jsonl"
    - Derived name: "Customer Feedback 2023"
    """

    description: str = Field(description="The description of the dataset", default="")
    path: str = Field(
        description="The path to the dataset in cloud storage. The dataset name will be derived from this path.",
        example=f"{DATASETS_PATH}/dataset.jsonl",
    )
    type: DatasetType = Field(description="The type of the dataset")


class DatasetEdit(BaseModel):
    """
    Base class for dataset edits with all fields optional.
    Note that name and path are immutable after creation and cannot be changed.
    """

    # name and path are immutable after creation
    description: str | None = Field(default=None, description="Updated description of the dataset")
    type: DatasetType | None = Field(default=None, description="Updated type of the dataset")

    # Allows submitting the Response to update only the available fields
    model_config = ConfigDict(extra="ignore")


class DatasetResponse(BaseEntityPublic):
    """Response model for dataset operations"""

    name: str = Field(description="The name of the dataset")
    description: str = Field(description="The description of the dataset")
    path: str = Field(description="The path to the dataset in cloud storage")
    type: DatasetType = Field(description="The type of the dataset")

    model_config = ConfigDict(from_attributes=True)


class DatasetsResponse(BaseModel):
    """Wrapper for collection of datasets."""

    data: list[DatasetResponse] = Field(description="List of datasets")
