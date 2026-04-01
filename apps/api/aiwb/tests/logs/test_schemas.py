# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for logs schemas."""

from datetime import UTC, datetime

from app.logs.schemas import LogEntry, LogLevel


def test_log_level_from_label():
    """Test LogLevel.from_label() conversion from raw strings."""
    assert LogLevel.from_label("info") is LogLevel.INFO
    assert LogLevel.from_label("debug") is LogLevel.DEBUG
    assert LogLevel.from_label("warn") is LogLevel.WARNING
    assert LogLevel.from_label("error") is LogLevel.ERROR
    assert LogLevel.from_label("critical") is LogLevel.CRITICAL
    assert LogLevel.from_label("trace") is LogLevel.TRACE

    assert LogLevel.from_label("WARNING") is LogLevel.WARNING
    assert LogLevel.from_label("ERROR") is LogLevel.ERROR

    assert LogLevel.from_label("warning") is LogLevel.WARNING
    assert LogLevel.from_label("fatal") is LogLevel.CRITICAL

    assert LogLevel.from_label("nonsense") is LogLevel.UNKNOWN
    assert LogLevel.from_label(None) is LogLevel.UNKNOWN
    assert LogLevel.from_label("") is LogLevel.UNKNOWN


def test_log_level_severity():
    """Test LogLevel.severity() returns correct ordering values."""
    assert LogLevel.TRACE.severity() == 0
    assert LogLevel.DEBUG.severity() == 10
    assert LogLevel.INFO.severity() == 20
    assert LogLevel.UNKNOWN.severity() == 21
    assert LogLevel.WARNING.severity() == 30
    assert LogLevel.ERROR.severity() == 40
    assert LogLevel.CRITICAL.severity() == 50

    assert LogLevel.TRACE.severity() < LogLevel.INFO.severity()
    assert LogLevel.WARNING.severity() < LogLevel.ERROR.severity()
    assert LogLevel.ERROR.severity() < LogLevel.CRITICAL.severity()


def test_log_level_levels_at_or_above():
    """Test LogLevel.levels_at_or_above() filters by severity."""
    warning_and_above = LogLevel.levels_at_or_above(LogLevel.WARNING)
    assert LogLevel.WARNING in warning_and_above
    assert LogLevel.ERROR in warning_and_above
    assert LogLevel.CRITICAL in warning_and_above
    assert LogLevel.INFO not in warning_and_above
    assert LogLevel.DEBUG not in warning_and_above
    assert LogLevel.TRACE not in warning_and_above

    error_and_above = LogLevel.levels_at_or_above(LogLevel.ERROR)
    assert LogLevel.ERROR in error_and_above
    assert LogLevel.CRITICAL in error_and_above
    assert LogLevel.WARNING not in error_and_above
    assert LogLevel.INFO not in error_and_above

    all_levels = LogLevel.levels_at_or_above(LogLevel.TRACE)
    assert len(all_levels) == 7


def test_log_entry_from_loki():
    """Test LogEntry.from_loki() parses Loki format correctly."""
    timestamp_ns = "1640995200000000000"
    message = "Test log message"
    labels = {"detected_level": "info", "k8s_pod_name": "test-pod"}

    entry = LogEntry.from_loki(timestamp_ns, message, labels)

    assert entry.timestamp == datetime.fromtimestamp(1640995200, tz=UTC)
    assert entry.level == LogLevel.INFO
    assert entry.message == message


def test_log_entry_from_loki_with_level_label():
    """Test LogEntry.from_loki() uses 'level' label if 'detected_level' missing."""
    timestamp_ns = "1640995200000000000"
    message = "Test log message"
    labels = {"level": "error", "k8s_pod_name": "test-pod"}

    entry = LogEntry.from_loki(timestamp_ns, message, labels)

    assert entry.level == LogLevel.ERROR
    assert entry.message == message


def test_log_entry_from_loki_extracts_level_from_message():
    """Test LogEntry.from_loki() extracts level from message if labels missing."""
    timestamp_ns = "1640995200000000000"
    message = "debug: Test log message"

    entry = LogEntry.from_loki(timestamp_ns, message, None)

    assert entry.level == LogLevel.DEBUG
    assert entry.message == message


def test_log_entry_from_loki_unknown_level():
    """Test LogEntry.from_loki() handles unknown level gracefully."""
    timestamp_ns = "1640995200000000000"
    message = "Test log message"
    labels = {"detected_level": "invalid_level"}

    entry = LogEntry.from_loki(timestamp_ns, message, labels)

    assert entry.level == LogLevel.UNKNOWN
    assert entry.message == message
