# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Pydantic models for Secret CRD responses from Kubernetes.

These models are intentionally minimal and lenient:
- Only include fields we actually access in the code
- All fields optional with sensible defaults
- Parsing won't fail if K8s adds/removes fields
- Uses populate_by_name for both snake_case and camelCase
"""

from pydantic import BaseModel, ConfigDict

from ..dispatch.crds import K8sMetadata


class KubernetesSecretResource(BaseModel):
    """Kubernetes Secret resource - minimal parser for K8s API responses."""

    metadata: K8sMetadata

    model_config = ConfigDict(populate_by_name=True)
