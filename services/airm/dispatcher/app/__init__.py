# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import os
import sys
from asyncio import Task
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from loguru import logger

from airm.utilities.fastapi import generic_exception_handler, value_error_handler

from .aims.router import router as aims_router
from .aims.service import publish_aim_cluster_models_message_to_queue
from .clusters.router import router as clusters_router
from .clusters.service import publish_cluster_nodes_message_to_queue
from .config.app_config import AppConfig
from .health.router import router as health_router
from .heartbeats.router import router as heartbeats_router
from .heartbeats.service import publish_heartbeat_message_to_queue
from .kubernetes import load_k8s_config
from .kubernetes.config import METRICS_CONFIG_MAP_NAME, METRICS_CONFIG_MAP_NAMESPACE
from .kubernetes.metrics_config import get_metrics_cluster_info
from .messaging.consumer import start_consuming_from_message_queue
from .messaging.publisher import (
    get_common_vhost_connection_and_channel,
)
from .namespaces.service import start_watching_namespace_components
from .quotas.service import start_watching_kaiwo_queue_config
from .secrets.service import start_watching_secrets_components
from .storages.service import start_watching_storages_components
from .workloads.service import start_watching_workload_components

load_dotenv(override=False)

tasks: list[Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup_event()
    yield
    await shutdown_event()


async def startup_event():
    global tasks
    load_k8s_config()

    # Set logging level
    # Remove default logger since we are adding a special level. This is how you do it in loguru.
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    try:
        # Read from environment variables
        org_name = os.getenv("ORG_NAME")
        cluster_name = os.getenv("KUBE_CLUSTER_NAME")

        if not org_name or not cluster_name:
            logger.info("Environment variables not set. Fetching values from Kubernetes config map.")
            org_name, cluster_name = await get_metrics_cluster_info(
                METRICS_CONFIG_MAP_NAMESPACE, METRICS_CONFIG_MAP_NAME
            )
            if not org_name or not cluster_name:
                logger.error("Organization name or cluster name is undefined.")
                sys.exit(1)

        # Set values in the singleton configuration
        AppConfig().set_config(org_name=org_name, cluster_name=cluster_name)
    except Exception as e:
        logger.exception("Failed to set organization name and cluster name.", e)
        sys.exit(1)

    try:
        connection, channel = await get_common_vhost_connection_and_channel()
        await publish_cluster_nodes_message_to_queue(connection, channel)
        await publish_heartbeat_message_to_queue(connection, channel)
        await publish_aim_cluster_models_message_to_queue(connection, channel)
    except Exception as e:
        logger.exception("Failed to connect or publish the message to RabbitMQ", e)
        sys.exit(1)

    try:
        tasks.append(start_consuming_from_message_queue())
    except Exception as e:
        logger.exception("Failed to start listening to inbound vhost queue", e)
        sys.exit(1)

    try:
        tasks.append(start_watching_workload_components())
        tasks.append(start_watching_kaiwo_queue_config())
        tasks.append(start_watching_secrets_components())
        tasks.append(start_watching_namespace_components())
        tasks.append(start_watching_storages_components())
    except Exception as e:
        logger.exception("Failed to start Kubernetes resource listeners", e)
        sys.exit(1)


async def shutdown_event():
    global tasks
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Task {task.get_name()} cancelled successfully.")


app = FastAPI(
    name="AMD Resource Manager Dispatcher",
    lifespan=lifespan,
    title="AMD Resource Manager Dispatcher",
)
app.include_router(health_router, prefix="/v1")
app.include_router(heartbeats_router, prefix="/v1")
app.include_router(clusters_router, prefix="/v1")
app.include_router(aims_router, prefix="/v1")

app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
