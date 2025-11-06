# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
import yaml

from airm.messaging.schemas import ProjectSecretStatus, SecretsComponentKind
from app.projects.models import Project
from app.secrets.enums import SecretStatus, SecretType
from app.secrets.models import ProjectSecret
from app.secrets.utils import (
    map_secret_type_to_component_kind,
    resolve_secret_status,
    sanitize_external_secret_manifest,
)


def test_removes_namespace_from_metadata():
    manifest = {
        "apiVersion": "external-secrets.io/v1beta1",
        "kind": "ExternalSecret",
        "metadata": {"name": "my-secret", "namespace": "some-namespace"},
        "spec": {},
    }

    result_yaml = sanitize_external_secret_manifest(manifest)
    result = yaml.safe_load(result_yaml)

    assert "namespace" not in result["metadata"]
    assert result["metadata"]["name"] == "my-secret"


def test_does_nothing_if_namespace_not_present():
    manifest = {
        "apiVersion": "external-secrets.io/v1beta1",
        "kind": "ExternalSecret",
        "metadata": {"name": "my-secret"},
        "spec": {},
    }

    original = manifest.copy()
    result_yaml = sanitize_external_secret_manifest(manifest)
    result = yaml.safe_load(result_yaml)

    assert result["metadata"] == original["metadata"]
    assert "namespace" not in result["metadata"]


def test_handles_missing_metadata_field():
    manifest = {"apiVersion": "external-secrets.io/v1beta1", "kind": "ExternalSecret", "spec": {}}

    result_yaml = sanitize_external_secret_manifest(manifest)
    result = yaml.safe_load(result_yaml)

    assert "metadata" not in result
    assert result["kind"] == "ExternalSecret"


def test_returns_yaml_string():
    manifest = {"kind": "ExternalSecret", "metadata": {"name": "test", "namespace": "dev"}, "spec": {"data": []}}

    result_yaml = sanitize_external_secret_manifest(manifest)
    assert isinstance(result_yaml, str)
    assert "namespace" not in result_yaml
    assert "name: test" in result_yaml


def test_map_secret_type_to_component_kind():
    assert map_secret_type_to_component_kind(SecretType.EXTERNAL) == SecretsComponentKind.EXTERNAL_SECRET
    assert map_secret_type_to_component_kind(SecretType.KUBERNETES_SECRET) == SecretsComponentKind.KUBERNETES_SECRET


@pytest.mark.parametrize(
    "prev_status,project_secret_statuses,expected_status,expected_reason",
    [
        # No project secrets → UNASSIGNED
        (SecretStatus.SYNCED, [], SecretStatus.UNASSIGNED, None),
        # DELETING: all project secrets deleted → DELETED
        (SecretStatus.DELETING, [], SecretStatus.DELETED, None),
        # DELETING: one delete failed → DELETE_FAILED
        (
            SecretStatus.DELETING,
            [ProjectSecretStatus.DELETE_FAILED],
            SecretStatus.DELETE_FAILED,
            "Some project secrets failed to be deleted",
        ),
        # DELETING: not all deleted or failed → DELETING
        (SecretStatus.DELETING, [ProjectSecretStatus.SYNCED, ProjectSecretStatus.PENDING], SecretStatus.DELETING, None),
        # All DELETED (not deleting) → UNASSIGNED
        (SecretStatus.SYNCED, [], SecretStatus.UNASSIGNED, None),
        # Any DELETE_FAILED → DELETE_FAILED
        (
            SecretStatus.SYNCED,
            [ProjectSecretStatus.SYNCED, ProjectSecretStatus.DELETE_FAILED],
            SecretStatus.DELETE_FAILED,
            "Some project secrets failed to be deleted",
        ),
        # Any FAILED → FAILED
        (
            SecretStatus.SYNCED,
            [ProjectSecretStatus.FAILED, ProjectSecretStatus.SYNCED],
            SecretStatus.FAILED,
            "Some project secrets are in a failed state",
        ),
        # Any SYNCED_ERROR or UNKNOWN → SYNCED_ERROR
        (
            SecretStatus.SYNCED,
            [ProjectSecretStatus.SYNCED_ERROR, ProjectSecretStatus.SYNCED],
            SecretStatus.SYNCED_ERROR,
            "Some project secrets have failed to sync",
        ),
        (
            SecretStatus.SYNCED,
            [ProjectSecretStatus.UNKNOWN, ProjectSecretStatus.SYNCED],
            SecretStatus.SYNCED_ERROR,
            "Some project secrets have failed to sync",
        ),
        # All SYNCED → SYNCED
        (
            SecretStatus.PARTIALLY_SYNCED,
            [ProjectSecretStatus.SYNCED, ProjectSecretStatus.SYNCED],
            SecretStatus.SYNCED,
            None,
        ),
        # Some DELETED -> SYNCED_ERROR
        (
            SecretStatus.SYNCED,
            [ProjectSecretStatus.DELETED, "UNKNOWN", ProjectSecretStatus.SYNCED, "UNKNOWN"],
            SecretStatus.SYNCED_ERROR,
            "One or more project secrets have been deleted unexpectedly.",
        ),
        # Some SYNCED → PARTIALLY_SYNCED
        (
            SecretStatus.UNASSIGNED,
            [ProjectSecretStatus.SYNCED, ProjectSecretStatus.PENDING],
            SecretStatus.PARTIALLY_SYNCED,
            None,
        ),
        # Fallback: no rule matched → SYNCED_ERROR
        (
            SecretStatus.SYNCED,
            [ProjectSecretStatus.PENDING, "UNKNOWN"],
            SecretStatus.SYNCED_ERROR,
            "Unknown Project secret states detected.",
        ),
    ],
)
def test_resolve_secret_status(prev_status, project_secret_statuses, expected_status, expected_reason):
    project = Project(name="project-1")
    project_secrets = [ProjectSecret(status=s, project=project) for s in project_secret_statuses]
    status, status_reason = resolve_secret_status(prev_status, project_secrets)
    assert status == expected_status
    assert expected_reason == status_reason
