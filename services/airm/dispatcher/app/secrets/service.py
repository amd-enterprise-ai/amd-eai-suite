# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic import DynamicClient
from kubernetes.utils import create_from_dict
from loguru import logger

from airm.messaging.schemas import (
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
    SecretsComponentKind,
)
from airm.secrets.constants import EXTERNAL_SECRETS_API_GROUP, EXTERNAL_SECRETS_PLURAL, PROJECT_SECRET_ID_LABEL
from airm.secrets.utils import validate_external_secret_manifest, validate_kubernetes_secret_manifest

from ..kubernetes.utils import delete_resources_by_label
from ..kubernetes.watcher import get_installed_version_for_custom_resource, start_kubernetes_watcher_if_resource_exists
from ..messaging.publisher import get_common_vhost_connection_and_channel, publish_to_common_feedback_queue
from .utils import (
    create_project_secret_status_message,
    extract_project_secret_id,
    get_status_for_external_secret,
    get_status_for_kubernetes_secret,
    patch_external_secret_manifest,
    patch_kubernetes_secret_manifest,
)


async def process_project_secrets_create(message: ProjectSecretsCreateMessage):
    logger.info("Project secrets create handler received message")
    logger.debug(f"Processing ProjectSecretsCreateMessage: {message}")

    def _failure_reason(base: str) -> str:
        return f"{base} (secret_type={message.secret_type})"

    match message.secret_type:
        case SecretsComponentKind.EXTERNAL_SECRET:
            validator = validate_external_secret_manifest
            patcher = patch_external_secret_manifest
        case SecretsComponentKind.KUBERNETES_SECRET:
            validator = validate_kubernetes_secret_manifest
            patcher = patch_kubernetes_secret_manifest
        case _:
            logger.error(_failure_reason("Unsupported secret type received"))
            await __publish_secrets_component_status_update(
                ProjectSecretsUpdateMessage(
                    message_type="project_secrets_update",
                    status=ProjectSecretStatus.FAILED,
                    status_reason=_failure_reason("Unsupported secret type"),
                    project_secret_id=message.project_secret_id,
                    updated_at=datetime.now(UTC),
                )
            )
            return

    try:
        parsed_manifest = validator(message.manifest)
    except Exception as e:
        logger.error(f"{e}")
        await __publish_secrets_component_status_update(
            ProjectSecretsUpdateMessage(
                message_type="project_secrets_update",
                status=ProjectSecretStatus.FAILED,
                status_reason=_failure_reason(str(e)),
                project_secret_id=message.project_secret_id,
                updated_at=datetime.now(UTC),
            )
        )
        return

    manifest = patcher(
        manifest=parsed_manifest,
        namespace=message.project_name,
        secret_name=message.secret_name,
        project_secret_id=str(message.project_secret_id),  # Ensure secret_id is a string
    )

    logger.info(f"Creating ExternalSecret: {message.project_secret_id}")

    try:
        api_client = client.ApiClient()
        create_from_dict(api_client, manifest, apply=True, namespace=message.project_name, force_conflicts=True)
    except Exception as e:
        logger.error(_failure_reason(f"Failed to create secret: {e}"))
        await __publish_secrets_component_status_update(
            ProjectSecretsUpdateMessage(
                message_type="project_secrets_update",
                status=ProjectSecretStatus.FAILED,
                status_reason=_failure_reason(f"Failed to create secret: {e}"),
                project_secret_id=message.project_secret_id,
                updated_at=datetime.now(UTC),
            )
        )
        return


async def _publish_project_secret_status(project_secret_id: UUID, status: ProjectSecretStatus, reason: str):
    connection, channel = await get_common_vhost_connection_and_channel()
    await publish_to_common_feedback_queue(
        ProjectSecretsUpdateMessage(
            message_type="project_secrets_update",
            project_secret_id=project_secret_id,
            status=status,
            status_reason=reason,
            updated_at=datetime.now(UTC),
        ),
        connection,
        channel,
    )


async def process_secret_delete_error(api_resource: Any, delete_err: ApiException, item):
    project_secret_id = extract_project_secret_id(item)

    status_reason = f"Deletion failed for resource {getattr(api_resource, 'kind', str(api_resource))} project_secret_id={project_secret_id}: {delete_err}"
    logger.error(f"{status_reason}\nException: {delete_err}")

    if project_secret_id:
        message = create_project_secret_status_message(
            project_secret_id, ProjectSecretStatus.DELETE_FAILED, status_reason
        )
        await __publish_secrets_component_status_update(message)


async def __publish_secrets_component_status_update(message: ProjectSecretsUpdateMessage):
    connection, channel = await get_common_vhost_connection_and_channel()

    await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)
    logger.info(f"Published to queue, message={message.model_dump_json()}")


async def process_project_secrets_delete(message: ProjectSecretsDeleteMessage):
    logger.info("Project secrets delete handler received message")
    logger.debug(f"Processing ProjectSecretsDeleteMessage: {message}")
    label_selector = f"{PROJECT_SECRET_ID_LABEL}={message.project_secret_id}"

    try:
        k8s_client = client.ApiClient()
        dynamic_client = DynamicClient(k8s_client)

        # Determine which resource kind to delete based on secret_type
        match message.secret_type:
            case SecretsComponentKind.EXTERNAL_SECRET:
                allowed_kinds = [SecretsComponentKind.EXTERNAL_SECRET.value]
                version = get_installed_version_for_custom_resource(
                    client, EXTERNAL_SECRETS_API_GROUP, EXTERNAL_SECRETS_PLURAL
                )
                api_version_for_kind: dict[str, str] = {}
                if version:
                    api_version_for_kind[SecretsComponentKind.EXTERNAL_SECRET.value] = version
            case SecretsComponentKind.KUBERNETES_SECRET:
                allowed_kinds = [SecretsComponentKind.KUBERNETES_SECRET.value]
                api_version_for_kind = {SecretsComponentKind.KUBERNETES_SECRET.value: "v1"}
            case _:
                logger.error(f"Unsupported secret type: {message.secret_type}")
                await _publish_project_secret_status(
                    message.project_secret_id,
                    ProjectSecretStatus.DELETE_FAILED,
                    f"Unsupported secret type: {message.secret_type}",
                )
                return

        deleted_any = await delete_resources_by_label(
            dynamic_client,
            label_selector,
            allowed_kinds,
            process_secret_delete_error,
            message.project_name,
            api_version_for_kind=api_version_for_kind or None,
        )

        if not deleted_any:
            logger.warning(f"No resources found with label selector '{label_selector}'")
            await _publish_project_secret_status(
                message.project_secret_id,
                ProjectSecretStatus.DELETED,
                f"No resources found for deletion: {label_selector}",
            )

    except Exception as ex:
        await _publish_project_secret_status(
            message.project_secret_id,
            ProjectSecretStatus.DELETE_FAILED,
            f"Error deleting project secret resources with label '{label_selector}': {ex}",
        )
        logger.exception(f"Error deleting project secret resources with label '{label_selector}' : {ex}")


async def __process_external_secret_event(resource, event_type):
    try:
        component_status, status_reason = get_status_for_external_secret(resource, event_type)

        if component_status:
            project_secret_id = extract_project_secret_id(resource)
            if project_secret_id:
                message = create_project_secret_status_message(project_secret_id, component_status, status_reason)
                await __publish_secrets_component_status_update(message)
            else:
                logger.warning(f"ExternalSecret resource with missing secret_id label. Resource: {resource}")
        else:
            logger.info("Unable to determine a status for event")

    except Exception as e:
        logger.exception("Error processing resource", e)


async def __process_kubernetes_secret_event(resource, event_type):
    try:
        component_status, status_reason = get_status_for_kubernetes_secret(resource, event_type)

        if component_status:
            project_secret_id = extract_project_secret_id(resource)
            if project_secret_id:
                message = create_project_secret_status_message(project_secret_id, component_status, status_reason)
                await __publish_secrets_component_status_update(message)
            else:
                logger.debug("Skipping Kubernetes Secret without project-secret-id label")
        else:
            logger.info("Unable to determine a status for Kubernetes secret event")

    except Exception as e:
        logger.exception("Error processing Kubernetes Secret resource", e)


def start_watching_secrets_components() -> asyncio.Task:
    async def __start_watching_secrets_components():
        await asyncio.gather(
            start_kubernetes_watcher_if_resource_exists(
                "external_secret_watcher",
                client.CustomObjectsApi().list_cluster_custom_object,
                __process_external_secret_event,
                group=EXTERNAL_SECRETS_API_GROUP,
                plural=EXTERNAL_SECRETS_PLURAL,
                version=get_installed_version_for_custom_resource(
                    client, EXTERNAL_SECRETS_API_GROUP, EXTERNAL_SECRETS_PLURAL
                ),
            ),
            start_kubernetes_watcher_if_resource_exists(
                "kubernetes_secret_watcher",
                client.CoreV1Api().list_secret_for_all_namespaces,
                __process_kubernetes_secret_event,
            ),
        )

    return asyncio.create_task(__start_watching_secrets_components())
