# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock

from airm.messaging.schemas import NamespaceStatus, QuotaStatus
from app.projects.enums import ProjectStatus
from app.projects.utils import resolve_project_status


async def test_resolve_project_status_deleting():
    """Test that project in DELETING status remains DELETING regardless of component states."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.ACTIVE
    namespace.status_reason = None

    quota = MagicMock()
    quota.status = QuotaStatus.READY
    quota.status_reason = None

    project = MagicMock()
    project.status = ProjectStatus.DELETING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.DELETING
    assert reason == "Project is being deleted."


def test_resolve_project_status_all_ready():
    """Test that project is READY when all components are ready/active."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.ACTIVE
    namespace.status_reason = "Namespace ready"

    quota = MagicMock()
    quota.status = QuotaStatus.READY
    quota.status_reason = "Quota allocated"

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.READY
    assert "All components ready" in reason
    assert "namespace: Namespace ready" in reason
    assert "quota: Quota allocated" in reason


def test_resolve_project_status_all_pending():
    """Test that project is PENDING when all components are pending."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.PENDING
    namespace.status_reason = "Creating namespace"

    quota = MagicMock()
    quota.status = QuotaStatus.PENDING
    quota.status_reason = "Allocating quota"

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.PENDING
    assert "All components pending" in reason
    assert "namespace: Creating namespace" in reason
    assert "quota: Allocating quota" in reason


def test_resolve_project_status_namespace_failed():
    """Test that project is FAILED when namespace fails."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.FAILED
    namespace.status_reason = "Failed to create namespace"

    quota = MagicMock()
    quota.status = QuotaStatus.READY
    quota.status_reason = None

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.FAILED
    assert "Failed components: namespace" in reason
    assert "namespace: Failed to create namespace" in reason


def test_resolve_project_status_quota_failed():
    """Test that project is FAILED when quota fails."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.ACTIVE
    namespace.status_reason = None

    quota = MagicMock()
    quota.status = QuotaStatus.FAILED
    quota.status_reason = "Insufficient resources"

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.FAILED
    assert "Failed components: quota" in reason
    assert "quota: Insufficient resources" in reason


def test_resolve_project_status_both_failed():
    """Test that project is FAILED when both components fail."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.FAILED
    namespace.status_reason = "Network error"

    quota = MagicMock()
    quota.status = QuotaStatus.FAILED
    quota.status_reason = "Resource limit exceeded"

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.FAILED
    assert "Failed components: namespace, quota" in reason
    assert "namespace: Network error" in reason
    assert "quota: Resource limit exceeded" in reason


def test_resolve_project_status_mixed_namespace_ready_quota_pending():
    """Test PARTIALLY_READY when namespace is active but quota is pending."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.ACTIVE
    namespace.status_reason = "Namespace created"

    quota = MagicMock()
    quota.status = QuotaStatus.PENDING
    quota.status_reason = "Waiting for approval"

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.PARTIALLY_READY
    assert "Ready: namespace" in reason
    assert "Pending: quota" in reason
    assert "namespace: Namespace created" in reason
    assert "quota: Waiting for approval" in reason


def test_resolve_project_status_mixed_namespace_pending_quota_ready():
    """Test PARTIALLY_READY when namespace is pending but quota is ready."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.PENDING
    namespace.status_reason = "Initializing"

    quota = MagicMock()
    quota.status = QuotaStatus.READY
    quota.status_reason = "Quota assigned"

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.PARTIALLY_READY
    assert "Ready: quota" in reason
    assert "Pending: namespace" in reason
    assert "namespace: Initializing" in reason
    assert "quota: Quota assigned" in reason


def test_resolve_project_status_no_reason_text():
    """Test that function works correctly when components have no status_reason."""
    namespace = MagicMock()
    namespace.status = NamespaceStatus.ACTIVE
    namespace.status_reason = None

    quota = MagicMock()
    quota.status = QuotaStatus.READY
    quota.status_reason = None

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.READY
    assert reason == "All components ready. "


def test_resolve_project_status_unknown_state():
    """Test that unknown component states result in FAILED status."""
    namespace = MagicMock()
    namespace.status = "UNKNOWN_STATUS"  # Simulate unexpected state
    namespace.status_reason = "Unexpected error"

    quota = MagicMock()
    quota.status = QuotaStatus.READY
    quota.status_reason = None

    project = MagicMock()
    project.status = ProjectStatus.PENDING

    status, reason = resolve_project_status(namespace, quota, project)

    assert status == ProjectStatus.FAILED
    assert "Unknown component states detected" in reason
    assert "namespace: Unexpected error" in reason
