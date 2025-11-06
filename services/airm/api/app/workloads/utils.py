# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

import yaml

from airm.messaging.schemas import (
    CommonComponentStatus,
    WorkloadComponentKind,
    WorkloadComponentStatusMessage,
    WorkloadStatus,
)
from airm.workloads.constants import COMPONENT_ID_LABEL, PROJECT_ID_LABEL, WORKLOAD_ID_LABEL

from ..projects.models import Project
from ..utilities.exceptions import ValidationException
from .constants import (
    COMPONENT_SPECIFIC_COMPLETED_STATUSES,
    COMPONENT_SPECIFIC_DOWNLOADING_STATUSES,
    COMPONENT_SPECIFIC_FAILED_STATUSES,
    COMPONENT_SPECIFIC_PENDING_STATUSES,
    COMPONENT_SPECIFIC_RUNNING_STATUSES,
    COMPONENT_SPECIFIC_TERMINATED_STATUSES,
    KUEUE_QUEUE_NAME_LABEL,
)
from .models import WorkloadComponent
from .schemas import WorkloadComponentIn


async def validate_and_parse_workload_manifest(yml: Any | str) -> list[dict]:
    if isinstance(yml, str):
        yml_content = yml
    else:
        yml_content_raw = await yml.read()
        yml_content = yml_content_raw.decode()
    manifest = list(yaml.safe_load_all(yml_content))

    for item in manifest:
        kind = item.get("kind")
        if not kind:
            raise ValidationException("Each manifest item must specify a 'kind'")

        try:
            _ = WorkloadComponentKind(kind)
        except ValueError:
            raise ValidationException(f"Unsupported resource kind: {kind}")

        metadata = item.get("metadata", {})
        if "name" not in metadata:
            raise ValidationException(f"{kind} metadata must contain 'name' attribute")

        if "namespace" in metadata:
            raise ValidationException(
                "Workload components must not contain the 'namespace' attribute, it will be injected"
            )

        if kind in {
            WorkloadComponentKind.DEPLOYMENT,
            WorkloadComponentKind.JOB,
        } and "serviceAccountName" in item.get("spec", {}).get("template", {}).get("spec", {}):
            raise ValidationException("Service account is not allowed for the supplied workload")
        elif kind in {
            WorkloadComponentKind.KAIWO_JOB,
            WorkloadComponentKind.KAIWO_SERVICE,
        } and "serviceAccountName" in item.get("spec"):
            raise ValidationException("Service account is not allowed for the supplied workload")

    return manifest


def __inject_standard_workload_labels(
    labels: dict[str, str], workload_id: UUID, component_id: UUID, project_id: UUID
) -> None:
    labels[WORKLOAD_ID_LABEL] = str(workload_id)
    labels[PROJECT_ID_LABEL] = str(project_id)
    labels[COMPONENT_ID_LABEL] = str(component_id)


def inject_workload_metadata_to_manifest(
    workload_id: UUID, project: Project, components_with_manifests: list[tuple[WorkloadComponent, dict]]
) -> str:
    manifest_items = []
    for component, item in components_with_manifests:
        metadata = item.setdefault("metadata", {})
        metadata["namespace"] = project.name
        labels = metadata.setdefault("labels", {})
        __inject_standard_workload_labels(
            labels=labels, workload_id=workload_id, component_id=component.id, project_id=project.id
        )
        kind = item.get("kind")

        # https://kueue.sigs.k8s.io/docs/tasks/run/plain_pods/
        if kind == WorkloadComponentKind.POD:
            labels[KUEUE_QUEUE_NAME_LABEL] = project.name

        elif kind in (
            # https://kueue.sigs.k8s.io/docs/tasks/run/jobs/
            WorkloadComponentKind.JOB,
            # https://kueue.sigs.k8s.io/docs/tasks/run/deployment/
            WorkloadComponentKind.DEPLOYMENT,
            # https://kueue.sigs.k8s.io/docs/tasks/run/statefulset/
            WorkloadComponentKind.STATEFUL_SET,
        ):
            labels[KUEUE_QUEUE_NAME_LABEL] = project.name
            spec = item.setdefault("spec", {})
            template = spec.setdefault("template", {})
            spec_metadata = template.setdefault("metadata", {})
            spec_labels = spec_metadata.setdefault("labels", {})
            __inject_standard_workload_labels(
                labels=spec_labels, workload_id=workload_id, component_id=component.id, project_id=project.id
            )

        elif kind == WorkloadComponentKind.DAEMON_SET:
            spec = item.setdefault("spec", {})
            template = spec.setdefault("template", {})
            spec_metadata = template.setdefault("metadata", {})
            spec_labels = spec_metadata.setdefault("labels", {})

            __inject_standard_workload_labels(
                labels=spec_labels, workload_id=workload_id, component_id=component.id, project_id=project.id
            )
            spec_labels[KUEUE_QUEUE_NAME_LABEL] = project.name

        # https://kueue.sigs.k8s.io/docs/tasks/run/run_cronjobs/
        elif kind == WorkloadComponentKind.CRON_JOB:
            spec = item.setdefault("spec", {})
            job_template = spec.setdefault("jobTemplate", {})
            template_metadata = job_template.setdefault("metadata", {})
            template_labels = template_metadata.setdefault("labels", {})
            __inject_standard_workload_labels(
                labels=template_labels, workload_id=workload_id, component_id=component.id, project_id=project.id
            )
            template_labels[KUEUE_QUEUE_NAME_LABEL] = project.name
            template_spec = job_template.setdefault("spec", {})
            template_spec_template = template_spec.setdefault("template", {})
            template_spec_template_meta = template_spec_template.setdefault("metadata", {})
            template_spec_template_labels = template_spec_template_meta.setdefault("labels", {})
            __inject_standard_workload_labels(
                labels=template_spec_template_labels,
                workload_id=workload_id,
                component_id=component.id,
                project_id=project.id,
            )

        elif kind in (WorkloadComponentKind.KAIWO_JOB, WorkloadComponentKind.KAIWO_SERVICE):
            spec = item.setdefault("spec", {})
            spec["clusterQueue"] = project.name
        manifest_items.append(item)

    return yaml.dump_all(manifest_items)


def extract_workload_components_from_manifest(
    manifest: list[dict], workload_id: UUID
) -> list[tuple[WorkloadComponentIn, dict]]:
    components = []
    for item in manifest:
        item_kind = item.get("kind", "")
        item_name = item.get("metadata", {}).get("name", "")
        item_api_version = item.get("apiVersion", "")

        component = WorkloadComponentIn(
            name=item_name,
            kind=WorkloadComponentKind(item_kind).value,
            api_version=item_api_version,
            workload_id=workload_id,
        )
        components.append((component, item))

    return components


def resolve_workload_status(current_status: WorkloadStatus, components: list[WorkloadComponent]) -> WorkloadStatus:
    if not components:
        return WorkloadStatus.UNKNOWN

    # All components are deleted
    if all(comp.status == CommonComponentStatus.DELETED for comp in components):
        return WorkloadStatus.DELETED

    # If any component is in deletion failed state, the overall state is deletion failed
    if any(comp.status == CommonComponentStatus.DELETE_FAILED for comp in components):
        return WorkloadStatus.DELETE_FAILED

    # If a delete was triggered, don't change the status
    if current_status == WorkloadStatus.DELETING:
        return WorkloadStatus.DELETING

    # If all components are in a Completed state, the workload is Completed
    if all(comp.status in COMPONENT_SPECIFIC_COMPLETED_STATUSES.get(comp.kind, []) for comp in components):
        return WorkloadStatus.COMPLETE

    # TODO: Revisit whether workload-type-specific statuses like DOWNLOADING should be top-level statuses
    # or if they should be treated as PENDING with component-specific details handled in ManagedWorkloads.
    # Similar to how Kubernetes has a Pod in "Pending" state with a container in "ContainerCreating" status.
    # If any component is in a Downloading state, the workload is Downloading
    if any(comp.status in COMPONENT_SPECIFIC_DOWNLOADING_STATUSES.get(comp.kind, []) for comp in components):
        return WorkloadStatus.DOWNLOADING

    # If all components are deleted, completed or terminated, the workload is Terminated
    if all(
        comp.status
        in [CommonComponentStatus.DELETED]
        + COMPONENT_SPECIFIC_COMPLETED_STATUSES.get(comp.kind, [])
        + COMPONENT_SPECIFIC_TERMINATED_STATUSES.get(comp.kind, [])
        for comp in components
    ):
        return WorkloadStatus.TERMINATED

    # If any component is in a Failed state, the workload is Failed
    if any(
        comp.status in [CommonComponentStatus.CREATE_FAILED] + COMPONENT_SPECIFIC_FAILED_STATUSES.get(comp.kind, [])
        for comp in components
    ):
        return WorkloadStatus.FAILED

    # If any component is in a Pending state, the workload is Pending
    if any(
        comp.status in [CommonComponentStatus.REGISTERED] + COMPONENT_SPECIFIC_PENDING_STATUSES.get(comp.kind, [])
        for comp in components
    ):
        return WorkloadStatus.PENDING

    # If any components is in a Running state, the workload is Running
    if any(comp.status in COMPONENT_SPECIFIC_RUNNING_STATUSES.get(comp.kind, []) for comp in components):
        return WorkloadStatus.RUNNING

    # If no rule matches, return Unknown
    return WorkloadStatus.UNKNOWN


def get_workload_component_for_status_update(
    components: list[WorkloadComponent], message: WorkloadComponentStatusMessage
) -> WorkloadComponent | None:
    matching_components = (
        c for c in components if c.id == message.id and c.kind == message.kind and c.api_version == message.api_version
    )
    return next(matching_components, None)
