# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
import yaml

from airm.messaging.schemas import SecretKind
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


def test_validate_secret_manifest_external_secret():
    """Test the universal validator with ExternalSecret."""
    manifest = {
        "apiVersion": f"{DUMMY_API_GROUP}/{DUMMY_VERSION}",
        "kind": DUMMY_KIND,
        "metadata": {"name": "foo", "namespace": "bar", "labels": {PROJECT_SECRET_ID_LABEL: DUMMY_SECRET_ID}},
        "spec": {"data": [{"secretKey": "foo", "remoteRef": {"key": "bar"}}]},
    }
    manifest_yaml = yaml.safe_dump(manifest)

    result = packgeUtils.validate_secret_manifest(manifest_yaml, SecretKind.EXTERNAL_SECRET)
    assert isinstance(result, dict)
    assert result["apiVersion"] == f"{DUMMY_API_GROUP}/{DUMMY_VERSION}"
    assert result["kind"] == DUMMY_KIND


def test_validate_secret_manifest_kubernetes_secret():
    """Test the universal validator with KubernetesSecret."""
    manifest = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "test-secret", "labels": {PROJECT_SECRET_ID_LABEL: DUMMY_SECRET_ID}},
        "data": {"key": "dmFsdWU="},
    }
    manifest_yaml = yaml.safe_dump(manifest)

    result = packgeUtils.validate_secret_manifest(manifest_yaml, SecretKind.KUBERNETES_SECRET)
    assert isinstance(result, dict)
    assert result["apiVersion"] == "v1"
    assert result["kind"] == "Secret"


def test_validate_secret_manifest_invalid_component_kind():
    """Test that the universal validator raises ValueError for unsupported component kind."""
    manifest_yaml = yaml.safe_dump({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "test"}})

    # Use a mock component kind that doesn't exist
    with pytest.raises(ValueError, match="Unsupported component kind"):
        packgeUtils.validate_secret_manifest(manifest_yaml, "InvalidKind")  # type: ignore


def test_get_kubernetes_kind_external_secret():
    """Test get_kubernetes_kind for ExternalSecret."""
    result = packgeUtils.get_kubernetes_kind(SecretKind.EXTERNAL_SECRET)
    assert result == DUMMY_KIND


def test_get_kubernetes_kind_kubernetes_secret():
    """Test get_kubernetes_kind for KubernetesSecret."""
    result = packgeUtils.get_kubernetes_kind(SecretKind.KUBERNETES_SECRET)
    assert result == "Secret"


def test_get_kubernetes_kind_invalid():
    """Test that get_kubernetes_kind raises ValueError for unsupported component kind."""
    with pytest.raises(ValueError, match="Unsupported component kind"):
        packgeUtils.get_kubernetes_kind("InvalidKind")  # type: ignore
