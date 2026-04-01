# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Schemas used by the logs service."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel

from api_common.schemas import PaginationMetadataResponse, TimeRangePaginationRequest

# Severity ordering for log levels (lower = less severe, higher = more severe)
_LOG_LEVEL_SEVERITY: dict[str, int] = {
    "trace": 0,  # Lowest level - most verbose
    "debug": 10,  # Debug information
    "info": 20,  # General information
    "unknown": 21,  # Loki unknown level, usually info
    "warning": 30,  # Warning messages
    "error": 40,  # Error messages
    "critical": 50,  # Critical/fatal errors - highest severity
}


class LogLevel(StrEnum):
    """Log levels for filtering.

    String-based enum for API clarity. Use severity() for ordering comparisons.
    """

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    UNKNOWN = "unknown"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @classmethod
    def from_label(cls, label: str | None) -> "LogLevel":
        """Convert a log level string to LogLevel enum.

        Case insensitive. Maps synonyms: 'warn' -> WARNING, 'fatal' -> CRITICAL.
        Returns UNKNOWN for None or unrecognized values.
        """
        if label is None:
            return cls.UNKNOWN

        label_lc = label.lower().strip()

        # Handle common synonyms
        if label_lc == "warn":
            return cls.WARNING
        if label_lc == "fatal":
            return cls.CRITICAL

        # Try direct value match
        for member in cls:
            if member.value == label_lc:
                return member

        return cls.UNKNOWN

    def to_loki_label(self) -> str:
        """Return the label value Loki uses for detected_level.

        Inverse of from_label: enum → Loki string. Loki uses "warn" and "fatal";
        our enum uses "warning" and "critical".
        """
        if self == LogLevel.WARNING:
            return "warn"
        if self == LogLevel.CRITICAL:
            return "fatal"
        return self.value

    def severity(self) -> int:
        """Get numeric severity for ordering comparisons."""
        return _LOG_LEVEL_SEVERITY.get(self.value, 21)

    @classmethod
    def levels_at_or_above(cls, min_level: "LogLevel") -> list["LogLevel"]:
        """Get all log levels at or above the given severity."""
        min_severity = min_level.severity()
        return [level for level in cls if level.severity() >= min_severity]


class LogType(StrEnum):
    """Type of logs to retrieve."""

    WORKLOAD = "workload"
    EVENT = "event"


class LogEntry(BaseModel):
    """A single log entry from Loki."""

    timestamp: AwareDatetime
    level: LogLevel
    message: str

    @classmethod
    def from_loki(cls, timestamp_ns: str, message: str, labels: dict | None = None) -> "LogEntry":
        """Parse a log entry from Loki format (nanosecond timestamp, labels dict)."""
        timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000, tz=UTC)
        level_str = labels.get("detected_level") or labels.get("level") if labels else None
        if not level_str:
            level_str = message.split(": ")[0]
        return cls(timestamp=timestamp, level=LogLevel.from_label(level_str), message=message)


class WorkloadLogsResponse(BaseModel):
    """Response containing log entries with pagination metadata."""

    data: list[LogEntry]
    pagination: PaginationMetadataResponse


class LogsQueryRequest(TimeRangePaginationRequest):
    """Query request for logs endpoints"""

    level: LogLevel | None = None
    log_type: LogType = LogType.WORKLOAD
