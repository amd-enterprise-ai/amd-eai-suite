# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from ..messaging.schemas import KubernetesMetadata, NamespaceManifest
from ..workloads.constants import KUEUE_MANAGED_LABEL, PROJECT_ID_LABEL


def _build_namespace_manifest(name: str, project_id: UUID) -> NamespaceManifest:
    return NamespaceManifest(
        metadata=KubernetesMetadata(
            name=name,
            labels={
                PROJECT_ID_LABEL: str(project_id),
                KUEUE_MANAGED_LABEL: "true",
            },
        )
    )
