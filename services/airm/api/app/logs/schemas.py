# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Schemas used by the logs service."""

import json
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, field_validator, model_serializer


class LogLevel(IntEnum):
    """Log levels with proper ordering for filtering.

    Values are based on Python logging levels for consistent ordering.
    Lower numeric values = lower severity, higher values = higher severity.
    """

    trace = 0  # Lowest level - most verbose
    debug = 10  # Debug information
    info = 20  # General information
    unknown = 21  # Loki unknown level, usually info
    warning = 30  # Warning messages
    error = 40  # Error messages
    critical = 50  # Critical/fatal errors - highest severity

    @classmethod
    def from_label(cls, label: str | None) -> "LogLevel":
        """Convert a log level string from Loki/Promtail or API to LogLevel enum.

        Handles string labels that come from Loki and API inputs:
        - Standard names: 'debug', 'info', 'warn', 'error', 'critical', 'trace'
        - Common synonyms: 'warning' -> 'warn', 'fatal' -> 'critical'
        - Case insensitive
        """
        if label is None:
            return cls.unknown  # Default to unknown for unknown/null levels

        label_lc = label.lower().strip()

        # Handle common synonyms first
        if label_lc == "warn":
            return cls.warning
        if label_lc == "fatal":
            return cls.critical

        # Try direct name match with enum members
        if label_lc in cls.__members__:
            return cls.__members__[label_lc]

        # Default fallback for unrecognized levels
        return cls.unknown

    def __str__(self) -> str:
        """Return the string name of the log level."""
        if self == LogLevel.warning:
            return "warn"
        if self == LogLevel.critical:
            return "fatal"
        return self.name


# API-friendly literal type for endpoint parameters
LogLevelLiteral = Literal["trace", "debug", "info", "warning", "error", "critical", "unknown"]

LogDirectionLiteral = Literal["forward", "backward"]

LogTypeLiteral = Literal["workload", "event"]


class LogEntry(BaseModel):
    """A single log entry from Loki.

    The level field accepts various input formats but always stores as LogLevel enum.
    When serialized (e.g., in API responses), level is returned as a string.
    """

    timestamp: str  # ISO 8601 string
    level: LogLevel
    message: str

    @field_validator("level", mode="before")
    @classmethod
    def _convert_level(cls, v):
        """Convert various level input formats to LogLevel enum."""
        if isinstance(v, LogLevel):
            return v
        return LogLevel.from_label(v)

    @model_serializer(mode="wrap")
    def _serialize_model(self, serializer, info):
        """Serialize level as string name in API responses."""
        data = serializer(self)
        if isinstance(data, dict) and "level" in data:
            data["level"] = self.level.name
        return data

    def __str__(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "level": self.level.name,
                "message": self.message,
            }
        )


class PaginationMetadata(BaseModel):
    """Pagination metadata for log responses."""

    has_more: bool
    page_token: str | None = None
    total_returned: int


class WorkloadLogsResponse(BaseModel):
    """Response containing log entries with pagination metadata."""

    logs: list[LogEntry]
    pagination: PaginationMetadata
