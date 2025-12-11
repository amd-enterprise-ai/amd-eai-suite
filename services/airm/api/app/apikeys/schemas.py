# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from ..utilities.schema import BaseEntityPublic


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key"""

    name: str = Field(description="User-friendly name for the API key")
    ttl: str = Field(default="0", description="Time to live (e.g., '1h', '24h', '30d', '0' for never)")
    renewable: bool = Field(default=True, description="Whether the key can be renewed")
    num_uses: int = Field(default=0, description="Number of uses allowed (0 = unlimited)")
    meta: dict = Field(default_factory=dict, description="Additional metadata for the key")
    explicit_max_ttl: str = Field(
        default="",
        description="Maximum TTL that cannot be changed later. Unlike normal keys, updates to system/mount max TTL have no effect at renewal time.",
    )
    period: str = Field(
        default="",
        description="If set, the key will be periodic with no maximum TTL (unless explicit_max_ttl is set) but every renewal will use this period. Requires root or sudo capability.",
    )
    aim_ids: list[UUID] = Field(default_factory=list, description="List of AIM IDs to bind this API key to")


class ApiKeyResponse(BaseEntityPublic):
    """Schema for API key response in list view (without ttl/expires_at/renewable/num_uses)"""

    name: str = Field(description="User-friendly name for the API key")
    truncated_key: str = Field(
        description="Truncated API key for display (e.g., 'amd_aim_api_key_••••••••1234')",
        examples=["amd_aim_api_key_••••••••a1b2"],
    )
    project_id: UUID = Field(description="The ID of the project this key belongs to")


class ApiKeyWithFullKey(ApiKeyResponse):
    """
    Schema for API key response that includes the full key.
    This is only returned once during creation.
    Includes ttl, expires_at, renewable, and num_uses from Cluster Auth.
    """

    ttl: str | None = Field(default=None, description="Time to live (fetched from Cluster Auth)")
    expires_at: AwareDatetime | None = Field(default=None, description="Expiration timestamp from Cluster Auth")
    renewable: bool = Field(description="Whether the key can be renewed (fetched from Cluster Auth)")
    num_uses: int = Field(description="Number of uses allowed - 0 = unlimited (fetched from Cluster Auth)")
    full_key: str = Field(
        description="The complete API key with prefix (only shown once during creation)",
        examples=["amd_aim_api_key_hvs.CAESIJlWWvb3r..."],
    )


class ApiKeyDetails(ApiKeyResponse):
    """
    Schema for detailed API key information including Cluster Auth metadata.
    Includes current ttl, expires_at, renewable, and num_uses from Cluster Auth.
    """

    ttl: str | None = Field(default=None, description="Time to live (fetched from Cluster Auth)")
    expires_at: AwareDatetime | None = Field(default=None, description="Expiration timestamp from Cluster Auth")
    renewable: bool = Field(description="Whether the key can be renewed (fetched from Cluster Auth)")
    num_uses: int = Field(description="Number of uses allowed - 0 = unlimited (fetched from Cluster Auth)")
    groups: list[str] = Field(default_factory=list, description="List of group IDs this key is bound to")
    entity_id: str | None = Field(default=None, description="Cluster Auth entity ID")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class ApiKeyUpdate(BaseModel):
    """Schema for updating an API key's AIM bindings"""

    aim_ids: list[UUID] = Field(description="List of AIM IDs to bind this API key to (replaces existing bindings)")


class BindGroupRequest(BaseModel):
    """Request to bind an API key to a group"""

    group_id: str = Field(description="The ID of the group to bind the API key to")


class UnbindGroupRequest(BaseModel):
    """Request to unbind an API key from a group"""

    group_id: str = Field(description="The ID of the group to unbind the API key from")


class RenewApiKeyResponse(BaseModel):
    """Response after renewing an API key"""

    lease_duration: int = Field(description="New lease duration in seconds")


class GroupCreate(BaseModel):
    """Request schema for creating a new group"""

    name: str = Field(description="Name of the group")
    id: str | None = Field(default=None, description="ID of the group (auto-generated if not provided)")


class GroupResponse(BaseModel):
    """Response schema for group operations"""

    id: str = Field(description="The unique identifier of the group")
    name: str = Field(description="The name of the group")


class ApiKeysResponse(BaseModel):
    """Wrapper for collection of API keys."""

    data: list[ApiKeyResponse] = Field(description="List of API keys")
