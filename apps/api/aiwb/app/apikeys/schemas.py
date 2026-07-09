# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pydantic import AwareDatetime, Field

from api_common.collections import BasePaginationList, PaginationConditions
from api_common.schemas import BaseEntityPublic, BaseModel


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key"""

    display_name: str = Field(
        description="User-friendly name for the API key",
        examples=["llama-3-prod-key"],
    )
    ttl: str = Field(
        default="0",
        description="Time to live (e.g., '1h', '24h', '30d', '0' for never)",
        examples=["24h", "30d", "0"],
    )
    renewable: bool = Field(default=True, description="Whether the key can be renewed", examples=[True])
    num_uses: int = Field(
        default=0,
        description="Number of uses allowed (0 = unlimited)",
        examples=[0, 100],
    )
    meta: dict = Field(
        default_factory=dict,
        description="Additional metadata for the key",
        examples=[{"team": "ml-platform", "env": "prod"}],
    )
    explicit_max_ttl: str = Field(
        default="",
        description="Maximum TTL that cannot be changed later. Unlike normal keys, updates to system/mount max TTL have no effect at renewal time.",
        examples=["", "90d"],
    )
    period: str = Field(
        default="",
        description="If set, the key will be periodic with no maximum TTL (unless explicit_max_ttl is set) but every renewal will use this period. Requires root or sudo capability.",
        examples=["", "24h"],
    )
    aim_ids: list[str] = Field(
        default_factory=list,
        description="List of AIM IDs to bind this API key to (use AIM service IDs from workloads)",
        examples=[["7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"]],
    )


class ApiKeyResponse(BaseEntityPublic):
    """Schema for API key response in list view (without ttl/expires_at/renewable/num_uses)"""

    display_name: str = Field(
        description="User-friendly name for the API key",
        examples=["llama-3-prod-key"],
    )
    truncated_key: str = Field(
        description="Truncated API key for display (e.g., 'amd_aim_api_key_••••••••1234')",
        examples=["amd_aim_api_key_••••••••a1b2"],
    )
    namespace: str = Field(
        description="The namespace this key belongs to",
        examples=["acme-summarizer"],
    )


class ApiKeysList(BasePaginationList):
    """Paginated list of API keys."""

    data: list[ApiKeyResponse]


class ListApiKeysQuery(PaginationConditions):
    """Query parameters for listing API keys."""

    page: int = Field(default=1, ge=1)
    # Bound page_size so a single client cannot fetch arbitrarily large pages.
    page_size: int = Field(default=10, ge=1, le=100)


class ApiKeyWithFullKey(ApiKeyResponse):
    """
    Schema for API key response that includes the full key.
    This is only returned once during creation.
    Includes ttl, expires_at, renewable, and num_uses from Cluster Auth.
    """

    ttl: str | None = Field(
        default=None,
        description="Time to live (fetched from Cluster Auth)",
        examples=["86400"],
    )
    expires_at: AwareDatetime | None = Field(
        default=None,
        description="Expiration timestamp from Cluster Auth",
        examples=["2026-06-28T12:00:00Z"],
    )
    renewable: bool = Field(
        description="Whether the key can be renewed (fetched from Cluster Auth)",
        examples=[True],
    )
    num_uses: int = Field(
        description="Number of uses allowed - 0 = unlimited (fetched from Cluster Auth)",
        examples=[0],
    )
    full_key: str = Field(
        description="The complete API key with prefix (only shown once during creation)",
        examples=["amd_aim_api_key_hvs.CAESIJlWWvb3r..."],
    )


class ApiKeyDetails(ApiKeyResponse):
    """
    Schema for detailed API key information including Cluster Auth metadata.
    Includes current ttl, expires_at, renewable, and num_uses from Cluster Auth.
    """

    ttl: str | None = Field(
        default=None,
        description="Time to live (fetched from Cluster Auth)",
        examples=["86400"],
    )
    expires_at: AwareDatetime | None = Field(
        default=None,
        description="Expiration timestamp from Cluster Auth",
        examples=["2026-06-28T12:00:00Z"],
    )
    renewable: bool = Field(
        description="Whether the key can be renewed (fetched from Cluster Auth)",
        examples=[True],
    )
    num_uses: int = Field(
        description="Number of uses allowed - 0 = unlimited (fetched from Cluster Auth)",
        examples=[0],
    )
    groups: list[str] = Field(
        default_factory=list,
        description="List of group IDs this key is bound to",
        examples=[["aim-7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"]],
    )
    entity_id: str | None = Field(
        default=None,
        description="Cluster Auth entity ID",
        examples=["b4f3a2c1-9d8e-7f6a-5b4c-3d2e1f0a9b8c"],
    )
    meta: dict = Field(
        default_factory=dict,
        description="Additional metadata",
        examples=[{"team": "ml-platform", "env": "prod"}],
    )


class ApiKeyUpdate(BaseModel):
    """Schema for updating an API key's AIM bindings"""

    aim_ids: list[str] = Field(
        description="List of AIM IDs to bind this API key to (replaces existing bindings)",
        examples=[["7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f", "9a8b7c6d-5e4f-3a2b-1c0d-987654321abc"]],
    )


class AddGroupMembershipRequest(BaseModel):
    """Request to add an API key to a cluster-auth group"""

    group_id: str = Field(
        description="The ID of the cluster-auth group to add this API key to",
        examples=["aim-7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"],
    )


class RenewApiKeyResponse(BaseModel):
    """Response after renewing an API key"""

    lease_duration: int = Field(
        description="New lease duration in seconds",
        examples=[86400],
    )


class GroupCreate(BaseModel):
    """Request schema for creating a new group"""

    name: str = Field(
        description="Name of the group",
        examples=["llama-3-readers"],
    )
    id: str | None = Field(
        default=None,
        description="ID of an existing group to update. Leave empty to create a new group with auto-generated ID.",
        examples=["aim-7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"],
    )


class GroupResponse(BaseModel):
    """Response schema for group operations"""

    id: str = Field(
        description="The unique identifier of the group",
        examples=["aim-7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"],
    )
    name: str = Field(
        description="The name of the group",
        examples=["llama-3-readers"],
    )


# ── API key metrics ──────────────────────────────────────────────────────────

# Each datapoint is a time bucket with per-service values keyed by aim_service_id.
# Wide format: { date: ISO string, <aim_service_id>: float, ... }
# This mirrors the frontend ApiKeyMetricsDataPoint type.
ApiKeyMetricsDataPoint = dict[str, float | str]


class ApiKeyMetricsStats(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    linked_deployments: int


class ApiKeyRequestsTimeseries(BaseModel):
    total: list[ApiKeyMetricsDataPoint]
    successful: list[ApiKeyMetricsDataPoint]
    failed: list[ApiKeyMetricsDataPoint]


class ApiKeyTokensTimeseries(BaseModel):
    total: list[ApiKeyMetricsDataPoint]
    input: list[ApiKeyMetricsDataPoint]
    output: list[ApiKeyMetricsDataPoint]


class ApiKeyMetricsResponse(BaseModel):
    stats: ApiKeyMetricsStats
    services: list[str]
    requests_over_time: ApiKeyRequestsTimeseries
    tokens_over_time: ApiKeyTokensTimeseries
