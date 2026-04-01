# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import ConfigDict, Field

from api_common.schemas import BaseEntityPublic

from .models import DatasetType


class DatasetResponse(BaseEntityPublic):
    """Response model for dataset operations"""

    name: str = Field(description="The name of the dataset")
    description: str = Field(description="The description of the dataset")
    path: str = Field(description="The path to the dataset in cloud storage")
    type: DatasetType = Field(description="The type of the dataset")

    model_config = ConfigDict(from_attributes=True)
