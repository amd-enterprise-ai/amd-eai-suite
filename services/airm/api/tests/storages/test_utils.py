# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ConfigMapStatus, ProjectSecretStatus, ProjectStorageStatus
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.secrets.models import OrganizationSecretAssignment
from app.storages.enums import StorageStatus
from app.storages.models import ProjectStorage, ProjectStorageConfigmap
from app.storages.utils import resolve_project_storage_composite_status, resolve_storage_status, verify_projects_ready
from app.utilities.exceptions import ValidationException
from tests import factory


@pytest.mark.asyncio
async def test_verify_projects_ready_no_ids_returns_ok(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    # Should not raise when list is empty
    await verify_projects_ready(db_session, env.organization.id, [])


@pytest.mark.asyncio
async def test_verify_projects_ready_all_ready_ok(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    # Create two READY projects in the same org
    p1 = await factory.create_project(
        db_session, env.organization, env.cluster, name="p1", project_status=ProjectStatus.READY.value
    )
    p2 = await factory.create_project(
        db_session, env.organization, env.cluster, name="p2", project_status=ProjectStatus.READY.value
    )

    # Should not raise
    await verify_projects_ready(db_session, env.organization.id, [p1.id, p2.id])


@pytest.mark.asyncio
async def test_verify_projects_ready_missing_project_raises(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    missing_id = uuid4()

    with pytest.raises(ValidationException, match=f"project id={missing_id} not found"):
        await verify_projects_ready(db_session, env.organization.id, [missing_id])


@pytest.mark.asyncio
async def test_verify_projects_ready_not_ready_raises(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    # Create a project that is NOT READY
    p = await factory.create_project(
        db_session, env.organization, env.cluster, name="p-not-ready", project_status=ProjectStatus.PENDING.value
    )

    with pytest.raises(ValidationException, match=f"project id={p.id} not READY"):
        await verify_projects_ready(db_session, env.organization.id, [p.id])


@pytest.mark.asyncio
async def test_verify_projects_ready_stops_at_first_failure_missing_then_not_ready(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    ok = await factory.create_project(
        db_session, env.organization, env.cluster, name="ok", project_status=ProjectStatus.READY.value
    )
    missing_id = uuid4()
    not_ready = await factory.create_project(
        db_session, env.organization, env.cluster, name="nr", project_status=ProjectStatus.PENDING.value
    )

    with pytest.raises(ValidationException, match=f"project id={missing_id} not found"):
        await verify_projects_ready(db_session, env.organization.id, [ok.id, missing_id, not_ready.id])


@pytest.mark.parametrize(
    "configmap_status,configmap_reason,secret_status,secret_reason,expected_status,expected_reason_parts",
    [
        # Both FAILED
        (
            ConfigMapStatus.FAILED,
            "ConfigMap failed",
            ProjectSecretStatus.FAILED,
            "Secret failed",
            ProjectStorageStatus.FAILED,
            ["Failed components: configmap, secret", "configmap: ConfigMap failed", "secret: Secret failed"],
        ),
        # Configmap FAILED, secret SYNCED
        (
            ConfigMapStatus.FAILED,
            "ConfigMap failed",
            ProjectSecretStatus.SYNCED,
            "Secret synced",
            ProjectStorageStatus.FAILED,
            ["Failed components: configmap", "configmap: ConfigMap failed", "secret: Secret synced"],
        ),
        # Secret FAILED, configmap ADDED
        (
            ConfigMapStatus.ADDED,
            "ConfigMap added",
            ProjectSecretStatus.FAILED,
            "Secret failed",
            ProjectStorageStatus.FAILED,
            ["Failed components: secret", "configmap: ConfigMap added", "secret: Secret failed"],
        ),
        # Both SYNCED
        (
            ConfigMapStatus.ADDED,
            "ConfigMap added",
            ProjectSecretStatus.SYNCED,
            "Secret synced",
            ProjectStorageStatus.SYNCED,
            ["All components synced", "configmap: ConfigMap added", "secret: Secret synced"],
        ),
        # PENDING
        (
            ConfigMapStatus.ADDED,
            "ConfigMap added",
            ProjectSecretStatus.PENDING,
            "Secret pending",
            ProjectStorageStatus.PENDING,
            ["Project secret pending", "configmap: ConfigMap added", "secret: Secret pending"],
        ),
        # Unknown states
        (
            "UNKNOWN",
            "Unknown configmap state",
            "UNKNOWN",
            "Unknown secret state",
            ProjectStorageStatus.FAILED,
            ["Unknown component states detected", "configmap: Unknown configmap state", "secret: Unknown secret state"],
        ),
        # No reasons
        (
            ConfigMapStatus.FAILED,
            None,
            ProjectSecretStatus.FAILED,
            None,
            ProjectStorageStatus.FAILED,
            ["Failed components: configmap, secret"],
        ),
    ],
)
@pytest.mark.asyncio
async def test_resolve_project_storage_composite_status(
    configmap_status,
    configmap_reason,
    secret_status,
    secret_reason,
    expected_status,
    expected_reason_parts,
    db_session: AsyncSession,
):
    """Test resolve_project_storage_composite_status with various component states."""
    # Create mock objects using actual model instances
    configmap = ProjectStorageConfigmap(
        id=uuid4(),
        project_storage_id=uuid4(),
        status=configmap_status,
        status_reason=configmap_reason,
        created_by="test",
        updated_by="test",
    )

    organization_secret_assignment = OrganizationSecretAssignment(
        id=uuid4(),
        project_id=uuid4(),
        organization_secret_id=uuid4(),
        status=secret_status,
        status_reason=secret_reason,
        created_by="test",
        updated_by="test",
    )

    project_storage = ProjectStorage(
        id=uuid4(), project_id=uuid4(), storage_id=uuid4(), status="PENDING", created_by="test", updated_by="test"
    )

    status, reason = await resolve_project_storage_composite_status(configmap, organization_secret_assignment)

    assert status == expected_status
    for part in expected_reason_parts:
        assert part in reason


@pytest.mark.parametrize(
    "prev_status,project_storage_statuses,expected_status,expected_reason",
    [
        # No project secrets → UNASSIGNED
        (StorageStatus.SYNCED, [], StorageStatus.UNASSIGNED, None),
        # DELETING: all project secrets deleted → DELETED
        (StorageStatus.DELETING, [], StorageStatus.DELETED, None),
        # DELETING: one delete failed → DELETE_FAILED
        (
            StorageStatus.DELETING,
            [ProjectSecretStatus.DELETE_FAILED],
            StorageStatus.DELETE_FAILED,
            "Some project storages failed to be deleted",
        ),
        # DELETING: not all deleted or failed → DELETING
        (
            StorageStatus.DELETING,
            [ProjectStorageStatus.SYNCED, ProjectStorageStatus.PENDING],
            StorageStatus.DELETING,
            None,
        ),
        # All DELETED (not deleting) → UNASSIGNED
        (StorageStatus.SYNCED, [], StorageStatus.UNASSIGNED, None),
        # Any DELETE_FAILED → DELETE_FAILED
        (
            StorageStatus.SYNCED,
            [ProjectStorageStatus.SYNCED, ProjectStorageStatus.DELETE_FAILED],
            StorageStatus.DELETE_FAILED,
            "Some project storages failed to be deleted",
        ),
        # Any FAILED → FAILED
        (
            StorageStatus.SYNCED,
            [ProjectStorageStatus.FAILED, ProjectStorageStatus.SYNCED],
            StorageStatus.FAILED,
            "Some project storages are in a failed state",
        ),
        # Any SYNCED_ERROR or UNKNOWN → SYNCED_ERROR
        (
            StorageStatus.SYNCED,
            [ProjectStorageStatus.SYNCED_ERROR, ProjectStorageStatus.SYNCED],
            StorageStatus.SYNCED_ERROR,
            "Some project storages have failed to sync",
        ),
        (
            StorageStatus.SYNCED,
            [ProjectStorageStatus.UNKNOWN, ProjectStorageStatus.SYNCED],
            StorageStatus.SYNCED_ERROR,
            "Some project storages have failed to sync",
        ),
        # All SYNCED → SYNCED
        (
            StorageStatus.PARTIALLY_SYNCED,
            [ProjectStorageStatus.SYNCED, ProjectStorageStatus.SYNCED],
            StorageStatus.SYNCED,
            None,
        ),
        # Some DELETED -> SYNCED_ERROR
        (
            StorageStatus.SYNCED,
            [ProjectStorageStatus.DELETED, "UNKNOWN", ProjectStorageStatus.SYNCED, "UNKNOWN"],
            StorageStatus.SYNCED_ERROR,
            "One or more project storages have been deleted unexpectedly.",
        ),
        # Some SYNCED → PARTIALLY_SYNCED
        (
            StorageStatus.UNASSIGNED,
            [ProjectStorageStatus.SYNCED, ProjectStorageStatus.PENDING],
            StorageStatus.PARTIALLY_SYNCED,
            None,
        ),
        # Fallback: no rule matched → SYNCED_ERROR
        (
            StorageStatus.SYNCED,
            [ProjectStorageStatus.PENDING, "UNKNOWN"],
            StorageStatus.SYNCED_ERROR,
            "Unknown Project storage states detected.",
        ),
    ],
)
def test_resolve_storage_status(prev_status, project_storage_statuses, expected_status, expected_reason):
    project = Project(name="project-1")
    project_storages = [ProjectStorage(status=s, project=project) for s in project_storage_statuses]
    status, status_reason = resolve_storage_status(prev_status, project_storages)
    assert status == expected_status
    assert expected_reason == status_reason
