# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from .models import Organization as OrganizationModel
from .schemas import OrganizationResponse


def merge_organization_details(
    keycloak_org: dict, organization: OrganizationModel, idp_linked: bool, smtp_enabled: bool
) -> OrganizationResponse:
    """Merge Keycloak organization data with DB organization model."""
    domain_names = [domain["name"] for domain in keycloak_org.get("domains", []) if "name" in domain]

    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        domains=domain_names,
        idp_linked=idp_linked,
        smtp_enabled=smtp_enabled,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        created_by=organization.created_by,
        updated_by=organization.updated_by,
    )


def is_smtp_enabled_for_realm(realm: dict) -> bool:
    return realm.get("smtpServer", {}).get("host") is not None
