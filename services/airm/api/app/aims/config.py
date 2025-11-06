# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os
from pathlib import Path

AIM_REGISTRY_HOST = os.getenv("AIM_REGISTRY_HOST", "docker.io")
AIM_REGISTRY_ORG = os.getenv("AIM_REGISTRY_ORG", "amdenterpriseai")
AIM_REGISTRY = f"{AIM_REGISTRY_HOST}/{AIM_REGISTRY_ORG}"
AIM_IMAGE_NAMES_PREFIX = os.getenv("AIM_IMAGE_NAMES_PREFIX", "aim-")
AIM_EXCLUDED_IMAGES = os.getenv("AIM_EXCLUDED_IMAGES", "aim-base,aim-base-rc,aim-llm").split(",")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WORKERS = int(os.getenv("AIM_FETCHING_WORKERS") or os.cpu_count() or 4)
TLS_VERIFY = os.getenv("AIM_TLS_VERIFY", "false").lower() in ("true", "1", "yes")

AIM_METADATA_FILE_PATH = Path(__file__).parent / "aim-metadata.yaml"

AIM_OTEL_COLLECTOR_SIDECAR_REF = os.getenv("AIM_OTEL_COLLECTOR_SIDECAR_REF", "airm/airm-vllm-sidecar-collector")

AIM_RUNTIME_CONFIG_NAME = os.getenv("AIM_RUNTIME_CONFIG_NAME", "amd-aim-cluster-runtime-config")
