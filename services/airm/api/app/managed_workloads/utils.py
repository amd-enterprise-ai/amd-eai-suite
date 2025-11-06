# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import hashlib
import os
import subprocess
import tempfile
import time
from contextlib import contextmanager
from urllib.parse import urljoin
from uuid import UUID

import yaml
from loguru import logger
from prometheus_api_client import PrometheusConnect
from yaml import safe_load_all

from ..charts.models import Chart
from ..managed_workloads.models import ManagedWorkload
from ..metrics.service import (
    get_gpu_device_utilization_for_project_by_workload_id,
    get_gpu_memory_utilization_for_project_by_workload_id,
)
from ..utilities.exceptions import InconsistentStateException
from ..workloads.enums import WorkloadType
from .schemas import AIMWorkloadResponse, AllocatedResources, ChartWorkloadResponse


@contextmanager
def workload_directory(chart: Chart):
    """
    Context manager that re-creates all the files of the chart in a temporary directory
    to be used with Helm template rendering and cleans it up afterward.
    """
    temp_dir = tempfile.TemporaryDirectory()
    try:
        for file in chart.files:
            if os.path.sep in file.path:
                # Create the directory structure based on the relative path of file.path
                file_dir = os.path.join(temp_dir.name, os.path.dirname(file.path))
                os.makedirs(file_dir, exist_ok=True)
            else:
                file_dir = temp_dir.name

            with open(os.path.join(file_dir, os.path.basename(file.path)), "w") as f:
                f.write(file.content)

        yield temp_dir.name
    finally:
        temp_dir.cleanup()


async def render_helm_template(chart: Chart, name: str, namespace: str, overlays_values: list[dict] = []) -> str:
    """
    Render the Helm template for the given chart with the overlays values.

    Params:
        chart: The chart to render.
        name: The name of the workload.
        namespace: Kubernetes namespace to render resources into.
        overlays_values: The values coming from the overlays to render the chart with.
    """

    with workload_directory(chart) as chart_dir:
        cmd = ["helm", "template", chart_dir, "--namespace", namespace, "--name-template", name]

        for i, values in enumerate(overlays_values):
            overlay_file = os.path.join(chart_dir, f"overlay_{i}.yaml")

            with open(overlay_file, "w") as f:
                yaml.dump(values, f)
                logger.debug(f"Overlay {i} has values: \n{values}\n\n")

            cmd.extend(["--values", overlay_file])
        cmd.extend(["--set", "fullnameOverride=" + name])
        logger.debug(f"Rendering Helm template: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = await process.communicate()

        if process.returncode is not None and process.returncode != 0:
            raise RuntimeError(f"Failed to render Helm template: {stderr.decode()}")

        return stdout.decode()


def get_workload_internal_host(workload_name: str, namespace: str) -> str:
    return f"{workload_name}.{namespace}.svc.cluster.local"


def get_workload_host_from_HTTPRoute_manifest(*, manifest: str, cluster_base_url: str) -> str | None:
    docs = safe_load_all(manifest)

    for doc in docs:
        if doc.get("kind") != "HTTPRoute":
            continue

        for rule in doc.get("spec", {}).get("rules", []):
            for match in rule.get("matches", []):
                path = match.get("path", {})

                if path.get("type") == "PathPrefix":
                    path_value = path.get("value")
                    if path_value:
                        return urljoin(cluster_base_url, path_value)

    return None


async def enrich_with_resource_utilization(
    project_id: UUID,
    workloads: list[ChartWorkloadResponse | AIMWorkloadResponse],
    prometheus_client: PrometheusConnect,
) -> list[ChartWorkloadResponse | AIMWorkloadResponse]:
    """
    Enrich the list of workloads with GPU utilization data.
    This function retrieves GPU device and memory utilization for each workload
    and adds it to the `allocated_resources` field of the workload response.
    """
    gpu_count, vram = await asyncio.gather(
        get_gpu_device_utilization_for_project_by_workload_id(project_id, prometheus_client),
        get_gpu_memory_utilization_for_project_by_workload_id(project_id, prometheus_client),
    )
    result = []
    for workload in workloads:
        # Use the correct response type to preserve specific fields
        if isinstance(workload, AIMWorkloadResponse):
            enriched = AIMWorkloadResponse.model_validate(workload).model_copy(
                update={
                    "allocated_resources": AllocatedResources(
                        gpu_count=gpu_count.get(str(workload.id), None), vram=vram.get(str(workload.id), None)
                    )
                }
            )
        else:
            enriched = ChartWorkloadResponse.model_validate(workload).model_copy(
                update={
                    "allocated_resources": AllocatedResources(
                        gpu_count=gpu_count.get(str(workload.id), None), vram=vram.get(str(workload.id), None)
                    )
                }
            )
        result.append(enriched)
    return result


def generate_workload_name(workload: ManagedWorkload) -> str:
    """
    Generate a unique name for a managed workload.

    AIM workloads: 8-character hash (to fit within DNS constraints with long namespace names)
    Chart workloads: mw-{chart_name}-{timestamp}-{uuid_prefix} (max 53 chars)
    """
    uuid_prefix = str(workload.id)[:4]
    timestamp = str(int(time.time()))[:10]

    if workload.aim:
        # AIM workloads: Use "mw-" prefix + 8-char hash (11 chars total)
        # Prefix ensures name starts with letter (KServe requirement)
        # This allows namespace names up to 63 - 11 - 10 ("-predictor") - 1 = 41 chars
        uuid_str = str(workload.id)
        hash_digest = hashlib.sha256(uuid_str.encode()).hexdigest()
        return f"mw-{hash_digest[:8]}"
    elif workload.chart:
        # Chart workloads use the format: mw-chart_name-timestamp-uuid_prefix
        prefix = workload.chart.name.replace(" ", "-").replace("_", "-")[:33]
        return f"mw-{prefix}-{timestamp}-{uuid_prefix}"[:53]
    else:
        raise InconsistentStateException(
            message=f"Cannot generate workload name for workload {workload.id}",
            detail="Workload must have either a chart or AIM reference to generate a name",
        )


def generate_display_name(workload: ManagedWorkload) -> str:
    """
    Generate a display name for a managed workload.
    """
    uuid_prefix = str(workload.id)[:8]

    if workload.aim:
        return f"{workload.aim.image_name}-{workload.aim.image_tag}-{uuid_prefix}"
    elif workload.chart:
        if workload.model:
            return f"{workload.chart.name}-{workload.model.name}-{uuid_prefix}"
        else:
            return f"{workload.chart.name}-{uuid_prefix}"
    else:
        raise InconsistentStateException(
            message=f"Cannot generate display name for workload {workload.id}",
            detail="Workload must have either a chart or AIM reference to generate a display name",
        )


def does_workload_need_cluster_base_url(chart: Chart):
    """
    Check if the workload type needs the cluster base URL to be accessed.
    """
    return chart.type in (WorkloadType.INFERENCE, WorkloadType.WORKSPACE)
