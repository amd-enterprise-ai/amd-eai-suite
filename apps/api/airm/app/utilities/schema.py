# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import AwareDatetime, BaseModel


class BaseEntityPublic(BaseModel):
    """Exposes fields from BaseEntity"""

    id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    created_by: str | None
    updated_by: str | None


class DeleteOverlaysBatchRequest(BaseModel):
    """Request to delete multiple entities by ID."""

    ids: list[UUID]
