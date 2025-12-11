# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime
from typing import Any

from kubernetes.client.models import V1CronJob, V1DaemonSet, V1Deployment, V1Job, V1Pod, V1Service, V1StatefulSet
from loguru import logger

from airm.messaging.schemas import (
    AIMServiceStatus,
    AutoDiscoveredWorkloadComponentMessage,
    CommonComponentStatus,
    ConfigMapStatus,
    CronJobStatus,
    DaemonSetStatus,
    DeploymentStatus,
    HTTPRouteStatus,
    IngressStatus,
    JobStatus,
    KaiwoJobStatus,
    KaiwoServiceStatus,
    PodStatus,
    ServiceStatus,
    StatefulSetStatus,
    WorkloadComponentKind,
    WorkloadComponentStatus,
    WorkloadComponentStatusMessage,
)
from airm.workloads.constants import (
    COMPONENT_ID_LABEL,
    PROJECT_ID_LABEL,
    WORKLOAD_ID_LABEL,
    WORKLOAD_SUBMITTER_MAX_LENGTH,
)

from ..utilities.attribute_utils import get_attr_or_key
from .constants import (
    AUTO_DISCOVERED_WORKLOAD_ANNOTATION,
    KUBERNETES_SERVICE_ACCOUNT_PREFIX,
    OIDC_USER_PREFIX,
    WORKLOAD_SUBMITTER_ANNOTATION,
)
from .schemas import WorkloadComponentData

standard_event_status_mappings = {
    "DELETED": (CommonComponentStatus.DELETED, "Resource has been removed from the cluster."),
}


def get_status_for_job(resource: V1Job, _: Any) -> tuple[CommonComponentStatus | JobStatus | None, str]:
    status = resource.status
    spec = resource.spec

    if spec.suspend:
        return JobStatus.SUSPENDED, "Job is currently suspended"

    active = status.active or 0
    if isinstance(active, int) and active > 0:
        return JobStatus.RUNNING, "Job is actively running."

    succeeded = status.succeeded or 0
    completions = spec.completions or 1
    if succeeded >= completions:
        return JobStatus.COMPLETE, "Job has completed all desired pods successfully."

    failed = status.failed or 0
    if isinstance(failed, int) and failed > 0:
        return JobStatus.FAILED, "Job has failed."

    return JobStatus.PENDING, "Job has not started yet"


def get_status_for_deployment(
    resource: V1Deployment, _: Any
) -> tuple[CommonComponentStatus | DeploymentStatus | None, str]:
    status = resource.status
    if not status:
        return None, "Deployment status is missing."

    # Get replicas and ready_replicas safely
    ready_replicas = status.ready_replicas or 0
    replicas = status.replicas or 0

    if ready_replicas == 0:
        return DeploymentStatus.PENDING, "No replicas are ready."
    elif ready_replicas < replicas:
        return DeploymentStatus.PENDING, f"Scaling up: {ready_replicas} ready of {replicas} total."
    elif ready_replicas == replicas:
        return DeploymentStatus.RUNNING, "All replicas are running."
    return None, "Deployment status could not be determined."


def get_status_for_config_map(_: Any, event_type: str) -> tuple[CommonComponentStatus | ConfigMapStatus | None, str]:
    if event_type == "ADDED":
        return ConfigMapStatus.ADDED.value, "Resource has been added to the cluster."
    elif event_type == "DELETED":
        return ConfigMapStatus.DELETED.value, "Resource has been deleted from the cluster."

    return None, "Config status could not be determined."


def get_status_for_service(resource: V1Service, _: Any) -> tuple[CommonComponentStatus | ServiceStatus | None, str]:
    # Basic integrity check
    if not resource.spec.ports:
        return ServiceStatus.INVALID, "Service has no defined ports."

    if not resource.spec.selector:
        return ServiceStatus.INVALID, "Service has no selector defined."

    # Check if it's a LoadBalancer service and has been provisioned
    if resource.spec.type == "LoadBalancer":
        ingress = getattr(resource.status.load_balancer, "ingress", [])
        if ingress:
            return ServiceStatus.READY, "LoadBalancer is provisioned with ingress."
        else:
            return ServiceStatus.PENDING, "Waiting for LoadBalancer ingress."

    # Fallback success
    return ServiceStatus.READY, "Service is configured properly."


def get_status_for_kaiwo_job(resource: Any, _: Any) -> tuple[CommonComponentStatus | KaiwoJobStatus | None, str]:
    status_value = resource.get("status", {}).get("status") if isinstance(resource, dict) else None
    try:
        status = KaiwoJobStatus(status_value)
        return status.value, f"Job status: {status.value}"
    except (ValueError, KeyError):
        logger.warning(f"Could not determine job status from resource, status_value={status_value}")
        return None, "Status information could not be determined"


def get_status_for_kaiwo_service(
    resource: Any, _: Any
) -> tuple[CommonComponentStatus | KaiwoServiceStatus | None, str]:
    status_value = resource.get("status", {}).get("status") if isinstance(resource, dict) else None
    try:
        status = KaiwoServiceStatus(status_value)
        return status.value, f"Service status: {status.value}"
    except (ValueError, KeyError):
        logger.warning(f"Could not determine service status from resource, status_value={status_value}")
        return None, "Status information could not be determined"


def get_status_for_aim_service(resource: Any, _: Any) -> tuple[CommonComponentStatus | AIMServiceStatus | None, str]:
    status_value = resource.get("status", {}).get("status") if isinstance(resource, dict) else None
    try:
        status = AIMServiceStatus(status_value)
        return status.value, f"AIM service status: {status.value}"
    except (ValueError, KeyError):
        logger.warning(f"Could not determine AIM service status from resource, status_value={status_value}")
        return None, "Status information could not be determined"


def get_status_for_http_route(_: Any, event_type: str) -> tuple[CommonComponentStatus | HTTPRouteStatus | None, str]:
    if event_type == "ADDED":
        return HTTPRouteStatus.ADDED.value, "HTTPRoute resource has been added to the cluster."

    return None, "HTTPRoute status could not be determined."


def get_status_for_ingress(_: Any, event_type: str) -> tuple[CommonComponentStatus | IngressStatus | None, str]:
    if event_type == "ADDED":
        return IngressStatus.ADDED.value, "Ingress resource has been added to the cluster."

    return None, "Ingress status could not be determined."


def get_status_for_stateful_set(
    resource: V1StatefulSet, _: Any
) -> tuple[CommonComponentStatus | StatefulSetStatus | None, str]:
    status = resource.status
    spec = resource.spec

    replicas = spec.replicas or 0
    ready_replicas = status.ready_replicas or 0
    current_replicas = status.current_replicas or 0
    available_replicas = status.available_replicas or 0

    if replicas == 0:
        return StatefulSetStatus.PENDING, "StatefulSet has no replicas defined."
    if current_replicas < replicas:
        return StatefulSetStatus.PENDING, f"StatefulSet is scaling up ({current_replicas}/{replicas} replicas)"
    if ready_replicas == replicas and available_replicas == replicas:
        return StatefulSetStatus.RUNNING, f"StatefulSet is ready ({ready_replicas}/{replicas} replicas)"
    if current_replicas > 0:
        return StatefulSetStatus.PENDING, f"StatefulSet partially ready ({ready_replicas}/{replicas} ready)"

    return None, "StatefulSet status could not be determined"


def get_status_for_daemon_set(
    resource: V1DaemonSet, _: Any
) -> tuple[CommonComponentStatus | DaemonSetStatus | None, str]:
    status = resource.status

    # Get daemon counts
    desired_number_scheduled = status.desired_number_scheduled or 0
    current_number_scheduled = status.current_number_scheduled or 0
    number_ready = status.number_ready or 0
    number_available = status.number_available or 0

    if current_number_scheduled == 0:
        return DaemonSetStatus.PENDING, "DaemonSet has no current pods scheduled."

    if (
        number_ready == desired_number_scheduled
        and number_available == desired_number_scheduled
        and current_number_scheduled == desired_number_scheduled
    ):
        return DaemonSetStatus.RUNNING, f"DaemonSet is ready ({number_ready}/{desired_number_scheduled} pods ready)"

    if number_ready > 0:
        return (
            DaemonSetStatus.PENDING,
            f"DaemonSet partially ready ({number_ready}/{desired_number_scheduled} pods ready)",
        )
    if current_number_scheduled > 0:
        return (
            DaemonSetStatus.PENDING,
            f"DaemonSet pods starting ({current_number_scheduled}/{desired_number_scheduled} scheduled)",
        )

    return None, "DaemonSet status could not be determined"


def get_status_for_cron_job(resource: V1CronJob, _: Any) -> tuple[CommonComponentStatus | CronJobStatus | None, str]:
    status = resource.status
    spec = resource.spec
    if spec.suspend:
        return CronJobStatus.SUSPENDED, "CronJob is currently suspended"

    active = status.active or []
    if len(active) > 0:
        return CronJobStatus.RUNNING, f"CronJob has {len(active)} active job(s) running"

    return CronJobStatus.READY, "CronJob is scheduled but hasn't run yet"


def get_status_for_pod(resource: V1Pod, _: Any) -> tuple[CommonComponentStatus | PodStatus | None, str]:
    status = resource.status

    phase = status.phase
    if phase == "Pending":
        return PodStatus.PENDING, "Pod is pending scheduling or initialization"
    if phase == "Running":
        return PodStatus.RUNNING, "Pod is running"
    if phase == "Succeeded":
        return PodStatus.COMPLETE, "Pod completed successfully"
    if phase == "Failed":
        return PodStatus.FAILED, "Pod has failed"
    return None, "Status information could not be determined"


def __is_component_auto_discovered(annotations: dict[str, str]) -> bool:
    return annotations.get(AUTO_DISCOVERED_WORKLOAD_ANNOTATION, "false") == "true"


def __parse_workload_submitter(annotations: dict[str, str]) -> str | None:
    submitter = annotations.get(WORKLOAD_SUBMITTER_ANNOTATION)
    if submitter:
        submitter = submitter.removeprefix(KUBERNETES_SERVICE_ACCOUNT_PREFIX)
        submitter = submitter.removeprefix(OIDC_USER_PREFIX)
        submitter = submitter[:WORKLOAD_SUBMITTER_MAX_LENGTH]
    return submitter


def extract_workload_component_data(resource: Any) -> WorkloadComponentData:
    metadata = get_attr_or_key(resource, "metadata")
    labels = get_attr_or_key(metadata, "labels", {}) or {}
    annotations = get_attr_or_key(metadata, "annotations", {}) or {}
    return WorkloadComponentData(
        kind=WorkloadComponentKind(get_attr_or_key(resource, "kind")),
        api_version=get_attr_or_key(resource, "api_version", get_attr_or_key(resource, "apiVersion")),
        name=get_attr_or_key(metadata, "name"),
        workload_id=uuid.UUID(labels.get(WORKLOAD_ID_LABEL)),
        component_id=uuid.UUID(labels.get(COMPONENT_ID_LABEL)),
        project_id=uuid.UUID(labels.get(PROJECT_ID_LABEL)),
        auto_discovered=__is_component_auto_discovered(annotations),
        submitter=__parse_workload_submitter(annotations),
    )


def create_component_status_message(
    workload_component_data: WorkloadComponentData,
    status: WorkloadComponentStatus,
    status_reason: str | None = None,
) -> WorkloadComponentStatusMessage:
    return WorkloadComponentStatusMessage(
        name=workload_component_data.name,
        kind=workload_component_data.kind,
        api_version=workload_component_data.api_version,
        workload_id=workload_component_data.workload_id,
        id=workload_component_data.component_id,
        status=status,
        status_reason=status_reason or f"Status: {status}",
        message_type="workload_component_status_update",
        updated_at=datetime.now(UTC),
    )


def create_auto_discovered_workload_component_message(
    workload_component_data: WorkloadComponentData,
) -> AutoDiscoveredWorkloadComponentMessage:
    return AutoDiscoveredWorkloadComponentMessage(
        message_type="auto_discovered_workload_component",
        project_id=workload_component_data.project_id,
        workload_id=workload_component_data.workload_id,
        component_id=workload_component_data.component_id,
        name=workload_component_data.name,
        kind=workload_component_data.kind,
        api_version=workload_component_data.api_version,
        updated_at=datetime.now(UTC),
        submitter=workload_component_data.submitter,
    )
