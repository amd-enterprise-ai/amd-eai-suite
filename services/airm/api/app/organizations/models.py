# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..utilities.models import BaseEntity


class Organization(BaseEntity):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String, nullable=False)
    keycloak_organization_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    keycloak_group_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    __table_args__ = (Index("organizations_name_key", func.lower(name), unique=True),)
