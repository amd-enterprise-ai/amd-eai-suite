# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
import yaml

from airm.secrets import utils as packgeUtils
from airm.secrets.constants import PROJECT_SECRET_ID_LABEL

# Dummy constants for testing
DUMMY_API_GROUP = "external-secrets.io"
DUMMY_KIND = "ExternalSecret"
DUMMY_VERSION = "v1beta1"
DUMMY_SECRET_ID = str(uuid4())


@pytest.fixture(autouse=True)
def patch_constants(monkeypatch):
    monkeypatch.setattr(packgeUtils, "EXTERNAL_SECRETS_API_GROUP", DUMMY_API_GROUP)
    monkeypatch.setattr(packgeUtils, "EXTERNAL_SECRETS_KIND", DUMMY_KIND)


def test_validate_external_secret_manifest_valid():
    manifest = {
        "apiVersion": f"{DUMMY_API_GROUP}/{DUMMY_VERSION}",
        "kind": DUMMY_KIND,
        "metadata": {"name": "foo", "namespace": "bar", "labels": {PROJECT_SECRET_ID_LABEL: DUMMY_SECRET_ID}},
        "spec": {"data": [{"secretKey": "foo", "remoteRef": {"key": "bar"}}]},
    }
    manifest_yaml = yaml.safe_dump(manifest)

    # Should successfully validate and return a dict
    result = packgeUtils.validate_external_secret_manifest(manifest_yaml)
    assert isinstance(result, dict)
    assert result["apiVersion"] == f"{DUMMY_API_GROUP}/{DUMMY_VERSION}"
    assert result["kind"] == DUMMY_KIND


@pytest.mark.parametrize(
    "field, value",
    [
        ("apiVersion", "wrong/version"),
        ("kind", "WrongKind"),
        ("metadata", None),
        ("spec", None),
    ],
)
def test_validate_external_secret_manifest_invalid(field, value):
    manifest = {
        "apiVersion": f"{DUMMY_API_GROUP}/{DUMMY_VERSION}",
        "kind": DUMMY_KIND,
        "metadata": {"name": "foo", "namespace": "bar"},
        "spec": {"data": [{"secretKey": "foo", "remoteRef": {"key": "bar"}}]},
    }
    if value is None:
        manifest.pop(field)
    else:
        manifest[field] = value

    manifest_yaml = yaml.safe_dump(manifest)

    # Should raise an Exception for invalid manifests
    with pytest.raises(Exception):
        packgeUtils.validate_external_secret_manifest(manifest_yaml)
