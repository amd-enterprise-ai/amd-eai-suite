# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import yaml
from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic import DynamicClient
from loguru import logger

from airm.messaging.schemas import (
    CommonComponentStatus,
    DeleteWorkloadMessage,
    WorkloadComponentKind,
    WorkloadComponentStatusMessage,
    WorkloadMessage,
    WorkloadStatus,
    WorkloadStatusMessage,
)
from airm.workloads.constants import WORKLOAD_ID_LABEL
from app.kubernetes.generic_watchers import start_generic_configmap_watcher

from ..kubernetes.utils import delete_resources_by_label
from ..kubernetes.watcher import (
    get_installed_version_for_custom_resource,
    start_kubernetes_watcher,
    start_kubernetes_watcher_if_resource_exists,
)
from ..messaging.publisher import get_common_vhost_connection_and_channel, publish_to_common_feedback_queue
from ..quotas.constants import KAIWO_RESOURCE_API_GROUP
from ..workloads.constants import (
    AIM_SERVICE_API_GROUP,
    AIM_SERVICE_RESOURCE_PLURAL,
    HTTPROUTE_API_GROUP,
    HTTPROUTE_PLURAL,
    KAIWO_JOB_RESOURCE_PLURAL,
    KAIWO_SERVICE_RESOURCE_PLURAL,
)
from .schemas import WorkloadComponentData
from .utils import (
    create_auto_discovered_workload_component_message,
    create_component_status_message,
    extract_workload_component_data,
    get_status_for_aim_service,
    get_status_for_config_map,
    get_status_for_cron_job,
    get_status_for_daemon_set,
    get_status_for_deployment,
    get_status_for_http_route,
    get_status_for_ingress,
    get_status_for_job,
    get_status_for_kaiwo_job,
    get_status_for_kaiwo_service,
    get_status_for_pod,
    get_status_for_service,
    get_status_for_stateful_set,
    standard_event_status_mappings,
)


async def process_workload(message: WorkloadMessage) -> None:
    logger.info("Workload handler received message")
    logger.debug(f"Processing WorkloadMessage: {message}")
    manifests = list(yaml.safe_load_all(message.manifest))
    k8s_client = DynamicClient(client.api_client.ApiClient())

    for manifest in manifests:
        try:
            # create_from_dict does not work when apply=False for custom objects: https://github.com/silogen/core/pull/1806
            api_version = manifest.get("apiVersion")
            kind = manifest.get("kind")
            namespace = manifest.get("metadata").get("namespace")
            api = k8s_client.resources.get(api_version=api_version, kind=kind)
            api.create(body=manifest, namespace=namespace)
        except Exception as e:
            logger.exception("Failed to create manifest due to error", e)
            failure_reason = f"Failed to create manifest : {e}"
            workload_component_data = extract_workload_component_data(manifest)
            message = create_component_status_message(
                workload_component_data, CommonComponentStatus.CREATE_FAILED, failure_reason
            )
            await __publish_workload_component_status_update(message)


async def __publish_workload_status(workload_id: UUID, status: str, reason: str) -> None:
    connection, channel = await get_common_vhost_connection_and_channel()
    await publish_to_common_feedback_queue(
        WorkloadStatusMessage(
            message_type="workload_status_update",
            workload_id=workload_id,
            status=status,
            status_reason=reason,
            updated_at=datetime.now(UTC),
        ),
        connection,
        channel,
    )


async def __publish_workload_component_status_update(message: WorkloadComponentStatusMessage) -> None:
    connection, channel = await get_common_vhost_connection_and_channel()

    await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)
    logger.info(f"Published to queue, message={message.model_dump_json()}")


async def __publish_auto_discovered_workload_component(workload_component_data: WorkloadComponentData) -> None:
    connection, channel = await get_common_vhost_connection_and_channel()
    message = create_auto_discovered_workload_component_message(workload_component_data)
    await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)
    logger.info(f"Published auto-discovered component to queue, message={message.model_dump_json()}")


async def __process_workload_component_event(resource: Any, event_type: str, status_function: Callable) -> None:
    try:
        workload_component_data = extract_workload_component_data(resource)
        if workload_component_data.auto_discovered:
            await __publish_auto_discovered_workload_component(workload_component_data)

        if event_type in standard_event_status_mappings:
            status, status_reason = standard_event_status_mappings[event_type]

        else:
            status, status_reason = status_function(resource, event_type)

        if status:
            message = create_component_status_message(workload_component_data, status, status_reason)
            await __publish_workload_component_status_update(message)
        else:
            logger.info("Unable to determine a status for event")

    except Exception as e:
        logger.exception("Error processing resource", e)


def start_watching_workload_components() -> asyncio.Task:
    async def __start_watching_workload_components():
        await asyncio.gather(
            start_kubernetes_watcher(
                "job_watcher",
                client.BatchV1Api().list_job_for_all_namespaces,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_job),
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "deployment_watcher",
                client.AppsV1Api().list_deployment_for_all_namespaces,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_deployment),
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_generic_configmap_watcher(
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_config_map),
                component_name="workloads",
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "service_watcher",
                client.CoreV1Api().list_service_for_all_namespaces,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_service),
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "pod_watcher",
                client.CoreV1Api().list_pod_for_all_namespaces,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_pod),
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "stateful_set_watcher",
                client.AppsV1Api().list_stateful_set_for_all_namespaces,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_stateful_set),
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "daemon_set_watcher",
                client.AppsV1Api().list_daemon_set_for_all_namespaces,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_daemon_set),
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "cron_job_watcher",
                client.BatchV1Api().list_cron_job_for_all_namespaces,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_cron_job),
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "kaiwo_job_watcher",
                client.CustomObjectsApi().list_cluster_custom_object,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_kaiwo_job),
                group=KAIWO_RESOURCE_API_GROUP,
                version=get_installed_version_for_custom_resource(
                    client, KAIWO_RESOURCE_API_GROUP, KAIWO_JOB_RESOURCE_PLURAL
                ),
                plural=KAIWO_JOB_RESOURCE_PLURAL,
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "kaiwo_service_watcher",
                client.CustomObjectsApi().list_cluster_custom_object,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_kaiwo_service),
                group=KAIWO_RESOURCE_API_GROUP,
                version=get_installed_version_for_custom_resource(
                    client, KAIWO_RESOURCE_API_GROUP, KAIWO_SERVICE_RESOURCE_PLURAL
                ),
                plural=KAIWO_SERVICE_RESOURCE_PLURAL,
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher(
                "aim_service_watcher",
                client.CustomObjectsApi().list_cluster_custom_object,
                lambda res, evt: __process_workload_component_event(res, evt, get_status_for_aim_service),
                group=AIM_SERVICE_API_GROUP,
                version=get_installed_version_for_custom_resource(
                    client, AIM_SERVICE_API_GROUP, AIM_SERVICE_RESOURCE_PLURAL
                ),
                plural=AIM_SERVICE_RESOURCE_PLURAL,
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher_if_resource_exists(
                watcher_name="http_route_watcher",
                watch_function=client.CustomObjectsApi().list_cluster_custom_object,
                callback=lambda res, evt: __process_workload_component_event(res, evt, get_status_for_http_route),
                group=HTTPROUTE_API_GROUP,
                version=get_installed_version_for_custom_resource(client, HTTPROUTE_API_GROUP, HTTPROUTE_PLURAL),
                plural=HTTPROUTE_PLURAL,
                label_selector=WORKLOAD_ID_LABEL,
            ),
            start_kubernetes_watcher_if_resource_exists(
                watcher_name="ingress_watcher",
                watch_function=client.NetworkingV1Api().list_ingress_for_all_namespaces,
                callback=lambda res, evt: __process_workload_component_event(res, evt, get_status_for_ingress),
                label_selector=WORKLOAD_ID_LABEL,
            ),
        )

    return asyncio.create_task(__start_watching_workload_components())


async def process_workload_delete_error(api_resource: Any, delete_err: ApiException, item: Any) -> None:
    workload_component_data = extract_workload_component_data(item)

    status_reason = f"Deletion failed for resource {api_resource.kind} workload_id={workload_component_data.workload_id} component_id={workload_component_data.component_id}: {delete_err}"
    logger.error(status_reason, delete_err)

    message = create_component_status_message(
        workload_component_data, CommonComponentStatus.DELETE_FAILED.value, status_reason
    )
    await __publish_workload_component_status_update(message)


async def process_delete_workload(message: DeleteWorkloadMessage) -> None:
    logger.info("Delete workload handler received message")
    logger.debug(f"Processing DeleteWorkloadMessage: {message}")
    label_selector = f"{WORKLOAD_ID_LABEL}={message.workload_id}"

    try:
        k8s_client = client.ApiClient()
        dynamic_client = DynamicClient(k8s_client)

        allowed_kinds = [kind.value for kind in WorkloadComponentKind]
        deleted_any = await delete_resources_by_label(
            dynamic_client, label_selector, allowed_kinds, process_workload_delete_error
        )

        if not deleted_any:
            logger.warning(f"No resources found with label selector '{label_selector}'")
            await __publish_workload_status(
                message.workload_id, WorkloadStatus.DELETED.value, f"No resources found for deletion: {label_selector}"
            )

    except Exception as ex:
        logger.exception(f"Error deleting workload with label '{label_selector}' : {ex}")
