# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
import yaml

from airm.messaging.schemas import ProjectSecretStatus, SecretKind, SecretScope
from app.projects.models import Project
from app.secrets.enums import SecretStatus, SecretUseCase
from app.secrets.models import OrganizationSecretAssignment
from app.secrets.schemas import BaseSecretIn
from app.secrets.utils import (
    publish_project_secret_creation_message,
    publish_project_secret_deletion_message,
    publish_secret_deletion_message,
    resolve_secret_status,
    sanitize_external_secret_manifest,
    validate_and_patch_secret_manifest,
    validate_secret_manifest_for_api,
)
from app.utilities.exceptions import ValidationException


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
    project_secrets_assignments = [
        OrganizationSecretAssignment(status=s, project=project) for s in project_secret_statuses
    ]
    status, status_reason = resolve_secret_status(prev_status, project_secrets_assignments)
    assert status == expected_status
    assert expected_reason == status_reason


# Tests for validate_secret_manifest and validate_and_patch_secret_manifest


def test_validate_secret_manifest_organization_scoped_external_secret():
    manifest_yaml = """
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: org-external-secret
spec:
  secretStoreRef:
    name: test-store
    kind: SecretStore
  target:
    name: test-secret
  data:
  - secretKey: key1
    remoteRef:
      key: remote-key1
"""

    secret_in = BaseSecretIn(
        name="org-external-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope="Organization",
        manifest=manifest_yaml,
    )

    result = validate_secret_manifest_for_api(secret_in, manifest_yaml)

    assert isinstance(result, dict)
    assert result["kind"] == "ExternalSecret"
    assert result["metadata"]["name"] == "org-external-secret"


def test_validate_secret_manifest_project_scoped_kubernetes_secret():
    manifest_yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: project-k8s-secret
type: Opaque
data:
  token: dG9rZW4=
"""

    secret_in = BaseSecretIn(
        name="project-k8s-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope="Project",
        manifest=manifest_yaml,
    )

    result = validate_secret_manifest_for_api(secret_in, manifest_yaml)

    assert isinstance(result, dict)
    assert result["kind"] == "Secret"
    assert result["apiVersion"] == "v1"
    assert result["metadata"]["name"] == "project-k8s-secret"


def test_validate_secret_manifest_project_scoped_external_secret():
    manifest_yaml = """
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: project-external-secret
spec:
  secretStoreRef:
    name: test-store
  target:
    name: test-target
  data: []
"""

    secret_in = BaseSecretIn(
        name="project-external-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope="Project",
        manifest=manifest_yaml,
    )

    result = validate_secret_manifest_for_api(secret_in, manifest_yaml)

    assert isinstance(result, dict)
    assert result["kind"] == "ExternalSecret"


def test_validate_secret_manifest_unsupported_type():
    manifest_yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
"""

    secret_in = Mock(spec=BaseSecretIn)
    secret_in.scope = "Project"
    secret_in.type = "UnsupportedType"
    secret_in.manifest = manifest_yaml

    with pytest.raises(ValueError) as exc_info:
        validate_secret_manifest_for_api(secret_in, manifest_yaml)

    assert "Unsupported component kind" in str(exc_info.value)


def test_validate_and_patch_secret_manifest_success_without_use_case():
    manifest_yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
type: Opaque
data:
  key1: dmFsdWUx
"""

    secret_in = BaseSecretIn(
        name="test-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope="Project",
        manifest=manifest_yaml,
    )

    result = validate_and_patch_secret_manifest(secret_in)

    assert isinstance(result, dict)
    assert result["kind"] == "Secret"
    assert result["metadata"]["name"] == "test-secret"
    # Should not have use-case label
    assert "airm.silogen.com/use-case" not in result["metadata"].get("labels", {})


def test_validate_and_patch_secret_manifest_success_with_use_case():
    manifest_yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: hf-token-secret
type: Opaque
data:
  token: aGZfdG9rZW4=
"""

    secret_in = BaseSecretIn(
        name="hf-token-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope="Project",
        manifest=manifest_yaml,
        use_case=SecretUseCase.HUGGING_FACE,
    )

    result = validate_and_patch_secret_manifest(secret_in)

    assert isinstance(result, dict)
    assert result["kind"] == "Secret"
    assert result["metadata"]["name"] == "hf-token-secret"
    # Should have use-case label
    assert "labels" in result["metadata"]
    assert result["metadata"]["labels"]["airm.silogen.com/use-case"] == "huggingface"


def test_validate_and_patch_secret_manifest_no_manifest():
    # Use a mock to bypass Pydantic's manifest length validation
    secret_in = Mock(spec=BaseSecretIn)
    secret_in.name = "test-secret"
    secret_in.type = SecretKind.KUBERNETES_SECRET
    secret_in.scope = "Project"
    secret_in.manifest = ""  # Empty manifest
    secret_in.use_case = None

    with pytest.raises(ValidationException) as exc_info:
        validate_and_patch_secret_manifest(secret_in)

    assert "Manifest must be provided for secret creation" in str(exc_info.value)


def test_validate_and_patch_secret_manifest_invalid_yaml():
    invalid_manifest = """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
  # Invalid YAML syntax
  data: [unclosed
"""

    secret_in = BaseSecretIn(
        name="test-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope="Project",
        manifest=invalid_manifest,
    )

    with pytest.raises(ValidationException) as exc_info:
        validate_and_patch_secret_manifest(secret_in)

    assert "Invalid Secret manifest" in str(exc_info.value)


def test_validate_and_patch_secret_manifest_invalid_external_secret():
    invalid_manifest = """
apiVersion: v1
kind: ExternalSecret
metadata:
  name: invalid-external-secret
"""

    secret_in = BaseSecretIn(
        name="invalid-external-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope="Organization",
        manifest=invalid_manifest,
    )

    with pytest.raises(ValidationException) as exc_info:
        validate_and_patch_secret_manifest(secret_in)

    assert "Invalid Secret manifest" in str(exc_info.value)


def test_validate_and_patch_secret_manifest_preserves_existing_labels():
    manifest_yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
  labels:
    custom-label: custom-value
    another-label: another-value
type: Opaque
data:
  key: dmFsdWU=
"""

    secret_in = BaseSecretIn(
        name="test-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope="Project",
        manifest=manifest_yaml,
        use_case=SecretUseCase.HUGGING_FACE,
    )

    result = validate_and_patch_secret_manifest(secret_in)

    assert "labels" in result["metadata"]
    # Original labels should be preserved
    assert result["metadata"]["labels"]["custom-label"] == "custom-value"
    assert result["metadata"]["labels"]["another-label"] == "another-value"
    # Use case label should be added
    assert result["metadata"]["labels"]["airm.silogen.com/use-case"] == "huggingface"


def test_validate_and_patch_secret_manifest_s3_use_case():
    manifest_yaml = """
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: s3-secret
spec:
  secretStoreRef:
    name: s3-store
  target:
    name: s3-target
  data: []
"""

    secret_in = BaseSecretIn(
        name="s3-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope="Organization",
        manifest=manifest_yaml,
        use_case=SecretUseCase.S3,
    )

    result = validate_and_patch_secret_manifest(secret_in)

    assert isinstance(result, dict)
    assert result["metadata"]["labels"]["airm.silogen.com/use-case"] == "s3"


# Tests for calculate_assignment_changes


def test_calculate_assignment_changes_add_projects():
    """Test adding new projects to an existing assignment."""
    from app.secrets.utils import calculate_assignment_changes

    current = {1, 2, 3}
    new = {1, 2, 3, 4, 5}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == {4, 5}
    assert to_remove == set()


def test_calculate_assignment_changes_remove_projects():
    """Test removing projects from an existing assignment."""
    from app.secrets.utils import calculate_assignment_changes

    current = {1, 2, 3, 4, 5}
    new = {1, 2}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == set()
    assert to_remove == {3, 4, 5}


def test_calculate_assignment_changes_add_and_remove():
    """Test both adding and removing projects in the same operation."""
    from app.secrets.utils import calculate_assignment_changes

    current = {1, 2, 3}
    new = {2, 3, 4, 5}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == {4, 5}
    assert to_remove == {1}


def test_calculate_assignment_changes_no_changes():
    """Test when there are no changes to assignments."""
    from app.secrets.utils import calculate_assignment_changes

    current = {1, 2, 3}
    new = {1, 2, 3}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == set()
    assert to_remove == set()


def test_calculate_assignment_changes_empty_current():
    """Test when starting from no assignments."""
    from app.secrets.utils import calculate_assignment_changes

    current = set()
    new = {1, 2, 3}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == {1, 2, 3}
    assert to_remove == set()


def test_calculate_assignment_changes_empty_new():
    """Test when removing all assignments."""
    from app.secrets.utils import calculate_assignment_changes

    current = {1, 2, 3}
    new = set()

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == set()
    assert to_remove == {1, 2, 3}


# Tests for message publishing functions


@pytest.mark.asyncio
async def test_publish_secret_deletion_message():
    cluster_id = uuid4()
    project_secret_id = uuid4()
    project_name = "test-project"
    secret_type = SecretKind.EXTERNAL_SECRET
    secret_scope = SecretScope.PROJECT

    mock_sender = AsyncMock()
    await publish_secret_deletion_message(
        cluster_id, project_secret_id, project_name, secret_type, secret_scope, mock_sender
    )

    mock_sender.enqueue.assert_called_once()
    call_args = mock_sender.enqueue.call_args
    assert call_args[0][0] == cluster_id

    message = call_args[0][1]
    assert message.message_type == "project_secrets_delete"
    assert message.project_secret_id == project_secret_id
    assert message.project_name == project_name
    assert message.secret_type == SecretKind.EXTERNAL_SECRET
    assert message.secret_scope == secret_scope


@pytest.mark.asyncio
async def test_publish_secret_deletion_message_kubernetes_secret():
    cluster_id = uuid4()
    project_secret_id = uuid4()
    project_name = "test-project"
    secret_type = SecretKind.KUBERNETES_SECRET
    secret_scope = SecretScope.PROJECT

    mock_sender = AsyncMock()
    await publish_secret_deletion_message(
        cluster_id, project_secret_id, project_name, secret_type, secret_scope, mock_sender
    )

    mock_sender.enqueue.assert_called_once()
    call_args = mock_sender.enqueue.call_args
    message = call_args[0][1]
    assert message.secret_type == SecretKind.KUBERNETES_SECRET
    assert message.secret_scope == secret_scope


@pytest.mark.asyncio
async def test_publish_project_secret_deletion_message():
    # Create mock objects
    mock_project = Mock()
    mock_project.cluster_id = uuid4()
    mock_project.name = "test-project"

    mock_assignment = Mock()
    mock_assignment.id = uuid4()
    mock_assignment.project = mock_project

    mock_parent_secret = Mock()
    mock_parent_secret.type = SecretKind.EXTERNAL_SECRET
    mock_parent_secret.scope = SecretScope.ORGANIZATION

    mock_sender = AsyncMock()
    await publish_project_secret_deletion_message(mock_assignment, mock_parent_secret, mock_sender)

    mock_sender.enqueue.assert_called_once()
    call_args = mock_sender.enqueue.call_args
    assert call_args[0][0] == mock_project.cluster_id

    message = call_args[0][1]
    assert message.message_type == "project_secrets_delete"
    assert message.project_secret_id == mock_assignment.id
    assert message.project_name == mock_project.name
    assert message.secret_type == SecretKind.EXTERNAL_SECRET


@pytest.mark.asyncio
async def test_publish_project_secret_creation_message_with_project_scoped_secret():
    # Create mock project-scoped secret
    mock_project = Mock()
    mock_project.cluster_id = uuid4()
    mock_project.name = "test-project"

    mock_secret = Mock()
    mock_secret.id = uuid4()
    mock_secret.name = "test-secret"
    mock_secret.type = SecretKind.EXTERNAL_SECRET
    mock_secret.scope = SecretScope.PROJECT
    mock_secret.project = mock_project

    manifest_yaml = "apiVersion: external-secrets.io/v1\nkind: ExternalSecret"

    mock_sender = AsyncMock()
    await publish_project_secret_creation_message(mock_secret, manifest_yaml, mock_sender)

    mock_sender.enqueue.assert_called_once()
    call_args = mock_sender.enqueue.call_args
    assert call_args[0][0] == mock_project.cluster_id

    message = call_args[0][1]
    assert message.message_type == "project_secrets_create"
    assert message.project_secret_id == mock_secret.id
    assert message.secret_name == mock_secret.name
    assert message.project_name == mock_project.name
    assert message.manifest == manifest_yaml
    assert message.secret_type == SecretKind.EXTERNAL_SECRET
    assert message.secret_scope == SecretScope.PROJECT


@pytest.mark.asyncio
async def test_publish_project_secret_creation_message_with_organization_assignment():
    # Create mock organization assignment
    mock_project = Mock()
    mock_project.cluster_id = uuid4()
    mock_project.name = "test-project"

    mock_assignment = Mock()
    mock_assignment.id = uuid4()
    mock_assignment.project = mock_project

    mock_parent_secret = Mock()
    mock_parent_secret.name = "org-secret"
    mock_parent_secret.type = SecretKind.EXTERNAL_SECRET
    mock_parent_secret.scope = SecretScope.ORGANIZATION

    manifest_yaml = "apiVersion: external-secrets.io/v1\nkind: ExternalSecret"

    mock_sender = AsyncMock()
    await publish_project_secret_creation_message(
        mock_assignment, manifest_yaml, mock_sender, parent_secret=mock_parent_secret
    )

    mock_sender.enqueue.assert_called_once()
    call_args = mock_sender.enqueue.call_args
    assert call_args[0][0] == mock_project.cluster_id

    message = call_args[0][1]
    assert message.message_type == "project_secrets_create"
    assert message.project_secret_id == mock_assignment.id
    assert message.secret_name == mock_parent_secret.name
    assert message.project_name == mock_project.name
    assert message.manifest == manifest_yaml
    assert message.secret_type == SecretKind.EXTERNAL_SECRET
    assert message.secret_scope == SecretScope.ORGANIZATION


def test_build_project_secret_response_filters_by_project():
    """Test that only assignments for the specified project are returned."""
    from datetime import UTC, datetime

    from app.secrets.models import OrganizationScopedSecret
    from app.secrets.utils import build_project_secret_response

    # Create target project and another project
    target_project = Mock(spec=Project)
    target_project.id = uuid4()
    target_project.name = "target-project"

    other_project = Mock(spec=Project)
    other_project.id = uuid4()
    other_project.name = "other-project"

    # Create organization-scoped secret
    org_secret = Mock(spec=OrganizationScopedSecret)
    org_secret.id = uuid4()
    org_secret.name = "org-secret"
    org_secret.type = SecretKind.EXTERNAL_SECRET
    org_secret.scope = SecretScope.ORGANIZATION
    org_secret.status = SecretStatus.SYNCED
    org_secret.status_reason = None
    org_secret.use_case = SecretUseCase.S3
    org_secret.created_at = datetime.now(UTC)
    org_secret.updated_at = datetime.now(UTC)
    org_secret.created_by = "user@test.com"
    org_secret.updated_by = "user@test.com"

    # Create two assignments: one for target project, one for other project
    target_assignment = Mock(spec=OrganizationSecretAssignment)
    target_assignment.id = uuid4()
    target_assignment.project_id = target_project.id
    target_assignment.status = ProjectSecretStatus.SYNCED
    target_assignment.status_reason = None
    target_assignment.created_at = datetime.now(UTC)
    target_assignment.updated_at = datetime.now(UTC)
    target_assignment.created_by = "user@test.com"
    target_assignment.updated_by = "user@test.com"
    target_assignment.project = target_project

    other_assignment = Mock(spec=OrganizationSecretAssignment)
    other_assignment.id = uuid4()
    other_assignment.project_id = other_project.id
    other_assignment.status = ProjectSecretStatus.PENDING
    other_assignment.status_reason = None
    other_assignment.created_at = datetime.now(UTC)
    other_assignment.updated_at = datetime.now(UTC)
    other_assignment.created_by = "user@test.com"
    other_assignment.updated_by = "user@test.com"
    other_assignment.project = other_project

    # Attach both assignments (simulating lazy="joined" behavior)
    org_secret.organization_secret_assignments = [target_assignment, other_assignment]

    # Call function for target_project
    result = build_project_secret_response([org_secret], target_project)

    # Should only return the assignment for target_project
    assert len(result.project_secrets) == 1
    assert result.project_secrets[0].id == target_assignment.id
    assert result.project_secrets[0].project_id == target_project.id
    assert result.project_secrets[0].project_name == target_project.name
