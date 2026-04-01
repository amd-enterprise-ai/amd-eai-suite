# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Database test data factories for creating real entities with proper relationships.

This module provides factory functions that create real database entities
for use in repository-level tests, replacing inline object creation patterns
and test_environment fixtures.

## Automatic Isolation Testing
"""

from datetime import UTC, datetime
from typing import NamedTuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.clusters.models import Cluster, ClusterNode
from app.messaging.schemas import (
    ConfigMapStatus,
    GPUVendor,
    NamespaceStatus,
    ProjectSecretStatus,
    ProjectStorageStatus,
    QuotaStatus,
    SecretKind,
    SecretScope,
    WorkloadComponentKind,
)
from app.namespaces.models import Namespace
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.quotas.models import Quota
from app.secrets.enums import SecretStatus, SecretUseCase
from app.secrets.models import OrganizationScopedSecret, OrganizationSecretAssignment, ProjectScopedSecret, Secret
from app.storages.enums import StorageScope, StorageStatus, StorageType
from app.storages.models import ProjectStorage, ProjectStorageConfigmap, Storage
from app.users.models import User
from app.workloads.enums import WorkloadType
from app.workloads.models import Workload, WorkloadComponent, WorkloadTimeSummary


class TestEnvironment(NamedTuple):
    """Container for standard test environment entities."""

    cluster: Cluster
    project: Project
    creator: str


class ExtendedTestEnvironment(NamedTuple):
    """Container for extended test environment with additional entities."""

    cluster: Cluster
    project: Project
    user: User
    creator: str = "test@example.com"


class ComplexTestEnvironment(NamedTuple):
    """Container for complex test scenarios with configurable entities."""

    cluster: Cluster
    accessible_projects: list[Project]
    users: list[User]
    project_memberships: dict[UUID, list[User]]  # project_id -> users (for test tracking only, not in DB)
    quotas: list[Quota]
    creator: str


async def create_cluster(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "test-cluster",
    creator: str = "test@example.com",
    workloads_base_url: str = "https://example.com",
    kube_api_url: str = "https://k8s.example.com:6443",
) -> Cluster:
    """Create a test cluster."""
    cluster = Cluster(
        id=id or uuid4(),
        name=name,
        created_by=creator,
        updated_by=creator,
        workloads_base_url=workloads_base_url,
        kube_api_url=kube_api_url,
    )
    session.add(cluster)
    await session.flush()
    return cluster


async def create_cluster_node(
    session: AsyncSession,
    cluster: Cluster,
    *,
    id: UUID | None = None,
    name: str = "test-node",
    cpu_milli_cores: int = 4000,
    memory_bytes: int = 8 * 1024**3,  # 8GB
    ephemeral_storage_bytes: int = 10 * 1024**3,  # 10GB
    gpu_count: int = 1,
    gpu_type: str | None = "74a0",
    gpu_vendor: GPUVendor | None = GPUVendor.AMD,
    gpu_vram_bytes_per_device: int | None = 8 * 1024**3,  # 8GB
    gpu_product_name: str | None = "Instinct MI300A",
    status: str = "Ready",
    is_ready: bool = True,
    creator: str = "test@example.com",
) -> ClusterNode:
    """Create a test cluster node associated with a cluster."""
    node = ClusterNode(
        id=id or uuid4(),
        cluster_id=cluster.id,
        name=name,
        cpu_milli_cores=cpu_milli_cores,
        memory_bytes=memory_bytes,
        ephemeral_storage_bytes=ephemeral_storage_bytes,
        gpu_count=gpu_count,
        gpu_type=gpu_type,
        gpu_vendor=gpu_vendor,
        gpu_vram_bytes_per_device=gpu_vram_bytes_per_device,
        gpu_product_name=gpu_product_name,
        status=status,
        is_ready=is_ready,
        created_by=creator,
        updated_by=creator,
    )
    session.add(node)
    await session.flush()
    return node


async def create_project(
    session: AsyncSession,
    cluster: Cluster,
    *,
    id: UUID | None = None,
    name: str = "test-project",
    project_status: str = ProjectStatus.PENDING.value,
    description: str = "Test project description",
    creator: str = "test@example.com",
    keycloak_group_id: str | None = None,
) -> Project:
    """Create a test project associated with cluster."""
    project = Project(
        id=id or uuid4(),
        name=name,
        description=description,
        cluster_id=cluster.id,
        created_by=creator,
        updated_by=creator,
        status=project_status,
        status_reason="Project is being created.",
        keycloak_group_id=keycloak_group_id or str(uuid4()),
    )
    session.add(project)
    await session.flush()
    return project


async def create_namespace(
    session: AsyncSession,
    cluster: Cluster,
    project: Project | None = None,
    *,
    id: UUID | None = None,
    name: str | None = None,
    project_id: UUID | None = None,
    status: str | NamespaceStatus = "Active",
    status_reason: str | None = None,
    creator: str = "test@example.com",
) -> Namespace:
    """Create a test namespace.

    Can accept either a project object or project_id. If both are provided, project takes precedence.
    """
    # Determine the actual project_id to use
    actual_project_id = project.id if project else project_id

    # Handle status - convert string to NamespaceStatus if needed
    if isinstance(status, str):
        namespace_status = NamespaceStatus(status)
    else:
        namespace_status = status or NamespaceStatus.ACTIVE

    now = datetime.now(UTC)
    namespace = Namespace(
        id=id or uuid4(),
        name=name or (project.name if project else "my-namespace"),
        cluster_id=cluster.id,
        project_id=actual_project_id,
        status=namespace_status,
        status_reason=status_reason,
        created_by=creator,
        updated_by=creator,
        created_at=now,
        updated_at=now,
    )
    session.add(namespace)
    await session.flush()
    return namespace


async def create_user(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    email: str = "test@example.com",
    keycloak_user_id: str | None = None,
    invited_by: str = "admin@example.com",
    invited_at: datetime | None = None,
    last_active_at: datetime | None = None,
) -> User:
    """Create a test user."""
    now = datetime.now(UTC)
    user = User(
        id=id or uuid4(),
        email=email,
        keycloak_user_id=keycloak_user_id or str(uuid4()),
        invited_at=invited_at or now,
        invited_by=invited_by,
        last_active_at=last_active_at or now,
        created_by=invited_by,
        updated_by=invited_by,
    )
    session.add(user)
    await session.flush()
    return user


async def create_quota(
    session: AsyncSession,
    cluster: Cluster,
    project: Project,
    *,
    id: UUID | None = None,
    cpu_milli_cores: int = 1000,
    memory_bytes: int = 1024**3,  # 1GB
    ephemeral_storage_bytes: int = 5 * 1024**3,  # 5GB
    gpu_count: int = 0,
    description: str = "Test quota",
    status: QuotaStatus = QuotaStatus.READY,
    updated_at: datetime | None = None,
    creator: str = "test@example.com",
) -> Quota:
    """Create a test quota for a cluster."""
    quota = Quota(
        id=id or uuid4(),
        project_id=project.id,
        cluster_id=cluster.id,
        cpu_milli_cores=cpu_milli_cores,
        memory_bytes=memory_bytes,
        ephemeral_storage_bytes=ephemeral_storage_bytes,
        gpu_count=gpu_count,
        status=status,
        created_by=creator,
        updated_by=creator,
    )
    if updated_at:
        quota.updated_at = updated_at
    session.add(quota)
    await session.flush()
    return quota


async def create_project_with_quota(
    session: AsyncSession,
    cluster: Cluster,
    *,
    project_id: UUID | None = None,
    project_name: str = "test-project",
    quota_cpu: int = 1000,
    quota_memory: int = 1024**3,
    quota_storage: int = 5 * 1024**3,
    quota_gpu: int = 0,
    quota_status: QuotaStatus = QuotaStatus.READY,
    quota_updated_at: datetime | None = None,
    creator: str = "test@example.com",
    keycloak_group_id: str | None = None,
) -> tuple[Project, Quota]:
    """Create a project with an associated quota."""
    project = await create_project(
        session,
        cluster,
        id=project_id,
        name=project_name,
        creator=creator,
        keycloak_group_id=keycloak_group_id or str(uuid4()),
    )
    quota = await create_quota(
        session,
        cluster,
        project,
        cpu_milli_cores=quota_cpu,
        memory_bytes=quota_memory,
        ephemeral_storage_bytes=quota_storage,
        gpu_count=quota_gpu,
        status=quota_status,
        updated_at=quota_updated_at,
        creator=creator,
    )
    await session.refresh(project, ["quota"])
    return project, quota


async def create_basic_test_environment(
    session: AsyncSession,
    *,
    cluster_name: str = "test-cluster",
    cluster_base_url: str = "https://example.com",
    project_name: str = "test-project",
    creator: str = "test@example.com",
    create_project_quota: bool = False,
) -> TestEnvironment:
    """
    Create a basic test environment with Cluster -> Project hierarchy.

    This is the most commonly used factory for repository tests that need
    a standard test environment setup.

    Args:
        create_project_quota: If True, creates the project with a quota. Use this
            for tests that need projects with quotas (e.g., resource allocation tests).
    """
    cluster = await create_cluster(session, name=cluster_name, creator=creator, workloads_base_url=cluster_base_url)

    if create_project_quota:
        project, quota = await create_project_with_quota(session, cluster, project_name=project_name, creator=creator)
    else:
        project = await create_project(session, cluster, name=project_name, creator=creator)

    return TestEnvironment(cluster=cluster, project=project, creator=creator)


async def create_full_test_environment(
    session: AsyncSession,
    *,
    cluster_name: str = "test-cluster",
    cluster_base_url: str = "https://example.com",
    project_name: str = "test-project",
    user_email: str = "test@example.com",
    creator: str = "test@example.com",
) -> ExtendedTestEnvironment:
    """
    Create a full test environment with optional additional entities.

    This factory creates the basic hierarchy plus a user and optionally
    charts, models, and datasets based on the provided flags.
    """
    cluster = await create_cluster(session, name=cluster_name, creator=creator, workloads_base_url=cluster_base_url)
    project = await create_project(session, cluster, name=project_name, creator=creator)
    user = await create_user(session, email=user_email, invited_by=creator)

    return ExtendedTestEnvironment(cluster=cluster, project=project, user=user, creator=creator)


async def create_multiple_users(
    session: AsyncSession, user_count: int = 3, *, email_prefix: str = "user", creator: str = "test@example.com"
) -> list[User]:
    """Create multiple users."""
    users = []
    for i in range(user_count):
        user = await create_user(session, email=f"{email_prefix}{i + 1}@example.com", invited_by=creator)
        users.append(user)
    return users


async def create_multi_user_environment(
    session: AsyncSession, user_count: int = 2, *, creator: str = "test@example.com"
) -> list[User]:
    """
    Create a test environment with multiple users for testing
    multi-user scenarios.
    """
    users = await create_multiple_users(session, user_count, creator=creator)
    return users


async def create_multi_cluster_environment(
    session: AsyncSession, cluster_count: int = 2, *, creator: str = "test@example.com"
) -> list[tuple[Cluster, Project]]:
    """
    Create multiple complete test environments for testing
    isolation scenarios.
    """
    environments = []
    for i in range(cluster_count):
        cluster = await create_cluster(session, name=f"test-cluster-{i + 1}", creator=creator)
        project = await create_project(
            session, cluster, name=f"test-project-{i + 1}", creator=creator, keycloak_group_id=str(uuid4())
        )
        environments.append((cluster, project))

    return environments


async def create_workload(
    session: AsyncSession,
    cluster: Cluster,
    project: Project,
    *,
    id: UUID | None = None,
    display_name: str | None = None,
    workload_type: WorkloadType = WorkloadType.CUSTOM,
    status: str = "Pending",
    last_status_transition_at: datetime | None = None,
    creator: str = "test@example.com",
) -> Workload:
    """Create a test workload associated with cluster and project."""
    now = datetime.now(UTC)
    workload = Workload(
        id=id or uuid4(),
        display_name=display_name,
        type=workload_type,
        cluster_id=cluster.id,
        project_id=project.id,
        status=status,
        last_status_transition_at=last_status_transition_at or now,
        created_by=creator,
        updated_by=creator,
    )
    session.add(workload)
    await session.flush()
    return workload


async def create_workload_component(
    session: AsyncSession,
    workload: Workload,
    *,
    id: UUID | None = None,
    name: str = "test-component",
    kind: WorkloadComponentKind = WorkloadComponentKind.JOB,
    api_version: str = "v1",
    status: str = "Pending",
    status_reason: str | None = None,
    creator: str = "test@example.com",
) -> WorkloadComponent:
    """Create a test workload component associated with a workload."""
    component = WorkloadComponent(
        id=id or uuid4(),
        name=name,
        kind=kind.value,
        api_version=api_version,
        workload_id=workload.id,
        status=status,
        status_reason=status_reason,
        created_by=creator,
        updated_by=creator,
    )
    session.add(component)
    await session.flush()
    return component


async def create_workload_time_summary(
    session: AsyncSession,
    workload: Workload,
    *,
    id: UUID | None = None,
    status: str = "Pending",
    total_elapsed_seconds: int = 3600,
    creator: str = "test@example.com",
) -> WorkloadTimeSummary:
    """Create a test workload time summary associated with a workload."""
    time_summary = WorkloadTimeSummary(
        id=id or uuid4(),
        workload_id=workload.id,
        status=status,
        total_elapsed_seconds=total_elapsed_seconds,
        created_by=creator,
        updated_by=creator,
    )
    session.add(time_summary)
    await session.flush()
    return time_summary


async def create_workload_with_components(
    session: AsyncSession,
    cluster: Cluster,
    project: Project,
    *,
    workload_id: UUID | None = None,
    component_count: int = 2,
    workload_status: str = "Running",
    component_status: str = "Running",
    workload_type: WorkloadType = WorkloadType.CUSTOM,
    creator: str = "test@example.com",
) -> tuple[Workload, list[WorkloadComponent]]:
    """Create a test workload with multiple components."""
    workload = await create_workload(
        session, cluster, project, id=workload_id, workload_type=workload_type, status=workload_status, creator=creator
    )

    components = []
    for i in range(component_count):
        component = await create_workload_component(
            session, workload, name=f"test-component-{i + 1}", status=component_status, creator=creator
        )
        components.append(component)

    return workload, components


async def create_secret(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "my-secret",
    secret_type: str = SecretKind.EXTERNAL_SECRET.value,
    secret_scope: str = SecretScope.ORGANIZATION.value,
    use_case: str | None = SecretUseCase.S3.value,
    manifest: str = "manifest",
    status: str = SecretStatus.UNASSIGNED.value,
    status_reason: str | None = None,
    creator: str = "test@example.com",
) -> Secret:
    """Create a test secret."""
    now = datetime.now(UTC)

    # Create OrganizationScopedSecret for ORGANIZATION scope, regular Secret otherwise
    if secret_scope == SecretScope.ORGANIZATION.value:
        secret = OrganizationScopedSecret(
            id=id or uuid4(),
            name=name,
            type=secret_type,
            scope=secret_scope,
            use_case=use_case,
            manifest="apiVersion: external-secrets.io/v1\nkind: ExternalSecret\nmetadata:\n  name: test-secret\nspec:\n  secretStoreRef:\n    kind: SecretStore\n    name: test-secret-store",
            status=status,
            status_reason=status_reason,
            created_by=creator,
            updated_by=creator,
            created_at=now,
            updated_at=now,
        )
    else:
        secret = ProjectScopedSecret(
            id=id or uuid4(),
            name=name,
            type=secret_type,
            scope=secret_scope,
            use_case=use_case,
            status=status,
            status_reason=status_reason,
            created_by=creator,
            updated_by=creator,
            created_at=now,
            updated_at=now,
        )
    session.add(secret)
    await session.flush()
    return secret


async def create_organization_secret_assignment(
    session: AsyncSession,
    project: Project,
    secret: Secret,  # Accept Secret type since it could be OrganizationScopedSecret
    *,
    id: UUID | None = None,
    status: str = ProjectSecretStatus.SYNCED.value,
    status_reason: str | None = None,
    creator: str = "test@example.com",
) -> OrganizationSecretAssignment:
    """Create a test organization secret assignment to a project."""
    assignment = OrganizationSecretAssignment(
        id=id or uuid4(),
        project_id=project.id,
        organization_secret_id=secret.id,  # This should be the secret's ID
        status=status,
        status_reason=status_reason,
        created_by=creator,
        updated_by=creator,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def create_secret_with_project_assignment(
    session: AsyncSession,
    project: Project,
    *,
    secret_id: UUID | None = None,
    name: str = "test-secret",
    secret_type: SecretKind = SecretKind.EXTERNAL_SECRET,
    manifest: str = "apiVersion: v1\nkind: Secret\nmetadata:\n  name: test-secret",
    secret_status: str = SecretStatus.SYNCED.value,
    secret_status_reason: str | None = None,
    project_secret_status: str = "Synced",
    project_secret_status_reason: str | None = None,
    creator: str = "test@example.com",
) -> Secret:
    """Create a test secret with project assignment."""
    secret = await create_secret(
        session,
        id=secret_id,
        name=name,
        secret_type=secret_type,
        secret_scope=SecretScope.ORGANIZATION,
        manifest=manifest,
        status=secret_status,
        status_reason=secret_status_reason,
        creator=creator,
    )

    await create_organization_secret_assignment(
        session,
        project,
        secret,
        status=project_secret_status,
        status_reason=project_secret_status_reason,
        creator=creator,
    )
    return secret


async def create_project_scoped_secret(
    session: AsyncSession,
    project: Project,
    *,
    secret_id: UUID | None = None,
    name: str = "test-project-secret",
    secret_type: SecretKind | str = SecretKind.EXTERNAL_SECRET,
    secret_status: str = SecretStatus.SYNCED.value,
    secret_status_reason: str | None = None,
    use_case: str | None = None,
    creator: str = "test@example.com",
) -> ProjectScopedSecret:
    """Create a test project-scoped secret."""
    now = datetime.now(UTC)
    # Handle both SecretKind enum and string values
    type_value = secret_type.value if isinstance(secret_type, SecretKind) else secret_type

    secret = ProjectScopedSecret(
        id=secret_id or uuid4(),
        name=name,
        type=type_value,
        scope=SecretScope.PROJECT.value,
        status=secret_status,
        status_reason=secret_status_reason,
        project_id=project.id,
        created_by=creator,
        updated_by=creator,
        created_at=now,
        updated_at=now,
        use_case=use_case,
    )
    session.add(secret)
    await session.flush()
    return secret


async def create_storage(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "my-storage",
    storage_type: str = StorageType.S3.value,
    storage_scope: str = StorageScope.ORGANIZATION.value,
    secret_id: UUID = uuid4(),
    status: str = StorageStatus.UNASSIGNED.value,
    status_reason: str | None = None,
    bucket_url: str = "https://some-bucket-name.s3.amazonaws.com/path/",
    access_key_name: str = "accessKeyName",
    secret_key_name: str = "secretKeyName",
    creator: str = "test@example.com",
) -> Storage:
    """Create a test storage."""
    now = datetime.now(UTC)
    storage = Storage(
        id=id or uuid4(),
        name=name,
        type=storage_type,
        scope=storage_scope,
        secret_id=secret_id,
        status=status,
        status_reason=status_reason,
        bucket_url=bucket_url,
        access_key_name=access_key_name,
        secret_key_name=secret_key_name,
        created_by=creator,
        updated_by=creator,
        created_at=now,
        updated_at=now,
    )
    session.add(storage)
    await session.flush()
    return storage


async def create_project_storage(
    session: AsyncSession,
    project: Project,
    storage: Storage,
    *,
    id: UUID | None = None,
    status: str = ProjectStorageStatus.SYNCED.value,
    status_reason: str | None = None,
    creator: str = "test@example.com",
) -> ProjectStorage:
    """Create a test project storage assignment."""
    project_storage = ProjectStorage(
        id=id or uuid4(),
        project_id=project.id,
        storage_id=storage.id,
        status=status,
        status_reason=status_reason,
        created_by=creator,
        updated_by=creator,
    )

    session.add(project_storage)
    await session.flush()
    return project_storage


async def create_project_storage_configmap(
    session: AsyncSession,
    project_storage: ProjectStorage,
    *,
    id: UUID | None = None,
    status: str = ConfigMapStatus.ADDED.value,
    status_reason: str | None = None,
    creator: str = "test@example.com",
) -> ProjectStorageConfigmap:
    """Create a test project storage assignment."""
    project_storage_configMap = ProjectStorageConfigmap(
        id=id or uuid4(),
        project_storage_id=project_storage.id,
        status=status,
        status_reason=status_reason,
        created_by=creator,
        updated_by=creator,
    )

    session.add(project_storage_configMap)
    await session.flush()
    return project_storage_configMap


async def create_storage_with_project_assignment(
    session: AsyncSession,
    project: Project,
    secret: Secret,
    *,
    storage_id: UUID | None = None,
    name: str = "my-storage",
    storage_type: str = StorageType.S3.value,
    storage_scope: str = StorageScope.ORGANIZATION.value,
    storage_status: str = StorageStatus.UNASSIGNED.value,
    storage_status_reason: str | None = None,
    bucket_url: str = "https://some-bucket-name.s3.amazonaws.com/path/",
    access_key_name: str = "accessKeyName",
    secret_key_name: str = "secretKeyName",
    project_storage_status: str = "Synced",
    project_storage_status_reason: str | None = None,
    creator: str = "test@example.com",
) -> Storage:
    """Create a test storage with project assignment."""
    storage = await create_storage(
        session,
        id=storage_id,
        name=name,
        storage_type=storage_type,
        storage_scope=storage_scope,
        secret_id=secret.id,
        status=storage_status,
        status_reason=storage_status_reason,
        bucket_url=bucket_url,
        access_key_name=access_key_name,
        secret_key_name=secret_key_name,
        creator=creator,
    )

    await create_organization_secret_assignment(session, project, secret)

    project_storage = await create_project_storage(
        session,
        project,
        storage,
        status=project_storage_status,
        status_reason=project_storage_status_reason,
        creator=creator,
    )

    await create_project_storage_configmap(session, project_storage)

    return storage
