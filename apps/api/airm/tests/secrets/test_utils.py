# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
import yaml

from app.messaging.schemas import (
    ExternalSecretManifest,
    KubernetesMetadata,
    KubernetesSecretManifest,
    ProjectSecretStatus,
    SecretKind,
    SecretScope,
)
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.secrets import constants as secrets_constants
from app.secrets import utils as packgeUtils
from app.secrets.constants import PROJECT_SECRET_ID_LABEL, PROJECT_SECRET_SCOPE_LABEL, PROJECT_SECRET_USE_CASE_LABEL
from app.secrets.enums import SecretStatus, SecretUseCase
from app.secrets.models import OrganizationScopedSecret, OrganizationSecretAssignment
from app.secrets.schemas import BaseSecretIn
from app.secrets.utils import (
    build_project_secret_response,
    calculate_assignment_changes,
    parse_manifest_yaml_to_model,
    publish_project_secret_creation_message,
    publish_project_secret_deletion_message,
    publish_secret_deletion_message,
    resolve_secret_status,
    sanitize_external_secret_manifest,
    validate_and_patch_secret_manifest,
)
from app.utilities.exceptions import ValidationException


def test_removes_namespace_from_metadata():
    manifest = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1beta1",
        kind="ExternalSecret",
        metadata=KubernetesMetadata(name="my-secret", namespace="some-namespace"),
        spec={},
    )

    result = sanitize_external_secret_manifest(manifest)

    assert result.metadata.namespace is None
    assert result.metadata.name == "my-secret"


def test_does_nothing_if_namespace_not_present():
    manifest = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1beta1",
        kind="ExternalSecret",
        metadata=KubernetesMetadata(name="my-secret"),
        spec={},
    )

    result = sanitize_external_secret_manifest(manifest)

    assert result.metadata.name == "my-secret"
    assert result.metadata.namespace is None


def test_handles_missing_metadata_field():
    manifest = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1beta1", kind="ExternalSecret", metadata=KubernetesMetadata(), spec={}
    )

    result = sanitize_external_secret_manifest(manifest)

    assert result.kind == "ExternalSecret"
    assert result.metadata.namespace is None


def test_returns_pydantic_model():
    manifest = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1beta1",
        kind="ExternalSecret",
        metadata=KubernetesMetadata(name="test", namespace="dev"),
        spec={"data": []},
    )

    result = sanitize_external_secret_manifest(manifest)
    assert isinstance(result, ExternalSecretManifest)
    assert result.metadata.namespace is None
    assert result.metadata.name == "test"


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
        # All PENDING → PENDING
        (SecretStatus.PENDING, [ProjectSecretStatus.PENDING, ProjectSecretStatus.PENDING], SecretStatus.PENDING, None),
        # Fallback: no rule matched → SYNCED_ERROR (with invalid status values)
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

    result = parse_manifest_yaml_to_model(manifest_yaml, SecretKind.EXTERNAL_SECRET)

    assert isinstance(result, ExternalSecretManifest)
    assert result.kind == "ExternalSecret"
    assert result.metadata.name == "org-external-secret"


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

    result = parse_manifest_yaml_to_model(manifest_yaml, SecretKind.KUBERNETES_SECRET)

    assert isinstance(result, KubernetesSecretManifest)
    assert result.kind == "Secret"
    assert result.apiVersion == "v1"
    assert result.metadata.name == "project-k8s-secret"


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

    result = parse_manifest_yaml_to_model(manifest_yaml, SecretKind.EXTERNAL_SECRET)

    assert isinstance(result, ExternalSecretManifest)
    assert result.kind == "ExternalSecret"


def test_validate_secret_manifest_unsupported_type():
    manifest_yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
"""

    with pytest.raises(ValidationException) as exc_info:
        parse_manifest_yaml_to_model(manifest_yaml, "UnsupportedType")  # type: ignore

    assert "Unsupported component kind: UnsupportedType" in str(exc_info.value)


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
        name="test-secret", type=SecretKind.KUBERNETES_SECRET, scope="Project", manifest=manifest_yaml
    )

    result = validate_and_patch_secret_manifest(secret_in)

    assert isinstance(result, KubernetesSecretManifest)
    assert result.kind == "Secret"
    assert result.metadata.name == "test-secret"
    # Should not have use-case label
    assert result.metadata.labels is None or PROJECT_SECRET_USE_CASE_LABEL not in result.metadata.labels


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

    assert isinstance(result, KubernetesSecretManifest)
    assert result.kind == "Secret"
    assert result.metadata.name == "hf-token-secret"
    # Should have use-case label
    assert result.metadata.labels is not None
    assert result.metadata.labels[PROJECT_SECRET_USE_CASE_LABEL] == "huggingface"


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
        name="test-secret", type=SecretKind.KUBERNETES_SECRET, scope="Project", manifest=invalid_manifest
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
        name="invalid-external-secret", type=SecretKind.EXTERNAL_SECRET, scope="Organization", manifest=invalid_manifest
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

    assert result.metadata.labels is not None
    # Original labels should be preserved
    assert result.metadata.labels["custom-label"] == "custom-value"
    assert result.metadata.labels["another-label"] == "another-value"
    # Use case label should be added
    assert result.metadata.labels[PROJECT_SECRET_USE_CASE_LABEL] == "huggingface"


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

    assert isinstance(result, ExternalSecretManifest)
    assert result.metadata.labels is not None
    assert result.metadata.labels[PROJECT_SECRET_USE_CASE_LABEL] == "s3"


# Tests for calculate_assignment_changes


def test_calculate_assignment_changes_add_projects():
    """Test adding new projects to an existing assignment."""

    current = {1, 2, 3}
    new = {1, 2, 3, 4, 5}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == {4, 5}
    assert to_remove == set()


def test_calculate_assignment_changes_remove_projects():
    """Test removing projects from an existing assignment."""

    current = {1, 2, 3, 4, 5}
    new = {1, 2}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == set()
    assert to_remove == {3, 4, 5}


def test_calculate_assignment_changes_add_and_remove():
    """Test both adding and removing projects in the same operation."""

    current = {1, 2, 3}
    new = {2, 3, 4, 5}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == {4, 5}
    assert to_remove == {1}


def test_calculate_assignment_changes_no_changes():
    """Test when there are no changes to assignments."""

    current = {1, 2, 3}
    new = {1, 2, 3}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == set()
    assert to_remove == set()


def test_calculate_assignment_changes_empty_current():
    """Test when starting from no assignments."""

    current = set()
    new = {1, 2, 3}

    to_add, to_remove = calculate_assignment_changes(current, new)

    assert to_add == {1, 2, 3}
    assert to_remove == set()


def test_calculate_assignment_changes_empty_new():
    """Test when removing all assignments."""

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

    # Create Pydantic manifest model
    manifest_model = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1",
        kind="ExternalSecret",
        metadata=KubernetesMetadata(name="test-secret"),
        spec={"secretStoreRef": {"name": "vault-backend"}},
    )

    mock_sender = AsyncMock()
    await publish_project_secret_creation_message(mock_secret, manifest_model, mock_sender)

    mock_sender.enqueue.assert_called_once()
    call_args = mock_sender.enqueue.call_args
    assert call_args[0][0] == mock_project.cluster_id

    message = call_args[0][1]
    assert message.message_type == "project_secrets_create"
    assert isinstance(message.manifest, ExternalSecretManifest)
    assert message.manifest.apiVersion == "external-secrets.io/v1"
    assert message.manifest.kind == "ExternalSecret"
    assert message.manifest.metadata.name == mock_secret.name
    assert message.manifest.metadata.namespace == mock_project.name
    assert message.manifest.metadata.labels[PROJECT_SECRET_ID_LABEL] == str(mock_secret.id)
    assert message.manifest.metadata.labels[PROJECT_SECRET_SCOPE_LABEL] == "project"
    assert message.secret_type == SecretKind.EXTERNAL_SECRET


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

    # Create Pydantic manifest model
    manifest_model = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1",
        kind="ExternalSecret",
        metadata=KubernetesMetadata(name="org-secret"),
        spec={"secretStoreRef": {"name": "vault-backend"}},
    )

    mock_sender = AsyncMock()
    await publish_project_secret_creation_message(
        mock_assignment, manifest_model, mock_sender, parent_secret=mock_parent_secret
    )

    mock_sender.enqueue.assert_called_once()
    call_args = mock_sender.enqueue.call_args
    assert call_args[0][0] == mock_project.cluster_id

    message = call_args[0][1]
    assert message.message_type == "project_secrets_create"
    assert isinstance(message.manifest, ExternalSecretManifest)
    assert message.manifest.apiVersion == "external-secrets.io/v1"
    assert message.manifest.kind == "ExternalSecret"
    assert message.manifest.metadata.name == mock_parent_secret.name
    assert message.manifest.metadata.namespace == mock_project.name
    assert message.manifest.metadata.labels[PROJECT_SECRET_ID_LABEL] == str(mock_assignment.id)
    assert message.manifest.metadata.labels[PROJECT_SECRET_SCOPE_LABEL] == "organization"
    assert message.secret_type == SecretKind.EXTERNAL_SECRET


@pytest.mark.asyncio
async def test_publish_project_secret_creation_message_patches_missing_scope_label():
    """Legacy manifests without a scope label get patched before publishing."""
    mock_project = Mock()
    mock_project.cluster_id = uuid4()
    mock_project.name = "test-project"

    mock_assignment = Mock()
    mock_assignment.id = uuid4()
    mock_assignment.project = mock_project

    mock_parent_secret = Mock()
    mock_parent_secret.name = "legacy-secret"
    mock_parent_secret.type = SecretKind.EXTERNAL_SECRET

    manifest_model = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1beta1",
        kind="ExternalSecret",
        metadata=KubernetesMetadata(name="legacy-secret"),
        spec={"secretStoreRef": {"name": "vault-backend"}},
    )
    assert manifest_model.metadata.labels is None

    mock_sender = AsyncMock()
    await publish_project_secret_creation_message(
        mock_assignment, manifest_model, mock_sender, parent_secret=mock_parent_secret
    )

    message = mock_sender.enqueue.call_args[0][1]
    assert message.manifest.metadata.labels[PROJECT_SECRET_SCOPE_LABEL] == "organization"


@pytest.mark.asyncio
async def test_publish_project_secret_creation_message_preserves_existing_scope_label():
    """Manifests that already have a scope label should not be overwritten.

    The label is set to "project" but a parent_secret is provided, so the
    inferred scope would be "organization". The guard must prevent overwriting.
    """
    mock_project = Mock()
    mock_project.cluster_id = uuid4()
    mock_project.name = "test-project"

    mock_assignment = Mock()
    mock_assignment.id = uuid4()
    mock_assignment.project = mock_project

    mock_parent_secret = Mock()
    mock_parent_secret.name = "org-secret"
    mock_parent_secret.type = SecretKind.EXTERNAL_SECRET

    manifest_model = ExternalSecretManifest(
        apiVersion="external-secrets.io/v1beta1",
        kind="ExternalSecret",
        metadata=KubernetesMetadata(
            name="test-secret",
            labels={PROJECT_SECRET_SCOPE_LABEL: "project"},
        ),
        spec={"secretStoreRef": {"name": "vault-backend"}},
    )

    mock_sender = AsyncMock()
    await publish_project_secret_creation_message(
        mock_assignment, manifest_model, mock_sender, parent_secret=mock_parent_secret
    )

    message = mock_sender.enqueue.call_args[0][1]
    assert message.manifest.metadata.labels[PROJECT_SECRET_SCOPE_LABEL] == "project"


def test_build_project_secret_response_filters_by_project():
    """Test that only assignments for the specified project are returned."""

    # Create target project and another project
    target_project = Mock(spec=Project)
    target_project.id = uuid4()
    target_project.name = "target-project"
    target_project.description = "Target project description"
    target_project.cluster_id = uuid4()
    target_project.status = ProjectStatus.READY.value
    target_project.status_reason = None
    target_project.created_at = datetime.now(UTC)
    target_project.updated_at = datetime.now(UTC)
    target_project.created_by = "user@test.com"
    target_project.updated_by = "user@test.com"

    other_project = Mock(spec=Project)
    other_project.id = uuid4()
    other_project.name = "other-project"
    other_project.description = "Other project description"
    other_project.cluster_id = uuid4()
    other_project.status = ProjectStatus.READY.value
    other_project.status_reason = None
    other_project.created_at = datetime.now(UTC)
    other_project.updated_at = datetime.now(UTC)
    other_project.created_by = "user@test.com"
    other_project.updated_by = "user@test.com"

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
    other_assignment.project = other_project.id
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
    assert len(result.data) == 1
    assert result.data[0].id == target_assignment.id
    assert result.data[0].project.id == target_project.id
    assert result.data[0].project.name == target_project.name


# Dummy constants for testing
DUMMY_API_GROUP = "external-secrets.io"
DUMMY_KIND = "ExternalSecret"
DUMMY_VERSION = "v1beta1"
DUMMY_SECRET_ID = str(uuid4())


@pytest.fixture(autouse=True)
def patch_constants(monkeypatch):
    monkeypatch.setattr(secrets_constants, "EXTERNAL_SECRETS_API_GROUP", DUMMY_API_GROUP)
    monkeypatch.setattr(secrets_constants, "EXTERNAL_SECRETS_KIND", DUMMY_KIND)


def test_validate_external_secret_manifest_valid():
    manifest = {
        "apiVersion": f"{DUMMY_API_GROUP}/{DUMMY_VERSION}",
        "kind": DUMMY_KIND,
        "metadata": {"name": "foo", "namespace": "bar", "labels": {PROJECT_SECRET_ID_LABEL: DUMMY_SECRET_ID}},
        "spec": {"data": [{"secretKey": "foo", "remoteRef": {"key": "bar"}}]},
    }
    manifest_yaml = yaml.safe_dump(manifest)

    # Should successfully validate and return a Pydantic model
    result = packgeUtils.validate_external_secret_manifest(manifest_yaml)
    assert isinstance(result, ExternalSecretManifest)
    assert result.apiVersion == f"{DUMMY_API_GROUP}/{DUMMY_VERSION}"
    assert result.kind == DUMMY_KIND


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
    assert isinstance(result, ExternalSecretManifest)
    assert result.apiVersion == f"{DUMMY_API_GROUP}/{DUMMY_VERSION}"
    assert result.kind == DUMMY_KIND


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
    assert isinstance(result, KubernetesSecretManifest)
    assert result.apiVersion == "v1"
    assert result.kind == "Secret"


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
