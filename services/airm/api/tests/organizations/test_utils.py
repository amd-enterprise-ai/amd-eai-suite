# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime

import pytest

from app.organizations.models import Organization as OrganizationModel
from app.organizations.utils import is_smtp_enabled_for_realm, merge_organization_details


def test_merge_organization_details():
    keycloak_organization = {
        "id": "fb925978-fafe-4b91-bb48-4467105deb46",
        "name": "organization_1",
        "enabled": True,
        "domains": [{"name": "example1.com"}],
    }

    organization = OrganizationModel(
        id=uuid.UUID("398b1744-97dd-48f1-85cc-73f76caf98c0"),
        name="Organization Name",
        keycloak_organization_id=uuid.UUID("fb925978-fafe-4b91-bb48-4467105deb46"),
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    ret = merge_organization_details(keycloak_organization, organization, True, False)
    assert ret.name == "Organization Name"
    assert ret.id == organization.id
    assert ret.domains == ["example1.com"]
    assert ret.idp_linked
    assert ret.smtp_enabled is False


@pytest.mark.parametrize(
    "realm, expected_value",
    [
        ({"smtpServer": {"host": "smtp.example.com"}}, True),
        ({"smtpServer": {}}, False),
    ],
)
def test_is_smtp_enabled_for_realm(realm, expected_value):
    assert is_smtp_enabled_for_realm(realm) is expected_value
