# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class OrganizationResponse(BaseModel):
    idp_linked: bool = Field(description="Whether the organization has an identity provider linked")
    smtp_enabled: bool = Field(description="Whether the organization has an SMTP server enabled", default=False)

    model_config = ConfigDict(from_attributes=True)
