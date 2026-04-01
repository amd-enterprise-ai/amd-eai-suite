# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Test data factories for AIWB.

This module provides factory functions for creating test data:
- K8s CRD factories (make_*): Create in-memory K8s resource objects
- DB factories (create_*): Create database records

Note: AIWB secrets are managed directly in Kubernetes without database models,
so there is no factory function for secrets. Secrets tests use direct K8s mocks.
"""

from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from fastapi import UploadFile
from kubernetes_asyncio.client import V1Namespace
from sqlalchemy.ext.asyncio import AsyncSession

from app.aims.crds import (
    AIMClusterModelResource,
    AIMClusterServiceTemplateResource,
    AIMServiceResource,
    AIMServiceSpec,
    AIMServiceStatusFields,
    HTTPRouteBackendRef,
    HTTPRouteMatch,
    HTTPRoutePathMatch,
    HTTPRouteResource,
    HTTPRouteRule,
    HTTPRouteSpec,
)
from app.aims.enums import AIMClusterModelStatus, AIMServiceStatus, OptimizationMetric
from app.aims.models import AIMService
from app.aims.schemas import AIMResponse, AIMServiceResponse
from app.apikeys.models import ApiKey
from app.charts.models import Chart
from app.charts.schemas import ChartCreate
from app.config import SUBMITTER_ANNOTATION
from app.datasets.models import Dataset, DatasetType
from app.dispatch.crds import K8sMetadata
from app.models.models import InferenceModel, OnboardingStatus
from app.namespaces.constants import NAMESPACE_ID_LABEL
from app.namespaces.crds import Namespace
from app.namespaces.schemas import (
    NamespaceStatsCounts,
    NamespaceWorkloadMetrics,
    ResourceStatusCount,
    ResourceType,
)
from app.overlays.models import Overlay
from app.workloads.constants import WORKLOAD_ID_LABEL
from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.models import Workload

DEFAULT_TEST_MANIFEST = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test\n"

# ============================================================================
# Namespace Factories
# ============================================================================


def make_namespace_k8s(
    name: str = "test-namespace",
    labels: dict[str, str] | None = None,
    annotations: dict[str, str] | None = None,
    created_at: datetime | None = None,
    project_id: str | None = "test-project-id",
) -> Any:  # Returns MagicMock(spec=V1Namespace)
    """Create a mock K8s V1Namespace for testing.

    Args:
        name: Namespace name
        labels: Namespace labels (defaults to empty dict)
        annotations: Namespace annotations (defaults to empty dict)
        created_at: Creation timestamp
        project_id: Project ID for the namespace (added to labels if provided)

    Returns:
        MagicMock configured to behave like kubernetes_asyncio.client.V1Namespace
    """
    mock_ns = MagicMock(spec=V1Namespace)
    mock_ns.metadata.name = name

    namespace_labels = labels.copy() if labels else {}
    if project_id:
        namespace_labels[NAMESPACE_ID_LABEL] = project_id

    mock_ns.metadata.labels = namespace_labels
    mock_ns.metadata.annotations = annotations or {}
    mock_ns.metadata.creation_timestamp = created_at or datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

    return mock_ns


def make_namespace_crd(
    name: str = "test-namespace",
    labels: dict[str, str] | None = None,
    annotations: dict[str, str] | None = None,
    created_at: datetime | None = None,
    project_id: str | None = "test-project-id",
) -> Namespace:
    """Create a Namespace CRD object for testing.

    Args:
        name: Namespace name
        labels: Namespace labels (defaults to empty dict)
        annotations: Namespace annotations (defaults to empty dict)
        created_at: Creation timestamp
        project_id: Project ID for the namespace (added to labels if provided)

    Returns:
        Namespace CRD object
    """
    namespace_labels = labels.copy() if labels else {}
    if project_id:
        namespace_labels[NAMESPACE_ID_LABEL] = project_id

    return Namespace(
        name=name,
        labels=namespace_labels,
        annotations=annotations or {},
        created_at=created_at or datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )


def make_namespace_workload_metrics(
    id: UUID | None = None,
    name: str = "test-workload",
    display_name: str = "Test Workload",
    type: WorkloadType = WorkloadType.INFERENCE,
    status: WorkloadStatus = WorkloadStatus.RUNNING,
    resource_type: ResourceType = ResourceType.DEPLOYMENT,
    gpu_count: int | None = 2,
    vram: float | None = 1024.0,
    created_at: datetime | None = None,
    created_by: str = "test@example.com",
) -> NamespaceWorkloadMetrics:
    """Create NamespaceWorkloadMetrics for testing.

    Args:
        id: Workload UUID
        name: Workload name
        display_name: Display name
        type: Workload type
        status: Workload status
        resource_type: CRD type
        gpu_count: GPU count
        vram: VRAM in MB
        created_at: Creation timestamp
        created_by: Creator email

    Returns:
        NamespaceWorkloadMetrics instance
    """
    return NamespaceWorkloadMetrics(
        id=id or uuid4(),
        name=name,
        display_name=display_name,
        type=type,
        status=status,
        resource_type=resource_type,
        gpu_count=gpu_count,
        vram=vram,
        created_at=created_at or datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        created_by=created_by,
    )


def make_namespace_stats_counts(
    namespace: str = "test-namespace",
    status_counts: list[ResourceStatusCount] | None = None,
) -> NamespaceStatsCounts:
    """Create NamespaceStatsCounts for testing.

    Args:
        namespace: Namespace name
        status_counts: List of status counts

    Returns:
        NamespaceStatsCounts instance
    """
    counts = status_counts or [
        ResourceStatusCount(status=WorkloadStatus.RUNNING, count=3),
        ResourceStatusCount(status=WorkloadStatus.PENDING, count=2),
    ]
    total = sum(c.count for c in counts)

    return NamespaceStatsCounts(
        namespace=namespace,
        total=total,
        status_counts=counts,
    )


# ============================================================================
# AIM Factories
# ============================================================================


async def create_aim_service_db(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    namespace: str = "test-namespace",
    model: str = "llama3-8b",
    status: AIMServiceStatus = AIMServiceStatus.RUNNING,
    metric: OptimizationMetric | None = None,
    created_by: str = "test@example.com",
) -> AIMService:
    """Create an AIMService record in the database."""
    aim_service = AIMService(
        id=id or uuid4(),
        namespace=namespace,
        model=model,
        status=status.value if isinstance(status, AIMServiceStatus) else status,
        metric=metric.value if isinstance(metric, OptimizationMetric) else metric,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(aim_service)
    await session.flush()
    await session.refresh(aim_service)
    return aim_service


def make_aim_cluster_model(
    name: str = "llama3-8b",
    namespace: str = "test-namespace",
    image: str = "docker.io/amd/llama3:8b",
    status: AIMClusterModelStatus = AIMClusterModelStatus.READY,
    canonical_name: str | None = "meta/llama3-8b",
    tags: list[str] | None = None,
    hf_token_required: bool = False,
    as_response: bool = False,
) -> AIMClusterModelResource | AIMResponse:
    """Create an AIMClusterModelResource for testing.

    Args:
        as_response: If True, returns AIMResponse (for router tests).
    """
    data = {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"image": image},
        "status": {
            "status": status.value,
            "imageMetadata": {
                "model": {
                    "canonicalName": canonical_name,
                    "tags": tags if tags is not None else ["chat", "text-generation"],
                    "hfTokenRequired": hf_token_required,
                },
            },
        },
    }
    if as_response:
        return AIMResponse.model_validate(data)
    return AIMClusterModelResource.model_validate(data)


def make_aim_service_k8s(
    name: str | None = None,
    namespace: str = "test-namespace",
    workload_id: UUID | None = None,
    model_ref: str = "llama3-8b",
    replicas: int = 1,
    min_replicas: int | None = None,
    max_replicas: int | None = None,
    auto_scaling: dict[str, Any] | None = None,
    status: AIMServiceStatus = AIMServiceStatus.RUNNING,
    routing_path: str | None = None,
    with_httproute: bool = False,
    as_response: bool = False,
) -> AIMServiceResource | AIMServiceResponse:
    """Create an AIMServiceResource (K8s CRD) for testing.

    Args:
        with_httproute: If True, creates and attaches an HTTPRoute to the service
        as_response: If True, returns AIMServiceResponse (for router tests).
    """
    wid = workload_id or uuid4()
    svc_name = name or f"wb-aim-{str(wid)[:8]}"

    status_data: dict[str, Any] = {"status": status.value, "resolvedModel": {"name": model_ref}}
    if routing_path:
        status_data["routing"] = {"path": routing_path}

    spec_data: dict[str, Any] = {"model": {"name": model_ref}, "replicas": replicas}
    if min_replicas is not None:
        spec_data["minReplicas"] = min_replicas
    if max_replicas is not None:
        spec_data["maxReplicas"] = max_replicas
    if auto_scaling is not None:
        spec_data["autoScaling"] = auto_scaling

    resource = AIMServiceResource(
        metadata=K8sMetadata(
            name=svc_name,
            namespace=namespace,
            labels={WORKLOAD_ID_LABEL: str(wid)},
            annotations={SUBMITTER_ANNOTATION: "test@example.com"},
        ),
        spec=AIMServiceSpec.model_validate(spec_data),
        status=AIMServiceStatusFields.model_validate(status_data),
    )

    if with_httproute:
        resource.httproute = make_httproute(
            name=f"{svc_name}-route",
            namespace=namespace,
            service_name=f"{svc_name}-predictor",
            path=f"/{namespace}/{wid}",
        )

    if as_response:
        response = AIMServiceResponse.model_validate(resource.model_dump(by_alias=True))
        if with_httproute:
            response.httproute = resource.httproute
        return response
    return resource


def make_aim_cluster_service_template(
    name: str = "llama3-8b-latency",
    model_name: str = "llama3-8b",
    metric: str = "latency",
) -> AIMClusterServiceTemplateResource:
    """Create an AIMClusterServiceTemplateResource for testing."""
    return AIMClusterServiceTemplateResource.model_validate(
        {
            "metadata": {
                "name": name,
                "labels": {"aim.silogen.ai/aim-image": model_name},
            },
            "spec": {"modelName": model_name, "metric": metric},
            "status": {},
        }
    )


def make_httproute(
    name: str = "test-route",
    namespace: str = "test-namespace",
    service_name: str = "test-svc-predictor",
    port: int = 80,
    path: str = "/test-namespace/12345678-1234-5678-1234-567812345678",
) -> HTTPRouteResource:
    """Create an HTTPRouteResource for testing.

    Args:
        name: HTTPRoute name
        namespace: HTTPRoute namespace
        service_name: Backend service name
        port: Backend service port (omitted from URL if 80)
        path: Path prefix for external routing (format: /namespace/uuid)

    Returns:
        HTTPRouteResource with standard backend and path configuration
    """
    return HTTPRouteResource(
        metadata=K8sMetadata(name=name, namespace=namespace),
        spec=HTTPRouteSpec(
            rules=[
                HTTPRouteRule(
                    backend_refs=[HTTPRouteBackendRef(kind="Service", name=service_name, port=port)],
                    matches=[HTTPRouteMatch(path=HTTPRoutePathMatch(type="PathPrefix", value=path))],
                )
            ]
        ),
    )


# ============================================================================
# Dataset Factories
# ============================================================================


async def create_dataset(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "Test Dataset",
    description: str = "Test dataset description",
    path: str = "test-dataset.jsonl",
    type: DatasetType = DatasetType.FINETUNING,
    namespace: str = "test-namespace",
    created_by: str = "test@example.com",
) -> Dataset:
    """
    Create a test dataset in a namespace.

    Args:
        session: Database session
        id: Optional UUID for the dataset (auto-generated if not provided)
        name: Human-readable name for the dataset
        description: Description of the dataset
        path: Path to the dataset file
        type: Type of dataset (default: FINETUNING)
        namespace: Namespace the dataset belongs to
        created_by: Email of the user creating the dataset

    Returns:
        The created Dataset instance
    """
    dataset = Dataset(
        id=id or uuid4(),
        name=name,
        description=description,
        path=path,
        type=type,
        namespace=namespace,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(dataset)
    await session.flush()
    await session.refresh(dataset)
    return dataset


# ============================================================================
# Model Factories
# ============================================================================


def make_inference_model(
    id: UUID | None = None,
    name: str = "Test Model",
    namespace: str = "test-namespace",
    model_weights_path: str = "test-model.bin",
    canonical_name: str = "test/model",
    onboarding_status: OnboardingStatus = OnboardingStatus.ready,
    created_by: str = "test@example.com",
) -> InferenceModel:
    """
    Create an InferenceModel object for testing (not persisted).

    This factory creates a model object with proper timestamps without database interaction.
    Useful for router tests where you need to mock service layer returns.

    Args:
        id: Optional UUID for the model (auto-generated if not provided)
        name: Human-readable name for the model
        namespace: Namespace the model belongs to
        model_weights_path: Path to the model weights
        canonical_name: Canonical name of the model (e.g., "meta-llama/Llama-3.1-8B")
        onboarding_status: Onboarding status of the model
        created_by: Email of the user creating the model

    Returns:
        InferenceModel instance (not persisted to database)
    """

    now = datetime.now(UTC)
    return InferenceModel(
        id=id or uuid4(),
        name=name,
        namespace=namespace,
        model_weights_path=model_weights_path,
        canonical_name=canonical_name,
        onboarding_status=onboarding_status,
        created_by=created_by,
        updated_by=created_by,
        created_at=now,
        updated_at=now,
    )


async def create_inference_model(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "Test Model",
    namespace: str = "test-namespace",
    model_weights_path: str = "test-model.bin",
    canonical_name: str = "test/model",
    onboarding_status: OnboardingStatus = OnboardingStatus.ready,
    created_by: str = "test@example.com",
) -> InferenceModel:
    """
    Create a test inference model in a namespace.

    Args:
        session: Database session
        id: Optional UUID for the model (auto-generated if not provided)
        name: Human-readable name for the model
        namespace: Namespace the model belongs to
        model_weights_path: Path to the model weights
        canonical_name: Canonical name of the model (e.g., "meta-llama/Llama-3.1-8B")
        onboarding_status: Onboarding status of the model
        created_by: Email of the user creating the model

    Returns:
        The created InferenceModel instance
    """
    model = InferenceModel(
        id=id or uuid4(),
        name=name,
        namespace=namespace,
        model_weights_path=model_weights_path,
        canonical_name=canonical_name,
        onboarding_status=onboarding_status,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(model)
    await session.flush()
    await session.refresh(model)
    return model


# ============================================================================
# API Key Factories
# ============================================================================


async def create_api_key(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "test-api-key",
    namespace: str = "test-namespace",
    truncated_key: str = "aiwb_api_key_••••••••1234",
    cluster_auth_key_id: str | None = None,
    created_by: str = "test@example.com",
) -> ApiKey:
    """
    Create a test API key.

    Args:
        session: Database session
        id: Optional UUID for the API key (auto-generated if not provided)
        name: Human-readable name for the key
        namespace: Namespace the key belongs to
        truncated_key: Truncated key for display
        cluster_auth_key_id: Cluster Auth accessor ID. IMPORTANT: This has a unique
            constraint in the database. If None, a unique value is auto-generated
            using UUID. When creating multiple keys in a test, either:
            1. Let it auto-generate (default, recommended)
            2. Provide explicit unique values (e.g., "key-1", "key-2")
        created_by: Email of the user creating the key

    Returns:
        The created ApiKey instance

    Example:
        # Auto-generate unique cluster_auth_key_id (recommended)
        key1 = await create_api_key(session, name="Key 1")
        key2 = await create_api_key(session, name="Key 2")

        # Or be explicit about unique values
        key1 = await create_api_key(session, cluster_auth_key_id="explicit-id-1")
        key2 = await create_api_key(session, cluster_auth_key_id="explicit-id-2")
    """
    # Auto-generate unique cluster_auth_key_id to avoid constraint violations
    # when creating multiple keys in a single test
    if cluster_auth_key_id is None:
        cluster_auth_key_id = f"cluster-auth-{uuid4()}"

    api_key = ApiKey(
        id=id or uuid4(),
        name=name,
        namespace=namespace,
        truncated_key=truncated_key,
        cluster_auth_key_id=cluster_auth_key_id,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(api_key)
    await session.flush()
    await session.refresh(api_key)
    return api_key


# ============================================================================
# Chart, Overlay and Workload Factories
# ============================================================================


def make_mock_signature_file(content: str = "model_name: test\nreplicas: 1") -> UploadFile:
    """Create a mock signature UploadFile for testing.

    Args:
        content: YAML content for the signature file.

    Returns:
        An UploadFile with the given content.
    """
    return UploadFile(filename="signature.yaml", file=BytesIO(content.encode()))


def make_mock_chart_files(files_data: list[dict]) -> list[UploadFile]:
    """Create mock chart UploadFile objects for testing.

    Args:
        files_data: List of dicts with 'path' and 'content' keys.

    Returns:
        List of UploadFile objects.

    Example:
        files = make_mock_chart_files([
            {"path": "values.yaml", "content": "key: value"},
            {"path": "Chart.yaml", "content": "apiVersion: v2"},
        ])
    """
    upload_files = []
    for file_data in files_data:
        upload_file = UploadFile(filename=file_data["path"], file=BytesIO(file_data["content"].encode()))
        upload_files.append(upload_file)
    return upload_files


def make_chart_create_schema(
    name: str = "Test Chart",
    chart_type: WorkloadType = WorkloadType.INFERENCE,
    signature_content: str = "model_name: test\nreplicas: 1",
    files: list[dict[str, str]] | None = None,
    **kwargs: Any,
) -> ChartCreate:
    """Create a ChartCreate schema with mock files for testing.

    Combines make_mock_signature_file + make_mock_chart_files + ChartCreate
    into a single call to reduce test boilerplate.

    Args:
        name: Chart name.
        chart_type: Workload type for the chart.
        signature_content: YAML content for signature file.
        files: List of dicts with 'path' and 'content' keys, or None.
        **kwargs: Additional fields passed to ChartCreate (e.g., tags).

    Returns:
        A ChartCreate schema ready for use in tests.

    Example:
        schema = make_chart_create_schema(
            name="My Chart",
            files=[{"path": "values.yaml", "content": "key: value"}],
            tags=["test"],
        )
    """
    signature_file = make_mock_signature_file(signature_content)
    chart_files = make_mock_chart_files(files) if files else None
    return ChartCreate(name=name, type=chart_type, signature=signature_file, files=chart_files, **kwargs)


async def create_chart(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str = "test-chart",
    display_name: str | None = None,
    slug: str | None = None,
    chart_type: WorkloadType = WorkloadType.WORKSPACE,
    signature: dict[str, Any] | None = None,
    description: str | None = None,
    created_by: str = "test@example.com",
) -> Chart:
    """Create a test chart.

    Args:
        session: Database session
        id: Optional UUID for the chart (auto-generated if not provided)
        name: Chart name (must be unique)
        display_name: Human-readable display name
        slug: URL-friendly identifier
        chart_type: Type of workload this chart creates
        signature: Default values/schema for the chart
        description: Chart description
        created_by: Email of the user creating the chart

    Returns:
        The created Chart instance
    """
    chart = Chart(
        id=id or uuid4(),
        name=name,
        slug=slug,
        display_name=display_name or name.title(),
        type=chart_type,
        signature=signature or {},
        description=description,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(chart)
    await session.flush()
    await session.refresh(chart)
    return chart


async def create_overlay(
    session: AsyncSession,
    *,
    chart_id: UUID,
    canonical_name: str | None = None,
    chat_enabled: bool = True,
    overlay_data: dict[str, Any] | None = None,
    created_by: str = "test@example.com",
) -> Overlay:
    """
    Create a test overlay with optional chat capability.

    Args:
        session: Database session
        chart_id: UUID of the chart this overlay belongs to
        canonical_name: Canonical name of the model (e.g., "meta/llama3-8b"), or None for generic overlays
        chat_enabled: Whether chat capability is enabled (default True)
        overlay_data: Custom overlay data (if None, creates chat-enabled overlay)
        created_by: Email of the creator

    Returns:
        The created Overlay instance
    """
    if overlay_data is None:
        overlay_data = {"metadata": {"labels": {"chat": "true" if chat_enabled else "false"}}}

    overlay = Overlay(
        chart_id=chart_id,
        canonical_name=canonical_name,
        overlay=overlay_data,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(overlay)
    await session.flush()
    await session.refresh(overlay)
    return overlay


async def _create_namespace_isolation_data(session: AsyncSession, creator: str) -> None:
    """
    Create 'noise' data in other namespaces to automatically catch
    namespace isolation bugs.

    This function creates realistic test data in separate namespaces that
    should NEVER appear in namespace-scoped queries. If it does appear,
    it indicates a namespace isolation/data leakage bug.

    Uses session.info to cache data so it's only created once per session.
    """
    # Use session.info to cache - only create once per session
    if "_namespace_isolation_created" in session.info:
        return

    # Create noise namespace Alpha with workloads
    noise_chart_alpha = await create_chart(session, name="noise-chart-alpha", created_by=creator)
    await create_workload(
        session,
        namespace="noise-namespace-alpha",
        display_name="Noise Workload Alpha 1",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
        chart_id=noise_chart_alpha.id,
        submitter=creator,
        include_isolation_data=False,
    )
    await create_workload(
        session,
        namespace="noise-namespace-alpha",
        display_name="Noise Workload Alpha 2",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        chart_id=noise_chart_alpha.id,
        submitter=creator,
        include_isolation_data=False,
    )

    # Create noise namespace Beta with different workload patterns
    noise_chart_beta = await create_chart(session, name="noise-chart-beta", created_by=creator)
    await create_workload(
        session,
        namespace="noise-namespace-beta",
        display_name="Noise Workload Beta 1",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        chart_id=noise_chart_beta.id,
        submitter=creator,
        include_isolation_data=False,
    )
    await create_workload(
        session,
        namespace="noise-namespace-beta",
        display_name="Noise Workload Beta 2",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.FAILED,
        chart_id=noise_chart_beta.id,
        submitter=creator,
        include_isolation_data=False,
    )

    # Mark as created
    session.info["_namespace_isolation_created"] = True


async def create_workload(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    name: str | None = None,
    display_name: str = "Test Workload",
    namespace: str = "test-namespace",
    workload_type: WorkloadType = WorkloadType.WORKSPACE,
    status: WorkloadStatus = WorkloadStatus.PENDING,
    chart: Chart | None = None,
    chart_id: UUID | None = None,
    model_id: UUID | None = None,
    dataset_id: UUID | None = None,
    submitter: str = "test@example.com",
    manifest: str = DEFAULT_TEST_MANIFEST,
    include_isolation_data: bool = True,
) -> Workload:
    """
    Create a test workload.

    Args:
        session: Database session
        id: Optional UUID for the workload
        name: Workload name (auto-generated if not provided)
        display_name: Human-readable display name
        namespace: Namespace the workload belongs to
        workload_type: Type of workload
        status: Workload status
        chart: Chart object (if provided, chart_id is ignored)
        chart_id: Chart UUID (used if chart not provided)
        model_id: Optional inference model ID
        dataset_id: Optional dataset ID
        submitter: Email of the submitter
        manifest: Kubernetes manifest
        include_isolation_data: If True (default), automatically creates "noise"
            data in other namespaces to catch namespace isolation bugs.
            Set to False for non-namespace-scoped tests.

    Returns:
        The created Workload instance
    """
    workload_id = id or uuid4()

    # Generate name if not provided
    if name is None:
        name = f"mw-{workload_type.value}-{str(workload_id)[:8]}"

    # Determine chart_id
    if chart is not None:
        chart_id = chart.id
    elif chart_id is None:
        # Create a default chart
        default_chart = await create_chart(session, name=f"chart-{uuid4()}")
        chart_id = default_chart.id

    workload = Workload(
        id=workload_id,
        name=name,
        display_name=display_name,
        namespace=namespace,
        type=workload_type,
        status=status,
        chart_id=chart_id,
        model_id=model_id,
        dataset_id=dataset_id,
        created_by=submitter,
        updated_by=submitter,
        manifest=manifest,
    )
    session.add(workload)
    await session.flush()
    await session.refresh(workload)

    # Automatically create isolation noise data to catch namespace bugs
    if include_isolation_data:
        await _create_namespace_isolation_data(session, submitter)

    return workload


def make_workload_mock(
    *,
    workload_id: UUID | None = None,
    name: str = "test-workload",
    display_name: str = "Test Workload",
    namespace: str = "test-namespace",
    workload_type: WorkloadType = WorkloadType.WORKSPACE,
    status: WorkloadStatus = WorkloadStatus.RUNNING,
    chart_id: UUID | None = None,
    chart_name: str = "test-chart",
    model_id: UUID | None = None,
    dataset_id: UUID | None = None,
    created_by: str = "test@example.com",
    manifest: str = DEFAULT_TEST_MANIFEST,
) -> MagicMock:
    """
    Create a mock Workload for router-level testing.

    This creates a MagicMock with Workload spec for API layer tests
    that don't require database persistence.

    Args:
        workload_id: Workload UUID
        name: Workload Kubernetes name
        display_name: Human-readable display name
        namespace: Namespace the workload belongs to
        workload_type: Type of workload
        status: Workload status
        chart_id: UUID of the chart
        chart_name: Name of the chart (for mock chart relationship)
        model_id: Optional inference model ID
        dataset_id: Optional dataset ID
        created_by: Email of the creator
        manifest: Kubernetes manifest

    Returns:
        MagicMock configured to look like a Workload instance
    """
    mock = MagicMock(spec=Workload)
    mock.id = workload_id or uuid4()
    mock.name = name
    mock.display_name = display_name
    mock.namespace = namespace
    mock.type = workload_type
    mock.status = status
    mock.chart_id = chart_id or uuid4()
    mock.model_id = model_id
    mock.dataset_id = dataset_id
    mock.created_by = created_by
    mock.updated_by = created_by
    mock.manifest = manifest

    # Mock chart relationship
    mock.chart = MagicMock()
    mock.chart.id = mock.chart_id
    mock.chart.name = chart_name

    return mock
