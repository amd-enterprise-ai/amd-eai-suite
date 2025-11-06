# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field

from ..utilities.schema import BaseEntityPublic


class OrganizationCreate(BaseModel):
    name: str = Field(description="The ID of the organization.", max_length=64)
    domains: list[str] = Field(description="A list of domains.")


class OrganizationResponse(OrganizationCreate, BaseEntityPublic):
    idp_linked: bool = Field(description="Whether the organization has an identity provider linked")
    smtp_enabled: bool = Field(description="Whether the organization has an SMTP server enabled", default=False)

    model_config = ConfigDict(from_attributes=True)


class Organizations(BaseModel):
    organizations: list[OrganizationResponse]
