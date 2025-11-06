# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

from ..namespaces.constants import KUEUE_MANAGED_LABEL, PROJECT_ID_LABEL


def build_namespace_manifest(
    name: str,
    project_id: UUID,
    additional_labels: dict[str, str] | None = None,
    additional_annotations: dict[str, str] | None = None,
) -> dict[str, Any]:
    labels = {
        PROJECT_ID_LABEL: str(project_id),
        KUEUE_MANAGED_LABEL: "true",
    }

    if additional_labels:
        labels.update(additional_labels)

    metadata: dict[str, Any] = {
        "name": name,
        "labels": labels,
    }

    if additional_annotations:
        metadata["annotations"] = additional_annotations

    manifest = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": metadata,
    }

    return manifest
