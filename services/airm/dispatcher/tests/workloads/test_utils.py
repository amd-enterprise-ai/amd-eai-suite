# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
from kubernetes.client.models import V1Deployment, V1Job, V1ObjectMeta

from airm.messaging.schemas import (
    AIMServiceStatus,
    ConfigMapStatus,
    CronJobStatus,
    DaemonSetStatus,
    DeploymentStatus,
    JobStatus,
    KaiwoJobStatus,
    KaiwoServiceStatus,
    PodStatus,
    ServiceStatus,
    StatefulSetStatus,
    WorkloadComponentKind,
    WorkloadComponentStatusMessage,
)
from airm.workloads.constants import COMPONENT_ID_LABEL, WORKLOAD_ID_LABEL, WORKLOAD_SUBMITTER_MAX_LENGTH
from app.namespaces.constants import PROJECT_ID_LABEL
from app.workloads.constants import (
    AUTO_DISCOVERED_WORKLOAD_ANNOTATION,
    KUBERNETES_SERVICE_ACCOUNT_PREFIX,
    OIDC_USER_PREFIX,
    WORKLOAD_SUBMITTER_ANNOTATION,
)
from app.workloads.schemas import WorkloadComponentData
from app.workloads.utils import (
    __is_component_auto_discovered,
    __parse_workload_submitter,
    create_component_status_message,
    extract_workload_component_data,
    get_status_for_aim_service,
    get_status_for_config_map,
    get_status_for_cron_job,
    get_status_for_daemon_set,
    get_status_for_deployment,
    get_status_for_job,
    get_status_for_kaiwo_job,
    get_status_for_kaiwo_service,
    get_status_for_pod,
    get_status_for_service,
    get_status_for_stateful_set,
)


@pytest.mark.parametrize(
    "event_type, resource_type, active, succeeded, completions, failed, expected_status, expected_reason",
    [
        # Job status tests
        ("ADDED", "Job", None, None, None, None, JobStatus.PENDING.value, "Job has not started yet"),
        ("MODIFIED", "Job", 1, 0, 0, 0, JobStatus.RUNNING.value, "Job is actively running."),
        (
            "MODIFIED",
            "Job",
            0,
            1,
            1,
            0,
            JobStatus.COMPLETE.value,
            "Job has completed all desired pods successfully.",
        ),
        ("MODIFIED", "Job", 0, 0, 0, 1, JobStatus.FAILED.value, "Job has failed."),
        ("MODIFIED", "Job", None, None, None, None, JobStatus.PENDING, "Job has not started yet"),
    ],
)
def test_get_status_for_job(
    event_type, resource_type, active, succeeded, completions, failed, expected_status, expected_reason
):
    """Test different job statuses."""
    status_mock = Mock()
    status_mock.active = active
    status_mock.succeeded = succeeded
    status_mock.failed = failed

    spec_mock = Mock()
    spec_mock.suspend = False
    spec_mock.completions = completions

    resource_mock = Mock()
    resource_mock.status = status_mock
    resource_mock.spec = spec_mock

    status, reason = get_status_for_job(resource_mock, event_type)
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


@pytest.mark.parametrize(
    "event_type, resource_type, ready_replicas, replicas, conditions, expected_status, expected_reason",
    [
        # Deployment tests
        ("MODIFIED", "Deployment", 0, 3, None, DeploymentStatus.PENDING.value, "No replicas are ready."),
        ("MODIFIED", "Deployment", 1, 3, None, DeploymentStatus.PENDING.value, "Scaling up: 1 ready of 3 total."),
        ("MODIFIED", "Deployment", 3, 3, None, DeploymentStatus.RUNNING.value, "All replicas are running."),
    ],
)
def test_get_status_for_deployment(
    event_type, resource_type, ready_replicas, replicas, conditions, expected_status, expected_reason
):
    """Test different deployment statuses."""
    resource_mock = Mock()
    resource_mock.status.ready_replicas = ready_replicas
    resource_mock.status.replicas = replicas
    resource_mock.status.conditions = conditions

    status, reason = get_status_for_deployment(resource_mock, event_type)
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


def create_mock_resource(kind="ConfigMap", metadata_labels=None):
    metadata = MagicMock()
    metadata.name = "sample"
    metadata.labels = metadata_labels or {}

    resource = MagicMock()
    resource.kind = kind
    resource.metadata = metadata
    return resource


@pytest.mark.parametrize(
    "event_type, expected_status, expected_reason",
    [
        ("ADDED", ConfigMapStatus.ADDED.value, "Resource has been added to the cluster."),
        ("FOO", None, "Config status could not be determined."),
    ],
)
def test_get_status_for_config_map(event_type, expected_status, expected_reason):
    resource = create_mock_resource()

    status, reason = get_status_for_config_map(resource, event_type)
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


@pytest.mark.parametrize(
    "ingress, expected_status, expected_reason",
    [
        ([MagicMock(ip="1.2.3.4")], ServiceStatus.READY, "LoadBalancer is provisioned with ingress."),
        ([], ServiceStatus.PENDING, "Waiting for LoadBalancer ingress."),
    ],
)
def test_get_status_for_service_load_balancer(ingress, expected_status, expected_reason):
    resource = create_mock_resource(kind="Service")
    resource.spec.type = "LoadBalancer"
    resource.status.load_balancer.ingress = ingress

    status, reason = get_status_for_service(resource, "ADDED")
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


def test_get_status_for_service_cluster_ip():
    resource = create_mock_resource(kind="Service")
    resource.spec.type = "ClusterIP"
    resource.spec.cluster_ip = "10.0.0.1"

    status, reason = get_status_for_service(resource, "ADDED")
    assert status == ServiceStatus.READY
    assert "service is configured properly." in reason.lower()


@pytest.mark.parametrize(
    "event_type, status, expected_status, expected_reason",
    [
        ("MODIFIED", {"status": "PENDING"}, KaiwoJobStatus.PENDING, f"Job status: {KaiwoJobStatus.PENDING.value}"),
        ("MODIFIED", {}, None, "Status information could not be determined"),
    ],
)
def test_kaiwo_job_status(event_type, status, expected_status, expected_reason):
    resource = {"kind": "KaiwoJob", "metadata": {"name": "test-job"}, "status": status}

    result_status, reason = get_status_for_kaiwo_job(resource, event_type)

    assert result_status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


def test_kaiwo_job_with_non_dict_resource():
    resource = MagicMock()

    result_status, result_message = get_status_for_kaiwo_job(resource, "MODIFIED")

    assert result_status is None
    assert result_message == "Status information could not be determined"


@pytest.mark.parametrize(
    "event_type, status, expected_status, expected_reason",
    [
        (
            "MODIFIED",
            {"status": "RUNNING"},
            KaiwoServiceStatus.RUNNING,
            f"Service status: {KaiwoServiceStatus.RUNNING.value}",
        ),
        ("MODIFIED", {}, None, "Status information could not be determined"),
    ],
)
def test_kaiwo_service_status(event_type, status, expected_status, expected_reason):
    resource = {"kind": "KaiwoJob", "metadata": {"name": "test-service"}, "status": status}

    result_status, reason = get_status_for_kaiwo_service(resource, event_type)

    assert result_status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


def test_kaiwo_service_with_non_dict_resource():
    resource = MagicMock()

    result_status, result_message = get_status_for_kaiwo_service(resource, "MODIFIED")

    assert result_status is None
    assert result_message == "Status information could not be determined"


@pytest.mark.parametrize(
    "event_type, status, expected_status, expected_reason",
    [
        (
            "MODIFIED",
            {"status": "Pending"},
            AIMServiceStatus.PENDING,
            f"AIM service status: {AIMServiceStatus.PENDING.value}",
        ),
        (
            "MODIFIED",
            {"status": "Starting"},
            AIMServiceStatus.STARTING,
            f"AIM service status: {AIMServiceStatus.STARTING.value}",
        ),
        (
            "MODIFIED",
            {"status": "Running"},
            AIMServiceStatus.RUNNING,
            f"AIM service status: {AIMServiceStatus.RUNNING.value}",
        ),
        (
            "MODIFIED",
            {"status": "Failed"},
            AIMServiceStatus.FAILED,
            f"AIM service status: {AIMServiceStatus.FAILED.value}",
        ),
        (
            "MODIFIED",
            {"status": "Degraded"},
            AIMServiceStatus.DEGRADED,
            f"AIM service status: {AIMServiceStatus.DEGRADED.value}",
        ),
        ("MODIFIED", {}, None, "Status information could not be determined"),
        ("MODIFIED", {"status": "INVALID_STATUS"}, None, "Status information could not be determined"),
    ],
)
def test_aim_service_status(event_type, status, expected_status, expected_reason):
    resource = {"kind": "AIMService", "metadata": {"name": "test-aim-service"}, "status": status}

    result_status, reason = get_status_for_aim_service(resource, event_type)

    assert result_status == expected_status, f"Expected status {expected_status}, got {result_status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


def test_aim_service_with_non_dict_resource():
    resource = MagicMock()

    result_status, result_message = get_status_for_aim_service(resource, "MODIFIED")

    assert result_status is None
    assert result_message == "Status information could not be determined"


@pytest.mark.parametrize(
    "replicas, current_replicas, ready_replicas, available_replicas, expected_status, expected_reason",
    [
        (0, 0, 0, 0, StatefulSetStatus.PENDING, "StatefulSet has no replicas defined."),
        (3, 1, 0, 0, StatefulSetStatus.PENDING, "StatefulSet is scaling up (1/3 replicas)"),
        (2, 2, 2, 2, StatefulSetStatus.RUNNING, "StatefulSet is ready (2/2 replicas)"),
        (3, 3, 2, 2, StatefulSetStatus.PENDING, "StatefulSet partially ready (2/3 ready)"),
    ],
)
def test_get_status_for_stateful_set(
    replicas, current_replicas, ready_replicas, available_replicas, expected_status, expected_reason
):
    status_mock = Mock()
    status_mock.ready_replicas = ready_replicas
    status_mock.current_replicas = current_replicas
    status_mock.available_replicas = available_replicas

    spec_mock = Mock()
    spec_mock.replicas = replicas

    resource_mock = Mock()
    resource_mock.status = status_mock
    resource_mock.spec = spec_mock

    status, reason = get_status_for_stateful_set(resource_mock, None)
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


@pytest.mark.parametrize(
    "desired, current, ready, available, expected_status, expected_reason",
    [
        (3, 0, 0, 0, DaemonSetStatus.PENDING, "DaemonSet has no current pods scheduled."),
        (3, 3, 3, 3, DaemonSetStatus.RUNNING, "DaemonSet is ready (3/3 pods ready)"),
        (3, 3, 2, 2, DaemonSetStatus.PENDING, "DaemonSet partially ready (2/3 pods ready)"),
        (3, 2, 0, 0, DaemonSetStatus.PENDING, "DaemonSet pods starting (2/3 scheduled)"),
    ],
)
def test_get_status_for_daemon_set(desired, current, ready, available, expected_status, expected_reason):
    status_mock = Mock()
    status_mock.desired_number_scheduled = desired
    status_mock.current_number_scheduled = current
    status_mock.number_ready = ready
    status_mock.number_available = available

    resource_mock = Mock()
    resource_mock.status = status_mock

    status, reason = get_status_for_daemon_set(resource_mock, None)
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


@pytest.mark.parametrize(
    "suspend, active, expected_status, expected_reason",
    [
        # Suspended
        (True, [], CronJobStatus.SUSPENDED, "CronJob is currently suspended"),
        # Running with active jobs
        (False, [Mock(), Mock()], CronJobStatus.RUNNING, "CronJob has 2 active job(s) running"),
        # Ready but hasn't run yet
        (False, [], CronJobStatus.READY, "CronJob is scheduled but hasn't run yet"),
    ],
)
def test_get_status_for_cron_job(suspend, active, expected_status, expected_reason):
    spec_mock = Mock()
    spec_mock.suspend = suspend

    status_mock = Mock()
    status_mock.active = active

    resource_mock = Mock()
    resource_mock.spec = spec_mock
    resource_mock.status = status_mock

    status, reason = get_status_for_cron_job(resource_mock, None)
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


@pytest.mark.parametrize(
    "phase, expected_status, expected_reason",
    [
        ("Pending", PodStatus.PENDING, "Pod is pending scheduling or initialization"),
        ("Running", PodStatus.RUNNING, "Pod is running"),
        ("Succeeded", PodStatus.COMPLETE, "Pod completed successfully"),
        ("Failed", PodStatus.FAILED, "Pod has failed"),
        ("UnknownPhase", None, "Status information could not be determined"),
    ],
)
def test_get_status_for_pod(phase, expected_status, expected_reason):
    status_mock = Mock()
    status_mock.phase = phase

    resource_mock = Mock()
    resource_mock.status = status_mock

    status, reason = get_status_for_pod(resource_mock, None)
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    assert reason == expected_reason, f"Expected reason '{expected_reason}', got '{reason}'"


def test_extract_resource_data_from_dictionary():
    """Test extracting data from a dictionary representation of a resource."""
    # Create a dictionary resource
    project_id = uuid.uuid4()
    workload_id = uuid.uuid4()
    component_id = uuid.uuid4()

    resource = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "test-deployment",
            "namespace": "default",
            "labels": {
                WORKLOAD_ID_LABEL: str(workload_id),
                COMPONENT_ID_LABEL: str(component_id),
                PROJECT_ID_LABEL: str(project_id),
                "other-label": "other-value",
            },
            "annotations": {WORKLOAD_SUBMITTER_ANNOTATION: "test-submitter"},
        },
    }

    # Extract data
    result = extract_workload_component_data(resource)

    # Verify the extracted data
    assert result.name == "test-deployment"
    assert result.kind == "Deployment"
    assert result.api_version == "apps/v1"
    assert result.workload_id == workload_id
    assert result.component_id == component_id
    assert result.project_id == project_id
    assert result.submitter == "test-submitter"


def test_extract_resource_data_from_k8s_object():
    """Test extracting data from a Kubernetes client object."""
    # Create a metadata mock
    project_id = uuid.uuid4()
    workload_id = uuid.uuid4()
    component_id = uuid.uuid4()

    metadata = MagicMock(spec=V1ObjectMeta)
    metadata.name = "test-deployment"
    metadata.namespace = "default"
    metadata.labels = {
        WORKLOAD_ID_LABEL: str(workload_id),
        COMPONENT_ID_LABEL: str(component_id),
        PROJECT_ID_LABEL: str(project_id),
        "other-label": "other-value",
    }
    metadata.annotations = {WORKLOAD_SUBMITTER_ANNOTATION: "test-submitter"}

    # Create a deployment mock
    deployment = MagicMock(spec=V1Deployment)
    deployment.metadata = metadata
    deployment.kind = "Deployment"
    deployment.api_version = "apps/v1"

    # Extract data
    result = extract_workload_component_data(deployment)

    # Verify the extracted data
    assert result.name == "test-deployment"
    assert result.kind == "Deployment"
    assert result.api_version == "apps/v1"
    assert result.workload_id == workload_id
    assert result.component_id == component_id
    assert result.project_id == project_id
    assert result.submitter == "test-submitter"


def test_extract_resource_data_without_submitter():
    resource = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "test-deployment",
            "namespace": "default",
            "labels": {
                WORKLOAD_ID_LABEL: str(uuid.uuid4()),
                COMPONENT_ID_LABEL: str(uuid.uuid4()),
                PROJECT_ID_LABEL: str(uuid.uuid4()),
            },
        },
    }

    # Extract data
    result = extract_workload_component_data(resource)

    assert result.submitter is None


def test_extract_resource_data_with_missing_fields_exception():
    """Test extracting data with missing fields from a dictionary."""
    # Dictionary with missing fields
    resource = {
        "kind": "ConfigMap",
        "metadata": {
            "name": "test-config"
            # No labels
        },
    }

    with pytest.raises(TypeError):
        extract_workload_component_data(resource)


def test_extract_resource_data_with_missing_fields_k8s_object():
    """Test extracting data with missing fields from a K8s object."""
    # Create a metadata mock with minimal info
    metadata = MagicMock(spec=V1ObjectMeta)
    metadata.name = "test-job"
    metadata.labels = {}  # Empty labels

    # Create a job mock with minimal info
    job = MagicMock(spec=V1Job)
    job.metadata = metadata
    job.kind = "Job"

    with pytest.raises(TypeError):
        extract_workload_component_data(job)


def test_create_component_status_message():
    """Test creating a status message from a dictionary resource."""
    # Test data
    workload_id = "8330d6b8-0b68-47f5-a46f-25c32b4a7cef"
    component_id = "4fbb62ee-e65c-4500-a252-8e0c395c4e84"
    project_id = "12345678-1234-5678-1234-567812345678"

    # Create a dictionary resource
    workload_component_data = WorkloadComponentData(
        workload_id=workload_id,
        component_id=component_id,
        project_id=project_id,
        kind=WorkloadComponentKind.DEPLOYMENT,
        name="test-deployment",
        api_version="apps/v1",
        auto_discovered=False,
    )

    # Create status message
    status = "Running"
    reason = "Deployment is running well"
    message = create_component_status_message(workload_component_data, status, reason)

    # Verify the message
    assert isinstance(message, WorkloadComponentStatusMessage)
    assert message.name == "test-deployment"
    assert message.kind == "Deployment"
    assert message.api_version == "apps/v1"
    assert str(message.workload_id) == workload_id
    assert str(message.id) == component_id
    assert message.status == status
    assert message.status_reason == reason
    assert message.message_type == "workload_component_status_update"
    assert isinstance(message.updated_at, datetime)


def test_create_component_status_message_with_empty_reason():
    """Test creating a status message with an empty reason."""
    # Test data
    workload_id = "8330d6b8-0b68-47f5-a46f-25c32b4a7cef"
    component_id = "4fbb62ee-e65c-4500-a252-8e0c395c4e84"
    project_id = "12345678-1234-5678-1234-567812345678"

    workload_component_data = WorkloadComponentData(
        workload_id=workload_id,
        component_id=component_id,
        project_id=project_id,
        kind=WorkloadComponentKind.KAIWO_JOB,
        name="job",
        api_version="v1alpha1",
        auto_discovered=True,
    )
    # Create status message with None reason
    status = "Added"
    message = create_component_status_message(workload_component_data, status, None)

    # Verify the default reason
    assert message.status_reason == f"Status: {status}"


@pytest.mark.parametrize(
    "annotations, expected_response",
    [
        (
            {},
            False,
        ),
        (
            {AUTO_DISCOVERED_WORKLOAD_ANNOTATION: "false"},
            False,
        ),
        (
            {AUTO_DISCOVERED_WORKLOAD_ANNOTATION: "true"},
            True,
        ),
    ],
)
def test_is_component_auto_discovered(annotations, expected_response):
    assert __is_component_auto_discovered(annotations) == expected_response


@pytest.mark.parametrize(
    "annotations, expected_response",
    [
        ({}, None),
        ({WORKLOAD_SUBMITTER_ANNOTATION: "alice"}, "alice"),
        ({WORKLOAD_SUBMITTER_ANNOTATION: f"{KUBERNETES_SERVICE_ACCOUNT_PREFIX}bob"}, "bob"),
        ({WORKLOAD_SUBMITTER_ANNOTATION: f"{OIDC_USER_PREFIX}bob"}, "bob"),
        (
            {
                WORKLOAD_SUBMITTER_ANNOTATION: f"{KUBERNETES_SERVICE_ACCOUNT_PREFIX}"
                + "x" * (WORKLOAD_SUBMITTER_MAX_LENGTH + 10)
            },
            "x" * WORKLOAD_SUBMITTER_MAX_LENGTH,
        ),
        (
            {WORKLOAD_SUBMITTER_ANNOTATION: f"{OIDC_USER_PREFIX}" + "x" * (WORKLOAD_SUBMITTER_MAX_LENGTH + 10)},
            "x" * WORKLOAD_SUBMITTER_MAX_LENGTH,
        ),
    ],
)
def test_parse_workload_submitter(annotations, expected_response):
    assert __parse_workload_submitter(annotations) == expected_response
