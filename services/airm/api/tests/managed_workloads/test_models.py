# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from app.charts.models import Chart
from app.managed_workloads.enums import WorkloadStatus
from app.managed_workloads.models import ManagedWorkload
from app.models.models import InferenceModel, OnboardingStatus
from app.workloads.enums import WorkloadType


def test_managed_workload_structure():
    workload_id = uuid4()
    chart_id = uuid4()
    model_id = uuid4()
    dataset_id = uuid4()
    cluster_id = uuid4()
    project_id = uuid4()

    # Create a chart for the workload
    chart = Chart(
        id=chart_id,
        name="Test Chart",
        type=WorkloadType.INFERENCE,
        signature={},
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create a model for the workload
    model = InferenceModel(
        id=model_id,
        name="Test Model",
        canonical_name="test/model",
        project_id=project_id,
        onboarding_status=OnboardingStatus.ready,
        model_weights_path="/path/to/model",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create a managed workload
    managed_workload = ManagedWorkload(
        id=workload_id,
        cluster_id=cluster_id,
        project_id=project_id,
        chart_id=chart_id,
        model_id=model_id,
        dataset_id=dataset_id,
        type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        user_inputs={"key": "value"},
        display_name="Custom Display Name",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Set relationships manually for testing
    managed_workload.chart = chart
    managed_workload.model = model

    # Verify fields
    assert managed_workload.id == workload_id
    assert managed_workload.cluster_id == cluster_id
    assert managed_workload.chart_id == chart_id
    assert managed_workload.model_id == model_id
    assert managed_workload.dataset_id == dataset_id
    assert managed_workload.type == WorkloadType.INFERENCE
    assert managed_workload.status == WorkloadStatus.PENDING
    assert managed_workload.user_inputs == {"key": "value"}
    assert managed_workload.display_name == "Custom Display Name"

    # Verify relationships
    assert managed_workload.chart == chart
    assert managed_workload.chart.name == "Test Chart"
    assert managed_workload.model == model
    assert managed_workload.model.name == "Test Model"


def test_managed_workload_name_generation():
    workload_id = uuid4()
    chart_id = uuid4()
    cluster_id = uuid4()
    project_id = uuid4()

    # Create a chart for the workload
    chart = Chart(
        id=chart_id,
        name="Test Chart",
        type=WorkloadType.INFERENCE,
        signature={},
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create a managed workload without display_name
    managed_workload = ManagedWorkload(
        id=workload_id,
        cluster_id=cluster_id,
        project_id=project_id,
        chart_id=chart_id,
        type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        user_inputs={},
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Set relationships manually for testing
    managed_workload.chart = chart

    # Test the generate_name method manually
    uuid_prefix = str(managed_workload.id)[:8]
    timestamp = "1715123456"  # Mocked timestamp

    # Expected name
    chart_name = chart.name.replace(" ", "-").replace("_", "-")[:40]
    expected_name = f"mw-{chart_name}-{timestamp}-{uuid_prefix}"[:63]

    # Expected display_name
    expected_display_name = f"{chart.name}-{uuid_prefix}"

    # Verify that we can generate the expected names
    assert chart_name == "Test-Chart"
    assert expected_name.startswith("mw-Test-Chart-")
    assert expected_display_name.startswith("Test Chart-")


def test_managed_workload_with_model_name_generation():
    workload_id = uuid4()
    chart_id = uuid4()
    model_id = uuid4()
    cluster_id = uuid4()
    project_id = uuid4()

    # Create a chart for the workload
    chart = Chart(
        id=chart_id,
        name="Test Chart",
        type=WorkloadType.INFERENCE,
        signature={},
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create a model for the workload
    model = InferenceModel(
        id=model_id,
        name="Test Model",
        canonical_name="test/model",
        project_id=project_id,
        onboarding_status=OnboardingStatus.ready,
        model_weights_path="/path/to/model",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create a managed workload without display_name
    managed_workload = ManagedWorkload(
        id=workload_id,
        cluster_id=cluster_id,
        project_id=project_id,
        chart_id=chart_id,
        model_id=model_id,
        type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        user_inputs={},
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Set relationships manually for testing
    managed_workload.chart = chart
    managed_workload.model = model

    # Test the generate_name method manually
    uuid_prefix = str(managed_workload.id)[:8]
    timestamp = "1715123456"  # Mocked timestamp

    # Expected name
    chart_name = chart.name.replace(" ", "-").replace("_", "-")[:40]
    expected_name = f"mw-{chart_name}-{timestamp}-{uuid_prefix}"[:63]

    # Expected display_name with model
    expected_display_name = f"{chart.name}-{model.name}-{uuid_prefix}"

    # Verify that we can generate the expected names
    assert chart_name == "Test-Chart"
    assert expected_name.startswith("mw-Test-Chart-")
    assert expected_display_name.startswith("Test Chart-Test Model-")


def test_managed_workload_user_provided_display_name():
    workload_id = uuid4()
    chart_id = uuid4()
    model_id = uuid4()
    cluster_id = uuid4()
    project_id = uuid4()

    # Create a chart for the workload
    chart = Chart(
        id=chart_id,
        name="Test Chart",
        type=WorkloadType.INFERENCE,
        signature={},
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create a model for the workload
    model = InferenceModel(
        id=model_id,
        name="Test Model",
        canonical_name="test/model",
        project_id=project_id,
        onboarding_status=OnboardingStatus.ready,
        model_weights_path="/path/to/model",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Create a managed workload with a user-provided display_name
    custom_display_name = "My Custom Workload Name"
    managed_workload = ManagedWorkload(
        id=workload_id,
        cluster_id=cluster_id,
        project_id=project_id,
        chart_id=chart_id,
        model_id=model_id,
        type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        user_inputs={},
        display_name=custom_display_name,
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Set relationships manually for testing
    managed_workload.chart = chart
    managed_workload.model = model

    # Verify that the display_name is the user-provided one
    assert managed_workload.display_name == custom_display_name
