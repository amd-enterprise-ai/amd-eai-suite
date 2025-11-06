# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ConfigMapStatus, ProjectStorageStatus
from app.storages.enums import StorageStatus, StorageType
from app.storages.models import ProjectStorage, Storage
from app.storages.repository import (
    create_project_storage,
    create_project_storage_configmap,
    create_storage,
    delete_project_storage,
    delete_storage,
    get_configmap_by_project_storage_id,
    get_project_storage,
    get_project_storage_by_id,
    get_project_storages_by_project_ids_secret,
    get_project_storages_by_project_secret,
    get_storage_by_secret_id,
    get_storage_in_organization,
    get_storages_in_organization,
    update_project_storage_configmap_status,
    update_storage_status,
)
from app.storages.schemas import S3Spec, StorageIn
from app.utilities.exceptions import ConflictException
from tests import factory


@pytest.mark.asyncio
async def test_get_storages_in_organization_returns_secrets_with_projects(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        storage_status=StorageStatus.SYNCED.value,
    )

    storages = await get_storages_in_organization(db_session, env.organization.id)

    assert len(storages) == 1
    assert storages[0].organization_id == env.organization.id
    assert storages[0].project_storages[0].project.name == "test-project"


@pytest.mark.asyncio
async def test_get_storages_in_organization_returns_storage_with_project_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        storage_status=StorageStatus.SYNCED.value,
    )

    storages = await get_storages_in_organization(db_session, env.organization.id, project_id=env.project.id)

    assert len(storages) == 1
    assert storages[0].organization_id == env.organization.id
    assert storages[0].project_storages[0].project.name == "test-project"


@pytest.mark.asyncio
async def test_get_storages_in_organization_no_project_storages_found(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        storage_status=StorageStatus.SYNCED.value,
    )

    storages = await get_storages_in_organization(
        db_session, env.organization.id, project_id=UUID("bde8d859-609d-4186-9486-6c93732b2e99")
    )

    assert len(storages) == 0


@pytest.mark.asyncio
async def test_create_storage(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    creator = "test-user@example.com"
    storage_status = StorageStatus.UNASSIGNED.value

    storage_in = StorageIn(
        name="test-storage",
        type=StorageType.S3,
        scope="Organization",
        secret_id=str(secret.id),
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        project_ids=[],
        description="test storage",
    )

    result = await create_storage(
        session=db_session,
        organization_id=env.organization.id,
        storage_in=storage_in,
        storage_status=storage_status,
        creator=creator,
    )

    assert isinstance(result, Storage)
    assert result.name == "test-storage"
    assert result.organization_id == env.organization.id
    assert result.status == storage_status
    assert result.created_by == creator
    assert result.updated_by == creator


@pytest.mark.asyncio
async def test_create_storage_duplicate_name_conflict(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    creator = "test-user@example.com"

    # Create first storage
    storage_in = StorageIn(
        name="duplicate-storage",
        type=StorageType.S3,
        scope="Organization",
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        secret_id=str(secret.id),
        project_ids=[],
        description="first storage",
    )

    await create_storage(
        session=db_session,
        organization_id=env.organization.id,
        storage_in=storage_in,
        storage_status=StorageStatus.UNASSIGNED.value,
        creator=creator,
    )

    # Try to create second storage with same name - should raise ConflictException
    storage_in_duplicate = storage_in.model_copy(update={"description": "duplicate storage"})

    with pytest.raises(ConflictException, match="already exists") as exc_info:
        await create_storage(
            session=db_session,
            organization_id=env.organization.id,
            storage_in=storage_in_duplicate,
            storage_status=StorageStatus.UNASSIGNED.value,
            creator=creator,
        )

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_storage_with_generic_integrity_error(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    creator = "test-user@example.com"
    storage_status = StorageStatus.UNASSIGNED.value

    storage_in = StorageIn(
        name="test-secret-generic-error",
        type=StorageType.S3,
        scope="Organization",
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        secret_id=str(secret.id),
        project_ids=[],
        description="test storage",
    )

    async def mock_flush():
        raise IntegrityError("Generic constraint violation", None, None)

    with patch.object(db_session, "flush", side_effect=mock_flush):
        with pytest.raises(IntegrityError) as exc_info:
            await create_storage(
                session=db_session,
                organization_id=env.organization.id,
                storage_in=storage_in,
                storage_status=storage_status,
                creator=creator,
            )

    assert "Generic constraint violation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_project_storage_configmap_sets_status_and_links(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    # Create a project storage to attach the configmap to
    project_secret = await factory.create_project_secret(db_session, env.project, secret)

    ps = await create_project_storage(
        session=db_session,
        storage_id=storage.id,
        project_id=env.project.id,
        user_email="tester@example.com",
    )

    cm = await create_project_storage_configmap(
        session=db_session,
        project_storage_id=ps.id,
        user_email="tester@example.com",
    )
    assert cm.project_storage_id == ps.id
    assert cm.status == ConfigMapStatus.ADDED


@pytest.mark.asyncio
async def test_get_storage_in_organization(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.DELETING.value
    )

    result = await get_storage_in_organization(db_session, env.organization.id, storage.id)

    assert result.id == storage.id


@pytest.mark.asyncio
async def test_update_storage_status(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.DELETING.value
    )

    await update_storage_status(
        db_session, storage, ProjectStorageStatus.PENDING, "Updating Storage", "admin@example.com"
    )

    assert storage.status == "Pending"
    assert storage.status_reason == "Updating Storage"


@pytest.mark.asyncio
async def test_delete_storage(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.DELETING.value
    )

    await delete_storage(db_session, storage)

    assert await get_storage_in_organization(db_session, env.organization.id, storage.id) is None


@pytest.mark.asyncio
async def test_get_project_storage_found(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        storage_status=StorageStatus.SYNCED.value,
    )

    result = await get_project_storage(db_session, storage.id, env.project.id)
    assert result.project.name == "test-project"


@pytest.mark.asyncio
async def test_get_project_storage_not_found(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.DELETING.value
    )

    result = await get_project_storage(db_session, storage.id, env.project.id)
    assert result is None


@pytest.mark.asyncio
async def test_delete_project_storage(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        storage_status=StorageStatus.SYNCED.value,
    )

    # Verify the storage has exactly one project_storage assigned
    # Ensure relationship is loaded in an async-safe way BEFORE accessing it
    await db_session.refresh(storage, attribute_names=["project_storages"])
    assert len(storage.project_storages) == 1

    # Fetch the ProjectStorage object we’re about to delete
    project_storage = await get_project_storage(db_session, storage.id, env.project.id)
    assert project_storage is not None

    await delete_project_storage(db_session, project_storage)
    assert await get_project_storage(db_session, storage.id, env.project.id) is None

    # Assert: The cached relationship on the storage object should now reload from DB
    # (it should reflect the empty list after the expire() call)
    updated_storage = await get_storage_in_organization(db_session, env.organization.id, storage.id)
    assert len(updated_storage.project_storages) == 0


@pytest.mark.asyncio
async def test_update_project_storage_configmap_status(db_session: AsyncSession):
    # Setup
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    # Get the project_storage and create a configmap
    project_storage = await get_project_storage(db_session, storage.id, env.project.id)
    configmap = await create_project_storage_configmap(
        session=db_session,
        project_storage_id=project_storage.id,
        user_email="tester@example.com",
    )

    # Update the configmap status
    new_status = ConfigMapStatus.DELETED
    status_reason = "Test status update"
    await update_project_storage_configmap_status(db_session, configmap, new_status, status_reason, "admin@example.com")

    # Verify
    assert configmap.status == new_status
    assert configmap.status_reason == status_reason
    assert configmap.updated_by == "admin@example.com"


@pytest.mark.asyncio
async def test_get_configmap_by_project_storage_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)

    result = await get_configmap_by_project_storage_id(db_session, env.organization.id, project_storage.id)

    assert result is not None
    assert result.project_storage_id == project_storage.id

    wrong_org_id = UUID("bde8d859-609d-4186-9486-6c93732b2e99")
    no_result = await get_configmap_by_project_storage_id(db_session, wrong_org_id, project_storage.id)
    assert no_result is None


@pytest.mark.asyncio
async def test_get_storage_by_secret_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.SYNCED.value
    )

    result = await get_storage_by_secret_id(db_session, secret.id)

    assert result is not None
    assert result.id == storage.id
    assert result.secret_id == secret.id


@pytest.mark.asyncio
async def test_get_project_storage_by_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)

    result = await get_project_storage_by_id(db_session, project_storage.id)

    assert result is not None
    assert result.id == project_storage.id
    assert result.storage is not None
    assert result.storage.id == storage.id


@pytest.mark.asyncio
async def test_get_project_storages_by_project_secret(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_secret = await factory.create_project_secret(db_session, env.project, secret)

    result = await get_project_storages_by_project_secret(db_session, project_secret)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].project_id == project_secret.project_id
    assert result[0].storage.secret_id == project_secret.secret_id

    other_secret = await factory.create_secret(db_session, env.organization, name="other-secret")
    other_project_secret = await factory.create_project_secret(db_session, env.project, other_secret)

    no_result = await get_project_storages_by_project_secret(db_session, other_project_secret)
    assert no_result == []


@pytest.mark.asyncio
async def test_get_project_storages_by_project_ids_empty_list_returns_empty(db_session: AsyncSession):
    """Given an empty list, return an empty list"""
    res = await get_project_storages_by_project_ids_secret(db_session, [], uuid4())
    assert res == []


@pytest.mark.asyncio
async def test_get_project_storages_using_secret__filters_correctly(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    p1 = await factory.create_project(db_session, env.organization, env.cluster, name="p1")
    p2 = await factory.create_project(db_session, env.organization, env.cluster, name="p2")
    p3 = await factory.create_project(db_session, env.organization, env.cluster, name="p3")

    # Secret & Storage (linked to same org)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session,
        env.organization,
        secret_id=secret.id,
        name="s1",
    )

    # Link storages to projects
    await factory.create_project_storage(db_session, project=p1, storage=storage)
    await factory.create_project_storage(db_session, project=p2, storage=storage)
    await factory.create_project_storage(db_session, project=p3, storage=storage)  # control

    # Act: filter to p1/p2 and secret.id (NOT storage.id)
    results = await get_project_storages_by_project_ids_secret(db_session, [p1.id, p2.id], secret.id)

    # Assert
    assert isinstance(results, list)
    assert {ps.project_id for ps in results} == {p1.id, p2.id}
    assert all(isinstance(ps, ProjectStorage) for ps in results)
    # storage relationship should be eager-loaded; accessing .storage.id should not lazy-load
    assert {ps.storage.id for ps in results} == {storage.id}


@pytest.mark.asyncio
async def test_get_project_storages_by_project_ids_includes_only_existing_matches(db_session):
    env = await factory.create_basic_test_environment(db_session)

    p1 = await factory.create_project(db_session, env.organization, env.cluster, name="p1")

    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session,
        env.organization,
        secret_id=secret.id,
        name="s1",
    )

    await factory.create_project_storage(db_session, project=p1, storage=storage)

    not_found_project_id = uuid4()

    results = await get_project_storages_by_project_ids_secret(db_session, [p1.id, not_found_project_id], secret.id)
    assert [ps.project_id for ps in results] == [p1.id]
    assert results[0].storage.id == storage.id
