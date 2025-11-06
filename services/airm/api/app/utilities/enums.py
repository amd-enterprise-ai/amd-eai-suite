# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class Roles(StrEnum):
    """
    Enum class for the roles that can be set in the token.
    """

    PLATFORM_ADMINISTRATOR = "Platform Administrator"
    SUPER_ADMINISTRATOR = "Super Administrator"
    TEAM_MEMBER = "Team Member"
