# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from unittest.mock import AsyncMock, patch

import pytest
from keycloak import KeycloakAdmin

from app.organizations.utils import get_realm_details, is_smtp_enabled_for_realm


@pytest.mark.parametrize(
    "realm, expected_value",
    [
        ({"smtpServer": {"host": "smtp.example.com"}}, True),
        ({"smtpServer": {}}, False),
        ({}, False),
    ],
)
def test_is_smtp_enabled_for_realm(realm, expected_value):
    assert is_smtp_enabled_for_realm(realm) is expected_value


@pytest.mark.asyncio
async def test_get_realm_details() -> None:
    with (
        patch(
            "app.organizations.utils.get_idps",
            return_value=[
                {
                    "enabled": True,
                },
            ],
        ),
        patch("app.organizations.utils.is_smtp_enabled_for_realm", return_value=True),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        org = await get_realm_details(kc_admin)

    assert org.idp_linked
    assert org.smtp_enabled
