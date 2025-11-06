# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import re

import yaml

from ..managed_workloads.models import ManagedWorkload
from ..projects.models import Project
from ..utilities.exceptions import ValidationException
from .config import AIM_OTEL_COLLECTOR_SIDECAR_REF, AIM_RUNTIME_CONFIG_NAME
from .models import AIM
from .schemas import AIMDeployRequest

DNS1123_LABEL_MAX_LEN = 63
_DNS1123_LABEL_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


def kubernetes_name(image_name: str, image_tag: str, *, max_length: int = DNS1123_LABEL_MAX_LEN) -> str:
    """
    Join two strings with a hyphen and normalize to a Kubernetes DNS-1123 label.

    Rules enforced (DNS-1123 label):
      - only lowercase letters, digits, and hyphens
      - must start and end with an alphanumeric character
      - length: 1..max_length (default 63)

    Raises:
        ValidationException: if empty after normalization, invalid format, or exceeds max_length.

    Examples:
        >>> kubernetes_name("My App", "v1")
        'my-app-v1'
        >>> kubernetes_name("a!@#", "___B")
        'a-b'
    """
    # 1) join
    name = f"{image_name}-{image_tag}"

    # 2) normalize
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9-]+", "-", name)  # replace invalid chars with '-'
    name = re.sub(r"-{2,}", "-", name)  # collapse multiple '-'
    name = name.strip("-")  # must not start/end with '-'

    # 3) validate
    if not name:
        raise ValidationException("Name is empty after normalization.")

    if len(name) > max_length:
        raise ValidationException(f"Name '{name}' exceeds max length {max_length} (got {len(name)}).")

    if not _DNS1123_LABEL_RE.match(name):
        raise ValidationException(f"Name '{name}' is not a valid DNS-1123 label.")

    return name


def generate_aim_service_manifest(
    aim: AIM, deploy_request: AIMDeployRequest, workload: ManagedWorkload, project: Project, group_id: str | None = None
) -> str:
    """Generate AIMService CRD manifest for deploying an AIM."""

    spec: dict = {
        "model": {"ref": kubernetes_name(aim.image_name, aim.image_tag)},
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

    manifest = {
        "apiVersion": "aim.silogen.ai/v1alpha1",
        "kind": "AIMService",
        "metadata": {
            "name": workload.name,
            "annotations": {"sidecar.opentelemetry.io/inject": AIM_OTEL_COLLECTOR_SIDECAR_REF},
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
    base_url = project.cluster.base_url or "http://localhost"

    return {
        "internal_host": get_workload_internal_host(workload.name, project.name),
        "external_host": f"{base_url.rstrip('/')}/{project.name}/{workload.id}",
    }
