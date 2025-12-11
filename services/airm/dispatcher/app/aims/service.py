# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
AIMClusterModel discovery service for the dispatcher.
Syncs all AIMClusterModel resources and publishes batch discovery messages to RabbitMQ.
Triggered by Kubernetes CronJob.
"""

from datetime import UTC, datetime

from aio_pika import abc
from kubernetes import client
from loguru import logger
from starlette import status

from airm.messaging.schemas import AIMClusterModel, AIMClusterModelsMessage

from ..kubernetes.watcher import get_installed_version_for_custom_resource
from ..messaging.publisher import publish_to_common_feedback_queue
from ..workloads.constants import AIM_CLUSTER_MODEL_RESOURCE_PLURAL, AIM_SERVICE_API_GROUP


def process_aim_cluster_model_resource(resource: dict) -> AIMClusterModel | None:
    try:
        metadata = resource.get("metadata", {})
        spec = resource.get("spec", {})
        status = resource.get("status", {})

        resource_name = metadata.get("name")
        if not resource_name:
            logger.warning("AIMClusterModel resource is missing required metadata.name, skipping")
            return None
        image_reference = spec.get("image", "")

        if not image_reference:
            logger.warning(f"AIMClusterModel {resource_name} has no image in spec, skipping")
            return None

        image_metadata = status.get("imageMetadata", {})

        if not image_metadata:
            logger.warning(
                f"AIMClusterModel {resource_name} has no imageMetadata in status yet. "
                f"Skipping until Kaiwo populates the metadata."
            )
            return None

        labels = image_metadata.get("originalLabels", {})
        if not labels:
            logger.warning(
                f"AIMClusterModel {resource_name} has imageMetadata but no originalLabels. Skipping this AIM."
            )
            return None

        return AIMClusterModel(
            resource_name=resource_name,
            image_reference=image_reference,
            labels=labels,
            status=status.get("status"),
        )

    except Exception as e:
        logger.exception(f"Error processing AIMClusterModel resource: {e}")
        return None


async def publish_aim_cluster_models_message_to_queue(
    connection: abc.AbstractConnection, channel: abc.AbstractChannel | None = None
) -> None:
    try:
        api = client.CustomObjectsApi()

        version = get_installed_version_for_custom_resource(
            client, AIM_SERVICE_API_GROUP, AIM_CLUSTER_MODEL_RESOURCE_PLURAL
        )
        if not version:
            logger.warning("AIMClusterModel CRD not found or has no served version. Skipping sync.")
            return

        logger.info("Syncing AIMClusterModel resources from cluster...")

        # List all AIMClusterModel resources cluster-wide
        response = api.list_cluster_custom_object(
            group=AIM_SERVICE_API_GROUP,
            version=version,
            plural=AIM_CLUSTER_MODEL_RESOURCE_PLURAL,
        )

        items = response.get("items", [])
        logger.info(f"Found {len(items)} AIMClusterModel resources")

        # Process each resource
        discovered_models = []
        for item in items:
            model = process_aim_cluster_model_resource(item)
            if model:
                discovered_models.append(model)

        logger.info(
            f"Processed {len(discovered_models)} valid AIM models (skipped {len(items) - len(discovered_models)})"
        )

        message = AIMClusterModelsMessage(
            message_type="aim_cluster_models",
            models=discovered_models,
            synced_at=datetime.now(UTC),
        )

        await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)

        logger.info(f"Successfully published AIM discovery batch with {len(discovered_models)} models")

    except client.exceptions.ApiException as e:
        if e.status == status.HTTP_404_NOT_FOUND:
            logger.warning("AIMClusterModel CRD not found. Is the CRD installed?")
        else:
            logger.exception(f"API error while syncing AIMClusterModel resources: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error while syncing AIMClusterModel resources: {e}")
