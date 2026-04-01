# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Pydantic models for AIMService CRD responses from Kubernetes.

These models are intentionally minimal and lenient:
- Only include fields we actually access in the code
- All fields optional with sensible defaults
- Parsing won't fail if K8s adds/removes fields
- Uses populate_by_name for both snake_case and camelCase
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from ..dispatch.crds import K8sMetadata
from ..workloads.constants import WORKLOAD_ID_LABEL
from .enums import AIMClusterModelStatus as AIMClusterModelStatusEnum
from .enums import AIMServiceStatus as AIMServiceStatusEnum


class AIMModelMetadata(BaseModel):
    canonical_name: str | None = Field(None, alias="canonicalName")
    hf_token_required: bool | None = Field(None, alias="hfTokenRequired")
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    title: str | None = None
    variants: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class AIMImageMetadata(BaseModel):
    model: AIMModelMetadata = Field(default_factory=AIMModelMetadata)
    original_labels: dict[str, Any] = Field(default_factory=dict, alias="originalLabels")

    model_config = ConfigDict(populate_by_name=True)


class AIMClusterModelSpec(BaseModel):
    image: str = ""

    model_config = ConfigDict(populate_by_name=True)


class AIMClusterModelStatusFields(BaseModel):
    status: AIMClusterModelStatusEnum = AIMClusterModelStatusEnum.NOT_AVAILABLE
    image_metadata: AIMImageMetadata = Field(default_factory=AIMImageMetadata, alias="imageMetadata")

    model_config = ConfigDict(populate_by_name=True)


class AIMClusterModelResource(BaseModel):
    metadata: K8sMetadata
    spec: AIMClusterModelSpec = Field(default_factory=AIMClusterModelSpec)
    status: AIMClusterModelStatusFields = Field(default_factory=AIMClusterModelStatusFields)

    model_config = ConfigDict(populate_by_name=True)

    @computed_field
    def resource_name(self) -> str:
        return self.metadata.name

    @computed_field
    def image_reference(self) -> str:
        return self.spec.image

    @computed_field
    def status_value(self) -> str:
        return self.status.status.value


class AIMClusterServiceTemplateResource(BaseModel):
    """AIMClusterServiceTemplate CRD resource."""

    metadata: K8sMetadata
    spec: dict[str, Any] = Field(default_factory=dict)
    status: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class HTTPRoutePathMatch(BaseModel):
    """HTTPRoute path match configuration."""

    type: str | None = Field(None, description="Path match type (e.g., 'PathPrefix')")
    value: str | None = Field(None, description="Path value to match")

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteMatch(BaseModel):
    """HTTPRoute match configuration."""

    path: HTTPRoutePathMatch | None = Field(None, description="Path match configuration")

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteBackendRef(BaseModel):
    """HTTPRoute backend reference."""

    kind: str | None = Field(None, description="Backend resource kind (e.g., 'Service')")
    name: str | None = Field(None, description="Backend resource name")
    port: int | None = Field(None, description="Backend port")

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteRule(BaseModel):
    """HTTPRoute rule configuration."""

    matches: list[HTTPRouteMatch] = Field(default_factory=list, description="Request match conditions")
    backend_refs: list[HTTPRouteBackendRef] = Field(
        default_factory=list, alias="backendRefs", description="Backend references"
    )

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteSpec(BaseModel):
    """HTTPRoute spec configuration."""

    rules: list[HTTPRouteRule] = Field(default_factory=list, description="Route rules")

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteResource(BaseModel):
    """HTTPRoute CRD resource from Gateway API."""

    metadata: K8sMetadata
    spec: HTTPRouteSpec = Field(default_factory=HTTPRouteSpec)

    model_config = ConfigDict(populate_by_name=True)


class AIMServiceSpec(BaseModel):
    model: dict[str, Any] = Field(default_factory=dict)
    replicas: int = Field(1, description="The current replicas count")
    overrides: dict[str, Any] = Field(default_factory=dict)
    cache_model: bool = Field(True, alias="cacheModel")
    routing: dict[str, Any] = Field(default_factory=dict)
    runtime_config_name: str | None = Field(None, alias="runtimeConfigName")
    template: dict[str, Any] = Field(default_factory=dict)
    # Scaling policy fields
    min_replicas: int | None = Field(None, alias="minReplicas", description="Minimum replicas for autoscaling")
    max_replicas: int | None = Field(None, alias="maxReplicas", description="Maximum replicas for autoscaling")
    auto_scaling: dict[str, Any] | None = Field(None, alias="autoScaling", description="Advanced autoscaling config")
    env: list[dict[str, Any]] = Field(default_factory=list)
    image_pull_secrets: list[dict[str, Any]] = Field(default_factory=list, alias="imagePullSecrets")

    model_config = ConfigDict(populate_by_name=True)


class AIMServiceRuntime(BaseModel):
    """Runtime scaling status from AIMService CRD status.runtime."""

    current_replicas: int | None = Field(None, alias="currentReplicas")
    desired_replicas: int | None = Field(None, alias="desiredReplicas")
    min_replicas: int | None = Field(None, alias="minReplicas")
    max_replicas: int | None = Field(None, alias="maxReplicas")
    replicas: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class ResolvedRef(BaseModel):
    """Resolved reference (template name). Only name is used; scope/uid from K8s are not returned."""

    name: str | None = Field(None, description="Template name")

    model_config = ConfigDict(populate_by_name=True)


class AIMServiceStatusFields(BaseModel):
    status: AIMServiceStatusEnum = AIMServiceStatusEnum.PENDING
    routing: dict[str, Any] = Field(default_factory=dict)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    observed_generation: int | None = Field(None, alias="observedGeneration")
    runtime: AIMServiceRuntime = Field(default_factory=AIMServiceRuntime)
    resolved_model: ResolvedRef | None = Field(None, alias="resolvedModel")
    resolved_template: ResolvedRef | None = Field(None, alias="resolvedTemplate")

    model_config = ConfigDict(populate_by_name=True)


class AIMServiceResource(BaseModel):
    metadata: K8sMetadata
    spec: AIMServiceSpec = Field(default_factory=AIMServiceSpec)  # type: ignore
    status: AIMServiceStatusFields = Field(default_factory=AIMServiceStatusFields)  # type: ignore
    httproute: HTTPRouteResource | None = Field(None, repr=False, exclude=True)
    inference_service_name: str | None = Field(None, repr=False, exclude=True)

    model_config = ConfigDict(populate_by_name=True)

    @computed_field
    def id(self) -> str | None:
        return self.metadata.labels.get(WORKLOAD_ID_LABEL)

    @computed_field
    def resource_name(self) -> str:
        return self.metadata.name
