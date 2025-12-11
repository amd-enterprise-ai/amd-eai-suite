# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Database test data factories for creating real entities with proper relationships.

This module provides factory functions that create real database entities
for use in repository-level tests, replacing inline object creation patterns
and test_environment fixtures.

## Automatic Isolation Testing

By default, most factory functions automatically create "noise" data in other
organizations to catch cross-organization data leakage bugs. This ensures that
organization-scoped queries are properly filtered and don't accidentally return
data from other organizations.

When to disable isolation data (include_isolation_data=False):
- Testing non-organization-scoped functionality (global statistics, system-wide operations)
- Testing specific isolation scenarios where you need to control the exact data setup
- Performance-sensitive tests where the extra data creation is unnecessary
- Tests that specifically need a clean database state with minimal data

When to keep isolation data enabled (default):
- All organization-scoped repository and service tests
- Multi-tenant functionality testing
- Resource aggregation and calculation tests
- User access control tests
"""

from datetime import UTC, datetime
from typing import Any, NamedTuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    ConfigMapStatus,
    GPUVendor,
    ProjectSecretStatus,
    ProjectStorageStatus,
    QuotaStatus,
    SecretKind,
    SecretScope,
    WorkloadComponentKind,
)
from app.aims.models import AIM
from app.charts.models import Chart
from app.clusters.models import Cluster, ClusterNode
from app.datasets.models import Dataset, DatasetType
from app.managed_workloads.models import ManagedWorkload
from app.models.models import InferenceModel, OnboardingStatus
from app.organizations.models import Organization
from app.overlays.models import Overlay
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.quotas.models import Quota
from app.secrets.enums import SecretStatus, SecretUseCase
from app.secrets.models import (
    OrganizationScopedSecret,
    OrganizationSecretAssignment,
    ProjectScopedSecret,
    Secret,
)
from app.storages.enums import StorageScope, StorageStatus, StorageType
from app.storages.models import ProjectStorage, ProjectStorageConfigmap, Storage
from app.users.models import User
from app.workloads.enums import WorkloadType
from app.workloads.models import Workload, WorkloadComponent, WorkloadTimeSummary


class TestEnvironment(NamedTuple):
    """Container for standard test environment entities."""

    organization: Organization
    cluster: Cluster
    project: Project
    creator: str


class ExtendedTestEnvironment(NamedTuple):
    """Container for extended test environment with additional entities."""

    organization: Organization
    cluster: Cluster
    project: Project
    user: User
    chart: Chart | None = None
    model: InferenceModel | None = None
    dataset: Dataset | None = None
    creator: str = "test@example.com"


class ComplexTestEnvironment(NamedTuple):
    """Container for complex test scenarios with configurable entities."""

    organization: Organization
    cluster: Cluster
    accessible_projects: list[Project]
    users: list[User]
    project_memberships: dict[UUID, list[User]]  # project_id -> users (for test tracking only, not in DB)
    quotas: list[Quota]
    creator: str


async def create_organization(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "Test Organization",
    keycloak_organization_id: str | None = None,
    keycloak_group_id: str | None = None,
    creator: str = "test@example.com",
) -> Organization:
    """Create a test organization with consistent defaults."""
    organization = Organization(
        id=id or uuid4(),
        name=name,
        keycloak_organization_id=keycloak_organization_id or str(uuid4()),
        keycloak_group_id=keycloak_group_id or str(uuid4()),
        created_by=creator,
        updated_by=creator,
    )
    session.add(organization)
    await session.flush()
    return organization


async def create_cluster(
    session: AsyncSession,
    organization: Organization,
    *,
    id: UUID | None = None,
    name: str = "test-cluster",
    creator: str = "test@example.com",
    workloads_base_url: str = "https://example.com",
    kube_api_url: str = "https://k8s.example.com:6443",
) -> Cluster:
    """Create a test cluster associated with an organization."""
    cluster = Cluster(
        id=id or uuid4(),
        name=name,
        organization_id=organization.id,
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
    organization: Organization,
    cluster: Cluster,
    *,
    id: UUID | None = None,
    name: str = "test-project",
    project_status: str = ProjectStatus.PENDING.value,
    description: str = "Test project description",
    creator: str = "test@example.com",
    keycloak_group_id: str | None = None,
) -> Project:
    """Create a test project associated with organization and cluster."""
    project = Project(
        id=id or uuid4(),
        name=name,
        description=description,
        organization_id=organization.id,
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


async def create_user(
    session: AsyncSession,
    organization: Organization,
    *,
    id: UUID | None = None,
    email: str = "test@example.com",
    keycloak_user_id: str | None = None,
    invited_by: str = "admin@example.com",
    invited_at: datetime | None = None,
    last_active_at: datetime | None = None,
) -> User:
    """Create a test user in an organization."""
    now = datetime.now(UTC)
    user = User(
        id=id or uuid4(),
        email=email,
        organization_id=organization.id,
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
    organization: Organization,
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
    organization: Organization,
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
        organization,
        cluster,
        id=project_id,
        name=project_name,
        creator=creator,
        keycloak_group_id=keycloak_group_id or str(uuid4()),
    )
    quota = await create_quota(
        session,
        organization,
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

    return project, quota


async def create_chart(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "Test Chart",
    display_name: str | None = None,
    slug: str | None = None,
    chart_type: WorkloadType = WorkloadType.INFERENCE,
    signature: dict | None = None,
    creator: str = "test@example.com",
) -> Chart:
    """Create a test chart (charts are global, not organization-scoped)."""
    chart = Chart(
        id=id or uuid4(),
        name=name,
        slug=slug,
        display_name=display_name,
        type=chart_type,
        signature=signature or {},
        created_by=creator,
        updated_by=creator,
    )
    session.add(chart)
    await session.flush()
    return chart


async def create_overlay(
    session: AsyncSession,
    chart: Chart,
    *,
    id: UUID | None = None,
    canonical_name: str | None = None,
    overlay_data: dict | None = None,
    creator: str = "test@example.com",
) -> Overlay:
    """Create a test overlay associated with a chart."""
    overlay = Overlay(
        id=id or uuid4(),
        chart_id=chart.id,
        canonical_name=canonical_name,
        overlay=overlay_data or {},
        created_by=creator,
        updated_by=creator,
    )
    session.add(overlay)
    await session.flush()
    return overlay


async def create_inference_model(
    session: AsyncSession,
    project: Project,
    *,
    id: UUID | None = None,
    name: str = "Test Model",
    model_weights_path: str = "test-model.bin",
    canonical_name: str = "test/model",
    onboarding_status: OnboardingStatus = OnboardingStatus.ready,
    creator: str = "test@example.com",
) -> InferenceModel:
    """Create a test inference model in a project."""
    model = InferenceModel(
        id=id or uuid4(),
        name=name,
        model_weights_path=model_weights_path,
        canonical_name=canonical_name,
        onboarding_status=onboarding_status,
        project_id=project.id,
        created_by=creator,
        updated_by=creator,
    )
    session.add(model)
    await session.flush()
    return model


async def create_aim(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    resource_name: str = "aim-test-model-0-1-0",
    image_reference: str = "docker.io/amdenterpriseai/test-model:0.1.0",
    labels: dict[str, Any] | None = None,
    status: str = "Ready",
    creator: str = "test@example.com",
) -> AIM:
    """Create a test AIM entity."""
    aim = AIM(
        id=id or uuid4(),
        resource_name=resource_name,
        image_reference=image_reference,
        labels=labels or {},
        status=status,
        created_by=creator,
        updated_by=creator,
    )
    session.add(aim)
    await session.flush()
    return aim


async def create_dataset(
    session: AsyncSession,
    project: Project,
    *,
    id: UUID | None = None,
    name: str = "Test Dataset",
    description: str = "Test dataset description",
    path: str = "test-dataset.jsonl",
    dataset_type: DatasetType = DatasetType.FINETUNING,
    creator: str = "test@example.com",
) -> Dataset:
    """Create a test dataset in a project."""
    dataset = Dataset(
        id=id or uuid4(),
        name=name,
        description=description,
        path=path,
        type=dataset_type,
        project_id=project.id,
        created_by=creator,
        updated_by=creator,
    )
    session.add(dataset)
    await session.flush()
    return dataset


async def create_basic_test_environment(
    session: AsyncSession,
    *,
    org_name: str = "Test Organization",
    cluster_name: str = "test-cluster",
    cluster_base_url: str = "https://example.com",
    project_name: str = "test-project",
    creator: str = "test@example.com",
    include_isolation_data: bool = True,
    create_project_quota: bool = False,
) -> TestEnvironment:
    """
    Create a basic test environment with Organization -> Cluster -> Project hierarchy.

    This is the most commonly used factory for repository tests that need
    a standard test environment setup.

    Args:
        include_isolation_data: If True (default), automatically creates "noise"
            data in other organizations to catch cross-organization data leakage
            bugs. Set to False for non-organization-scoped tests that don't need
            isolation testing.
        create_project_quota: If True, creates the project with a quota. Use this
            for tests that need projects with quotas (e.g., resource allocation tests).
    """
    organization = await create_organization(session, name=org_name, creator=creator)
    cluster = await create_cluster(
        session, organization, name=cluster_name, creator=creator, workloads_base_url=cluster_base_url
    )

    if create_project_quota:
        project, quota = await create_project_with_quota(
            session, organization, cluster, project_name=project_name, creator=creator
        )
    else:
        project = await create_project(session, organization, cluster, name=project_name, creator=creator)

    # Automatically create isolation noise data to catch cross-org bugs
    if include_isolation_data:
        await _create_isolation_noise_data(session, creator)

    return TestEnvironment(
        organization=organization,
        cluster=cluster,
        project=project,
        creator=creator,
    )


async def create_full_test_environment(
    session: AsyncSession,
    *,
    with_chart: bool = False,
    with_model: bool = False,
    with_dataset: bool = False,
    org_name: str = "Test Organization",
    cluster_name: str = "test-cluster",
    cluster_base_url: str = "https://example.com",
    project_name: str = "test-project",
    user_email: str = "test@example.com",
    creator: str = "test@example.com",
    include_isolation_data: bool = True,
) -> ExtendedTestEnvironment:
    """
    Create a full test environment with optional additional entities.

    This factory creates the basic hierarchy plus a user and optionally
    charts, models, and datasets based on the provided flags.

    Args:
        include_isolation_data: If True (default), automatically creates "noise"
            data in other organizations to catch cross-organization data leakage
            bugs. Set to False for non-organization-scoped tests.
    """
    organization = await create_organization(session, name=org_name, creator=creator)
    cluster = await create_cluster(
        session, organization, name=cluster_name, creator=creator, workloads_base_url=cluster_base_url
    )
    project = await create_project(session, organization, cluster, name=project_name, creator=creator)
    user = await create_user(session, organization, email=user_email, invited_by=creator)

    chart = None
    if with_chart:
        chart = await create_chart(session, creator=creator)

    model = None
    if with_model:
        model = await create_inference_model(session, project, creator=creator)

    dataset = None
    if with_dataset:
        dataset = await create_dataset(session, project, creator=creator)

    # Automatically create isolation noise data to catch cross-org bugs
    if include_isolation_data:
        await _create_isolation_noise_data(session, creator)

    return ExtendedTestEnvironment(
        organization=organization,
        cluster=cluster,
        project=project,
        user=user,
        chart=chart,
        model=model,
        dataset=dataset,
        creator=creator,
    )


async def create_multi_project_environment(
    session: AsyncSession,
    project_count: int = 2,
    *,
    org_name: str = "Test Organization",
    cluster_name: str = "test-cluster",
    creator: str = "test@example.com",
) -> tuple[Organization, Cluster, list[Project]]:
    """
    Create a test environment with multiple projects for testing
    multi-project scenarios.
    """
    organization = await create_organization(session, name=org_name, creator=creator)
    cluster = await create_cluster(session, organization, name=cluster_name, creator=creator)

    projects = []
    for i in range(project_count):
        project, quota = await create_project_with_quota(
            session,
            organization,
            cluster,
            project_name=f"test-project-{i + 1}",
            creator=creator,
            keycloak_group_id=str(uuid4()),
        )
        projects.append(project)

    return organization, cluster, projects


async def create_multiple_users(
    session: AsyncSession,
    organization: Organization,
    user_count: int = 3,
    *,
    email_prefix: str = "user",
    creator: str = "test@example.com",
) -> list[User]:
    """Create multiple users in an organization."""
    users = []
    for i in range(user_count):
        user = await create_user(
            session,
            organization,
            email=f"{email_prefix}{i + 1}@example.com",
            invited_by=creator,
        )
        users.append(user)
    return users


async def create_multi_user_environment(
    session: AsyncSession,
    user_count: int = 2,
    *,
    org_name: str = "Test Organization",
    creator: str = "test@example.com",
) -> tuple[Organization, list[User]]:
    """
    Create a test environment with multiple users for testing
    multi-user scenarios.
    """
    organization = await create_organization(session, name=org_name, creator=creator)
    users = await create_multiple_users(session, organization, user_count, creator=creator)
    return organization, users


async def create_multi_organization_environment(
    session: AsyncSession,
    org_count: int = 2,
    *,
    creator: str = "test@example.com",
) -> list[tuple[Organization, Cluster, Project]]:
    """
    Create multiple complete test environments for testing
    organization isolation scenarios.
    """
    environments = []
    for i in range(org_count):
        org = await create_organization(
            session,
            name=f"Test Organization {i + 1}",
            creator=creator,
            keycloak_organization_id=str(uuid4()),
            keycloak_group_id=str(uuid4()),
        )
        cluster = await create_cluster(session, org, name=f"test-cluster-{i + 1}", creator=creator)
        project = await create_project(
            session, org, cluster, name=f"test-project-{i + 1}", creator=creator, keycloak_group_id=str(uuid4())
        )
        environments.append((org, cluster, project))

    return environments


async def create_complex_environment(
    session: AsyncSession,
    *,
    project_configs: list[dict] | None = None,
    total_users: int = 3,
    include_quotas: bool = True,
    include_memberships: bool = True,
    org_name: str = "Test Organization",
    cluster_name: str = "test-cluster",
    creator: str = "test@example.com",
) -> ComplexTestEnvironment:
    """
    Create a complex test environment with configurable projects and users.

    Args:
        project_configs: List of project configurations. Each dict should contain:
            - name: str - Project name
            - user_count: int - Number of users to assign to this project
            - description: str (optional) - Project description
        total_users: Total number of users to create (used if project_configs is None)
        include_quotas: Whether to create quotas for projects
        include_memberships: Whether to create project memberships
        org_name: Organization name
        cluster_name: Cluster name
        creator: Creator identifier

    Returns:
        ComplexTestEnvironment with all entities and relationships

    Default behavior creates 2 projects with varying user distributions.
    """
    # Set default project configurations if none provided
    if project_configs is None:
        project_configs = [
            {"name": "Complex Project 1", "user_count": 2, "description": "First complex test project"},
            {"name": "Complex Project 2", "user_count": 1, "description": "Second complex test project"},
        ]

    # Create basic hierarchy
    organization = await create_organization(session, name=org_name, creator=creator)
    cluster = await create_cluster(session, organization, name=cluster_name, creator=creator)

    # Create all users first
    users = await create_multiple_users(session, organization, user_count=total_users, creator=creator)

    # Create projects based on configuration
    projects = []
    quotas = []
    project_memberships = {}

    user_index = 0
    for config in project_configs:
        project_name = config["name"]
        user_count = config["user_count"]
        description = config.get("description", f"Test project: {project_name}")

        if include_quotas:
            # Create project with quota
            project, quota = await create_project_with_quota(
                session,
                organization,
                cluster,
                project_name=project_name,
                creator=creator,
                keycloak_group_id=str(uuid4()),
            )
            quotas.append(quota)
        else:
            # Create project without quota
            project = await create_project(
                session,
                organization,
                cluster,
                name=project_name,
                description=description,
                creator=creator,
                keycloak_group_id=str(uuid4()),
            )

        projects.append(project)

        # Track users conceptually associated with this project (for test purposes only)
        if include_memberships and user_count > 0:
            # Get users for this project (cycling through available users)
            project_users = []
            for _ in range(user_count):
                if user_index < len(users):
                    user = users[user_index]
                    project_users.append(user)
                    user_index += 1
                else:
                    # If we've used all users, start cycling through them again
                    user = users[user_index % len(users)]
                    project_users.append(user)
                    user_index += 1

            project_memberships[project.id] = project_users
        else:
            project_memberships[project.id] = []

    return ComplexTestEnvironment(
        organization=organization,
        cluster=cluster,
        accessible_projects=projects,
        users=users,
        project_memberships=project_memberships,
        quotas=quotas,
        creator=creator,
    )


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


async def create_chart_workload(
    session: AsyncSession,
    project: Project,
    chart: Chart | None = None,
    *,
    id: UUID | None = None,
    name: str | None = None,
    display_name: str | None = None,
    workload_type: WorkloadType | None = None,
    status: str = "Pending",
    model_id: UUID | None = None,
    dataset_id: UUID | None = None,
    user_inputs: dict | None = None,
    manifest: str | None = None,
    output: dict | None = None,
    last_status_transition_at: datetime | None = None,
    creator: str = "test@example.com",
) -> ManagedWorkload:
    """Create a test chart workload associated with project, and optionally chart, model, or dataset.
    If workload_type is not specified and a chart is provided, the workload type will be inferred
    from the chart type. Otherwise, defaults to INFERENCE.
    """
    now = datetime.now(UTC)

    # Determine the workload type: explicit parameter > chart type > default to INFERENCE
    if workload_type is not None:
        final_workload_type = workload_type
    elif chart is not None:
        final_workload_type = chart.type
    else:
        final_workload_type = WorkloadType.INFERENCE

    chart_workload = ManagedWorkload(
        id=id or uuid4(),
        name=name,
        display_name=display_name,
        type=final_workload_type,
        cluster_id=project.cluster.id,
        project_id=project.id,
        chart_id=chart.id if chart else None,
        model_id=model_id,
        dataset_id=dataset_id,
        status=status,
        kind="managed",
        user_inputs=user_inputs or {},
        manifest=manifest,
        output=output or {},
        last_status_transition_at=last_status_transition_at or now,
        created_by=creator,
        updated_by=creator,
    )
    session.add(chart_workload)
    await session.flush()
    return chart_workload


async def create_aim_workload(
    session: AsyncSession,
    project: Project,
    aim: AIM | None = None,
    *,
    id: UUID | None = None,
    name: str | None = None,
    display_name: str | None = None,
    workload_type: WorkloadType = WorkloadType.INFERENCE,
    status: str = "Pending",
    user_inputs: dict | None = None,
    manifest: str | None = None,
    output: dict | None = None,
    last_status_transition_at: datetime | None = None,
    cluster_auth_group_id: str | None = None,
    creator: str = "test@example.com",
) -> ManagedWorkload:
    """Create a test AIM workload associated with a project and AIM"""
    if not aim:
        aim = await create_aim(session, creator=creator)
    now = datetime.now(UTC)
    aim_workload = ManagedWorkload(
        id=id or uuid4(),
        name=name,
        display_name=display_name,
        type=workload_type,
        project_id=project.id,
        cluster_id=project.cluster.id,
        aim_id=aim.id,
        status=status,
        kind="managed",
        user_inputs=user_inputs or {},
        manifest=manifest,
        output=output or {},
        last_status_transition_at=last_status_transition_at or now,
        cluster_auth_group_id=cluster_auth_group_id,
        created_by=creator,
        updated_by=creator,
    )
    session.add(aim_workload)
    await session.flush()
    return aim_workload


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
        session,
        cluster,
        project,
        id=workload_id,
        workload_type=workload_type,
        status=workload_status,
        creator=creator,
    )

    components = []
    for i in range(component_count):
        component = await create_workload_component(
            session,
            workload,
            name=f"test-component-{i + 1}",
            status=component_status,
            creator=creator,
        )
        components.append(component)

    return workload, components


async def _create_isolation_noise_data(session: AsyncSession, creator: str) -> None:
    """
    Create 'noise' data in other organizations to automatically catch
    cross-organization data leakage bugs.

    This function creates realistic test data in separate organizations that
    should NEVER appear in organization-scoped queries. If it does appear,
    it indicates a cross-organization data leakage bug.
    """
    # Create noise organization 1 with complete hierarchy
    noise_org1 = await create_organization(session, name="Noise Org Alpha", creator=creator)
    noise_cluster1 = await create_cluster(session, noise_org1, name="Noise Cluster Alpha", creator=creator)
    noise_project1 = await create_project(
        session, noise_org1, noise_cluster1, name="Noise Project Alpha", creator=creator
    )

    # Add some nodes and quotas to make it realistic
    await create_cluster_node(
        session,
        noise_cluster1,
        name="noise-node-alpha",
        cpu_milli_cores=2000,
        memory_bytes=4 * 1024**3,
        ephemeral_storage_bytes=50 * 1024**3,
        gpu_count=1,
        gpu_type="Tesla V100",
        gpu_vendor=GPUVendor.NVIDIA,
        status="Ready",
        is_ready=True,
        creator=creator,
    )

    _, noise_quota1 = await create_project_with_quota(
        session,
        noise_org1,
        noise_cluster1,
        project_name="Noise Project Alpha Quota",
        quota_cpu=1000,
        quota_memory=2 * 1024**3,
        quota_gpu=1,
        quota_status=QuotaStatus.READY,
        creator=creator,
    )

    # Create noise organization 2 with different naming pattern
    noise_org2 = await create_organization(session, name="Noise Org Beta", creator=creator)
    noise_cluster2 = await create_cluster(session, noise_org2, name="Noise Cluster Beta", creator=creator)
    noise_project2 = await create_project(
        session, noise_org2, noise_cluster2, name="Noise Project Beta", creator=creator
    )

    # Add different node configuration to noise org 2
    await create_cluster_node(
        session,
        noise_cluster2,
        name="noise-node-beta",
        cpu_milli_cores=4000,
        memory_bytes=8 * 1024**3,
        ephemeral_storage_bytes=100 * 1024**3,
        gpu_count=2,
        gpu_type="Tesla A100",
        gpu_vendor=GPUVendor.NVIDIA,
        status="Ready",
        is_ready=True,
        creator=creator,
    )

    # Create user in noise org for user access testing
    noise_user = await create_user(session, noise_org2, email="noise-user@example.com", invited_by=creator)


async def create_cluster_resource_test_environment(
    session: AsyncSession,
    *,
    cluster_count: int = 2,
    nodes_per_cluster: int = 2,
    projects_per_cluster: int = 1,
    org_name: str = "Test Organization",
    creator: str = "test@example.com",
    include_isolation_data: bool = True,
) -> tuple[TestEnvironment, list[Cluster], list[ClusterNode], list[tuple[Project, Quota]]]:
    """
    Create a specialized test environment for testing cluster resource aggregation.

    This factory creates multiple clusters with nodes and quotas, ideal for testing
    resource calculation and aggregation logic. Automatic isolation testing ensures
    that resource calculations don't accidentally include data from other organizations.

    Returns:
        - Primary test environment (org, cluster, project)
        - List of all clusters (including the primary one)
        - List of all cluster nodes
        - List of (project, quota) tuples
    """
    # Create base environment
    organization = await create_organization(session, name=org_name, creator=creator)

    clusters = []
    nodes = []
    project_quotas = []

    # Create multiple clusters with resources
    for i in range(cluster_count):
        cluster = await create_cluster(session, organization, name=f"Test-Cluster-{i + 1}", creator=creator)
        clusters.append(cluster)

        # Create nodes for this cluster
        for j in range(nodes_per_cluster):
            node = await create_cluster_node(
                session,
                cluster,
                name=f"node-{i + 1}-{j + 1}",
                cpu_milli_cores=4000,
                memory_bytes=8 * 1024**3,
                ephemeral_storage_bytes=50 * 1024**3,
                gpu_count=2 if j == 0 else 0,  # First node has GPUs
                gpu_type="Tesla V100" if j == 0 else None,
                gpu_vendor=GPUVendor.NVIDIA if j == 0 else None,
                status="Ready",
                is_ready=True,
                creator=creator,
            )
            nodes.append(node)

        # Create projects with quotas for this cluster
        for k in range(projects_per_cluster):
            project, quota = await create_project_with_quota(
                session,
                organization,
                cluster,
                project_name=f"Test Project {i + 1}-{k + 1}",
                quota_cpu=2000,
                quota_memory=4 * 1024**3,
                quota_gpu=1,
                quota_status=QuotaStatus.READY,
                creator=creator,
            )
            project_quotas.append((project, quota))

    # Create primary test environment using first cluster
    primary_env = TestEnvironment(
        organization=organization,
        cluster=clusters[0],
        project=project_quotas[0][0],
        creator=creator,
    )

    # Automatically create isolation noise data
    if include_isolation_data:
        await _create_isolation_noise_data(session, creator)

    return primary_env, clusters, nodes, project_quotas


async def create_secret(
    session: AsyncSession,
    organization: Organization,
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
    """Create a test secret associated with organization."""
    now = datetime.now(UTC)

    # Create OrganizationScopedSecret for ORGANIZATION scope, regular Secret otherwise
    if secret_scope == SecretScope.ORGANIZATION.value:
        secret = OrganizationScopedSecret(
            id=id or uuid4(),
            name=name,
            type=secret_type,
            scope=secret_scope,
            use_case=use_case,
            manifest=manifest,
            status=status,
            status_reason=status_reason,
            organization_id=organization.id,
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
            organization_id=organization.id,
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
    organization: Organization,
    project: Project,
    *,
    secret_id: UUID | None = None,
    name: str = "test-secret",
    secret_type: SecretKind = SecretKind.EXTERNAL_SECRET,
    scope: SecretScope = SecretScope.ORGANIZATION,
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
        organization,
        id=secret_id,
        name=name,
        secret_type=secret_type.value,
        secret_scope=scope.value,
        manifest=manifest,
        status=secret_status,
        status_reason=secret_status_reason,
        creator=creator,
    )

    # Use OrganizationSecretAssignment for ORGANIZATION-scoped secrets
    if scope == SecretScope.ORGANIZATION:
        await create_organization_secret_assignment(
            session,
            project,
            secret,
            status=project_secret_status,
            status_reason=project_secret_status_reason,
            creator=creator,
        )
    else:
        # Use ProjectSecret for other scopes (if needed)
        await create_project_scoped_secret(
            session,
            project,
            secret,
            secret_status=project_secret_status,
            secret_status_reason=project_secret_status_reason,
            creator=creator,
        )

    return secret


async def create_project_scoped_secret(
    session: AsyncSession,
    organization: Organization,
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
        organization_id=organization.id,
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
    organization: Organization,
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
    """Create a test storage associated with organization."""
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
        organization_id=organization.id,
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
    organization: Organization,
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
        organization,
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

    await create_organization_secret_assignment(
        session,
        project,
        secret,
    )

    project_storage = await create_project_storage(
        session,
        project,
        storage,
        status=project_storage_status,
        status_reason=project_storage_status_reason,
        creator=creator,
    )

    await create_project_storage_configmap(
        session,
        project_storage,
    )

    return storage
