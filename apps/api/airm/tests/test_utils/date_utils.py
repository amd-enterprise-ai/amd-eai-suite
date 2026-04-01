# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime


def datetime_to_iso_format(date: datetime) -> str:
    """Convert a date time to ISO format with Zulu timezone for UTC dates."""
    return date.isoformat().replace("+00:00", "Z")
