# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
import asyncio

from keycloak import KeycloakAdmin

from ..utilities.keycloak_admin import (
    get_idps,
    get_realm,
)
from .schemas import OrganizationResponse


async def get_realm_details(kc_admin: KeycloakAdmin) -> OrganizationResponse:
    idps, realm = await asyncio.gather(
        get_idps(kc_admin=kc_admin),
        get_realm(kc_admin=kc_admin),
    )
    idp_linked = len([idp for idp in idps if idp["enabled"]]) > 0
    smtp_enabled = is_smtp_enabled_for_realm(realm)

    return OrganizationResponse(
        idp_linked=idp_linked,
        smtp_enabled=smtp_enabled,
    )


def is_smtp_enabled_for_realm(realm: dict) -> bool:
    return realm.get("smtpServer", {}).get("host") is not None
