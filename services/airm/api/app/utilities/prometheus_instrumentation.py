# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import os

from loguru import logger
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from prometheus_fastapi_instrumentator import Instrumentator

from ..clusters.repository import get_all_cluster_nodes
from ..organizations.repository import get_organizations
from ..projects.repository import get_all_projects
from ..quotas.utils import set_allocated_gpus_metric_samples, set_allocated_vram_metric_samples
from .database import session_scope

_asyncio_event_loop: asyncio.AbstractEventLoop | None = None
METRICS_PORT = os.environ.get("PROMETHEUS_METRICS_PORT", "9009")

ALLOCATED_GPUS_METRIC_LABEL = "allocated_gpus"
ALLOCATED_GPU_VRAM_METRIC_LABEL = "allocated_gpu_vram"


class GPUQuotaMetricsCollector(Collector):
    allocated_gpus_metric = GaugeMetricFamily(
        ALLOCATED_GPUS_METRIC_LABEL,
        "Number of allocated GPUs for the specified project",
        labels=["project_id", "cluster_id", "org_name", "cluster_name"],
    )
    allocated_gpu_vram_metric = GaugeMetricFamily(
        ALLOCATED_GPU_VRAM_METRIC_LABEL,
        "Amount of VRAM allocated for the specified project, via allocated GPUs, in MB",
        labels=["project_id", "cluster_id", "org_name", "cluster_name"],
    )

    def describe(self):
        return [self.allocated_gpus_metric, self.allocated_gpu_vram_metric]

    def collect(self):
        global _asyncio_event_loop
        fut = asyncio.run_coroutine_threadsafe(self.__get_gpu_allocation_metrics(), _asyncio_event_loop)
        try:
            return fut.result(timeout=10)
        except Exception as e:
            logger.exception("Error collecting GPU allocation metrics: {}", e)
            return []

    async def __get_gpu_allocation_metrics(self) -> list[GaugeMetricFamily]:
        async with session_scope() as session:
            projects = await get_all_projects(session=session)
            organizations = await get_organizations(session=session)
            cluster_nodes = await get_all_cluster_nodes(session=session)

            set_allocated_gpus_metric_samples(self.allocated_gpus_metric, projects, organizations)
            set_allocated_vram_metric_samples(self.allocated_gpu_vram_metric, projects, organizations, cluster_nodes)

        return [self.allocated_gpus_metric, self.allocated_gpu_vram_metric]


def start_metrics_server():
    start_http_server(int(METRICS_PORT))
    global _asyncio_event_loop
    _asyncio_event_loop = asyncio.get_event_loop()


def setup_instrumentation(app):
    instrumentator = Instrumentator().instrument(app)
    instrumentator.registry.register(GPUQuotaMetricsCollector())
