# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from airm.secrets.constants import PROJECT_SECRET_ID_LABEL
from app.secrets import utils

# Import the functions to test

# Dummy constants for testing
DUMMY_API_GROUP = "external-secrets.io"
DUMMY_KIND = "ExternalSecret"
DUMMY_VERSION = "v1beta1"
DUMMY_SECRET_ID = uuid4()
DUMMY_SECRET_SCOPE = "project"


def test_patch_external_secret_manifest_sets_fields():
    manifest = {}
    namespace = "test-ns"
    secret_name = "test-secret"
    project_secret_id = uuid4()
    result = utils.patch_external_secret_manifest(namespace, secret_name, manifest, project_secret_id=project_secret_id)
    assert result["metadata"]["name"] == secret_name
    assert result["metadata"]["namespace"] == namespace
    assert str(result["metadata"]["labels"][PROJECT_SECRET_ID_LABEL]) == str(project_secret_id)


def test_create_project_secret_status_message_sets_fields():
    # Patch ProjectSecretsUpdateMessage to a dummy class for inspection
    class DummyMsg:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    with patch("app.secrets.utils.ProjectSecretsUpdateMessage", DummyMsg):
        status = MagicMock()
        reason = "Test reason"
        msg = utils.create_project_secret_status_message(DUMMY_SECRET_ID, DUMMY_SECRET_SCOPE, status, reason)
        assert msg.message_type == "project_secrets_update"

        assert msg.status == status
        assert msg.status_reason == reason
        assert isinstance(msg.updated_at, datetime)
        assert msg.updated_at.tzinfo == UTC
        assert msg.project_secret_id == DUMMY_SECRET_ID
        assert msg.secret_scope == DUMMY_SECRET_SCOPE


@pytest.mark.parametrize(
    "event_type,expected_status,expected_message",
    [
        ("DELETED", utils.ProjectSecretStatus.DELETED, "Resource has been removed from the cluster."),
        ("UNKNOWN_EVENT", None, "Secret status could not be determined."),
    ],
)
def test_get_status_for_external_secret_event_type_mapping(event_type, expected_status, expected_message):
    resource = MagicMock()
    status, message = utils.get_status_for_external_secret(resource, event_type)
    assert status == expected_status
    assert message == expected_message


@pytest.mark.parametrize(
    "cond_status,expected_status,expected_message",
    [
        ("True", utils.ProjectSecretStatus.SYNCED, "Secret is ready."),
        ("False", utils.ProjectSecretStatus.SYNCED_ERROR, "Secret is not ready."),
    ],
)
def test_get_status_for_external_secret_ready_condition_dict(cond_status, expected_status, expected_message):
    resource = MagicMock()
    resource.status = {
        "conditions": [
            {
                "type": "Ready",
                "status": cond_status,
            }
        ]
    }
    status, message = utils.get_status_for_external_secret(resource, "SOME_EVENT")
    assert status == expected_status
    assert message == expected_message


def test_get_status_for_external_secret_ready_condition_dict_with_message_and_reason():
    resource = MagicMock()
    resource.status = {
        "conditions": [
            {
                "type": "Ready",
                "status": "False",
                "reason": "SomeReason",
                "message": "Failure message",
            }
        ]
    }
    status, message = utils.get_status_for_external_secret(resource, "SOME_EVENT")
    assert status == utils.ProjectSecretStatus.SYNCED_ERROR
    assert message == "Failure message"


def test_get_status_for_external_secret_ready_condition_dict_with_reason_only():
    resource = MagicMock()
    resource.status = {
        "conditions": [
            {
                "type": "Ready",
                "status": "False",
                "reason": "SomeReason",
            }
        ]
    }
    status, message = utils.get_status_for_external_secret(resource, "SOME_EVENT")
    assert status == utils.ProjectSecretStatus.SYNCED_ERROR
    assert message == "SomeReason"


def test_get_status_for_external_secret_ready_condition_object():
    # Simulate a resource with .status.conditions as objects
    class Condition:
        def __init__(self, type_, status, reason=None, message=None):
            self.type = type_
            self.status = status
            self.status_reason = reason
            self.message = message

    class Status:
        def __init__(self, conditions):
            self.conditions = conditions

    resource = MagicMock()
    resource.status = Status(
        [
            Condition("Ready", "True", reason="SomeReason", message="All good"),
        ]
    )
    status, message = utils.get_status_for_external_secret(resource, "SOME_EVENT")
    assert status == utils.ProjectSecretStatus.SYNCED
    assert message == "All good"


def test_get_status_for_external_secret_no_conditions():
    resource = MagicMock()
    resource.status = {}
    status, message = utils.get_status_for_external_secret(resource, "SOME_EVENT")
    assert status is None
    assert message == "Secret status could not be determined."


def test_get_status_for_external_secret_conditions_empty_list():
    resource = MagicMock()
    resource.status = {"conditions": []}
    status, message = utils.get_status_for_external_secret(resource, "SOME_EVENT")
    assert status is None
    assert message == "Secret status could not be determined."


def test_patch_kubernetes_secret_manifest_merges_labels():
    manifest = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": "original",
            "labels": {"custom": "label"},
            "annotations": {"note": "keep"},
        },
        "stringData": {"token": "abc"},
    }

    patched = utils.patch_kubernetes_secret_manifest(
        namespace="target-ns",
        secret_name="patched",
        manifest=manifest,
        project_secret_id=str(DUMMY_SECRET_ID),
    )

    assert patched["metadata"]["name"] == "patched"
    assert patched["metadata"]["namespace"] == "target-ns"
    assert patched["metadata"]["labels"][PROJECT_SECRET_ID_LABEL] == str(DUMMY_SECRET_ID)
    assert patched["metadata"]["labels"]["custom"] == "label"
    assert patched["metadata"]["annotations"]["note"] == "keep"


@pytest.mark.parametrize(
    "event_type,expected_status",
    [
        ("ADDED", utils.ProjectSecretStatus.SYNCED),
        ("MODIFIED", utils.ProjectSecretStatus.SYNCED),
        ("DELETED", utils.ProjectSecretStatus.DELETED),
        ("SOMETHING", utils.ProjectSecretStatus.UNKNOWN),
    ],
)
def test_get_status_for_kubernetes_secret(event_type, expected_status):
    resource = MagicMock()
    status, _ = utils.get_status_for_kubernetes_secret(resource, event_type)
    assert status == expected_status
