# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import yaml

from ..managed_workloads.models import ManagedWorkload
from ..projects.models import Project
from .config import AIM_RUNTIME_CONFIG_NAME
from .models import AIM
from .schemas import AIMDeployRequest


def generate_aim_service_manifest(
    aim: AIM, deploy_request: AIMDeployRequest, workload: ManagedWorkload, project: Project, group_id: str | None = None
) -> str:
    """Generate AIMService CRD manifest for deploying an AIM."""

    spec: dict = {
        "model": {"ref": aim.resource_name},
        "cacheModel": deploy_request.cache_model,
        "replicas": deploy_request.replicas,
        "runtimeConfigName": AIM_RUNTIME_CONFIG_NAME,
    }

    if deploy_request.image_pull_secrets:
        spec["imagePullSecrets"] = [{"name": secret_name} for secret_name in deploy_request.image_pull_secrets]

    if deploy_request.hf_token:
        spec["env"] = [
            {
                "name": "HF_TOKEN",
                "valueFrom": {"secretKeyRef": {"name": deploy_request.hf_token, "key": "token"}},
            }
        ]
    routing_spec: dict = {
        "enabled": True,
    }
    if group_id:
        routing_spec["annotations"] = {"cluster-auth/allowed-group": group_id}

    spec["routing"] = routing_spec

    if deploy_request.metric:
        if "overrides" not in spec:
            spec["overrides"] = {}
        spec["overrides"]["metric"] = deploy_request.metric

    if "template" not in spec or not isinstance(spec["template"], dict):
        spec["template"] = {}
    spec["template"]["allowUnoptimized"] = deploy_request.allow_unoptimized

    manifest = {
        "apiVersion": "aim.silogen.ai/v1alpha1",
        "kind": "AIMService",
        "metadata": {
            "name": workload.name,
        },
        "spec": spec,
    }

    return yaml.dump(manifest, default_flow_style=False, sort_keys=False)


def get_workload_internal_host(workload_name: str, namespace: str) -> str:
    """
    Generate the internal host for an AIM workload.

    KServe creates hostnames in the format: {isvc-name}-predictor.{namespace}.svc.cluster.local

    With our constraints:
    - AIM workload names: 11 characters (mw-{8-char-hash})
    - Project/namespace names: ≤41 characters
    - KServe suffix: "-predictor" (10 chars)

    The first DNS label ({isvc-name}-predictor) is 21 chars, well under the 63-char limit.
    No truncation is needed.
    """
    return f"{workload_name}-predictor.{namespace}.svc.cluster.local"


def generate_aim_workload_urls(project: Project, workload: ManagedWorkload) -> dict[str, str | None]:
    """Generate internal and external URLs for an AIM workload.

    URLs are generated to match the routing configuration enabled in the manifest.
    The external URL follows the pattern: {base_url}/{project}/{workload.id}
    """
    base_url = project.cluster.workloads_base_url

    return {
        "internal_host": get_workload_internal_host(workload.name, project.name),
        "external_host": f"{base_url.rstrip('/')}/{project.name}/{workload.id}",
    }
