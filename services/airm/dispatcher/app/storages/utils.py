# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

from .constants import PROJECT_STORAGE_ID_LABEL


def build_configmap_manifest(
    name: str,
    namespace: str,
    bucket_url: str,
    project_storage_id: UUID,
    secret_key_name: str,
    access_key_name: str,
    secret_name: str,
    additional_labels: dict[str, str] | None = None,
    additional_annotations: dict[str, str] | None = None,
) -> dict[str, Any]:
    labels = {
        PROJECT_STORAGE_ID_LABEL: str(project_storage_id),
    }

    if additional_labels:
        labels.update(additional_labels)

    metadata: dict[str, Any] = {
        "name": name,
        "namespace": namespace,
        "labels": labels,
    }

    if additional_annotations:
        metadata["annotations"] = additional_annotations

    data = {
        "BUCKET_URL": bucket_url,
        "ACCESS_KEY_NAME": access_key_name,
        "SECRET_KEY_NAME": secret_key_name,
        "SECRET_NAME": secret_name,
    }

    manifest = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": metadata,
        "data": data,
    }

    return manifest
