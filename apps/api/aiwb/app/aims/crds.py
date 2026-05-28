# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Pydantic models for AIMService CRD responses from Kubernetes.

These models are intentionally minimal and lenient:
- Only include fields we actually access in the code
- All fields optional with sensible defaults
- Parsing won't fail if K8s adds/removes fields
- Uses BaseModel with alias_generator=to_camel for K8s camelCase fields
"""

from typing import Any

from pydantic import Field, computed_field

from api_common.schemas import BaseModel

from ..dispatch.crds import K8sMetadata
from ..workloads.constants import WORKLOAD_ID_LABEL
from .enums import AIMClusterModelStatus as AIMClusterModelStatusEnum
from .enums import AIMServiceStatus as AIMServiceStatusEnum


class AIMModelMetadata(BaseModel):
    canonical_name: str | None = None
    description_full: str | None = None
    hf_token_required: bool | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    title: str | None = None
    variants: list[str] = Field(default_factory=list)


class OciMetadata(BaseModel):
    created: str | None = None
    description: str | None = None
    licenses: str | None = None
    revision: str | None = None
    source: str | None = None
    title: str | None = None
    vendor: str | None = None
    version: str | None = None


class AIMImageMetadata(BaseModel):
    model: AIMModelMetadata = Field(default_factory=AIMModelMetadata)
    oci: OciMetadata = Field(default_factory=OciMetadata)
    original_labels: dict[str, str] = Field(default_factory=dict)


class AIMClusterModelSpec(BaseModel):
    image: str = ""


class AIMClusterModelStatusFields(BaseModel):
    status: AIMClusterModelStatusEnum = AIMClusterModelStatusEnum.NOT_AVAILABLE
    image_metadata: AIMImageMetadata = Field(default_factory=AIMImageMetadata)


class AIMClusterModelResource(BaseModel):
    metadata: K8sMetadata
    spec: AIMClusterModelSpec = Field(default_factory=AIMClusterModelSpec)
    status: AIMClusterModelStatusFields = Field(default_factory=AIMClusterModelStatusFields)


class AIMClusterServiceTemplateResource(BaseModel):
    """AIMClusterServiceTemplate CRD resource."""

    metadata: K8sMetadata
    spec: dict[str, Any] = Field(default_factory=dict)
    status: dict[str, Any] = Field(default_factory=dict)


class AIMModelSource(BaseModel):
    """Source for model weights in an AIMModel or AIMClusterModel."""

    model_id: str = ""
    source_uri: str = ""


class AIMModelCustom(BaseModel):
    """Custom model settings (fine-tuned models)."""

    version_policy: str | None = None


class AIMModelSpec(BaseModel):
    """Spec shared by AIMModel and AIMClusterModel (namespace-scoped variant)."""

    aim_id: str | None = None
    image: str = ""
    model_sources: list[AIMModelSource] = Field(default_factory=list)
    custom: AIMModelCustom | None = None
    env: list[dict[str, Any]] = Field(default_factory=list)


class AIMModelCondition(BaseModel):
    """A single status condition on an AIMModel."""

    last_transition_time: str | None = None
    message: str = ""
    observed_generation: int | None = None
    reason: str = ""
    status: str = ""
    type: str = ""


class AIMModelStatusFields(BaseModel):
    """Status for namespace-scoped AIMModel."""

    status: str = ""
    conditions: list[AIMModelCondition] = Field(default_factory=list)
    image_metadata: AIMImageMetadata = Field(default_factory=AIMImageMetadata)
    source_type: str | None = None


class AIMModelResource(BaseModel):
    """Namespace-scoped AIMModel CRD resource."""

    metadata: K8sMetadata
    spec: AIMModelSpec = Field(default_factory=AIMModelSpec)
    status: AIMModelStatusFields = Field(default_factory=AIMModelStatusFields)


class AIMServiceTemplateSpec(BaseModel):
    """Spec for namespace-scoped AIMServiceTemplate."""

    model_name: str = ""
    metric: str | None = None
    precision: str | None = None


class AIMServiceTemplateResource(BaseModel):
    """Namespace-scoped AIMServiceTemplate CRD resource."""

    metadata: K8sMetadata
    spec: AIMServiceTemplateSpec = Field(default_factory=AIMServiceTemplateSpec)
    status: dict[str, Any] = Field(default_factory=dict)


class HTTPRoutePathMatch(BaseModel):
    """HTTPRoute path match configuration."""

    type: str | None = Field(None, description="Path match type (e.g., 'PathPrefix')")
    value: str | None = Field(None, description="Path value to match")


class HTTPRouteMatch(BaseModel):
    """HTTPRoute match configuration."""

    path: HTTPRoutePathMatch | None = Field(None, description="Path match configuration")


class HTTPRouteBackendRef(BaseModel):
    """HTTPRoute backend reference."""

    kind: str | None = Field(None, description="Backend resource kind (e.g., 'Service')")
    name: str | None = Field(None, description="Backend resource name")
    port: int | None = Field(None, description="Backend port")


class HTTPRouteRule(BaseModel):
    """HTTPRoute rule configuration."""

    matches: list[HTTPRouteMatch] = Field(default_factory=list, description="Request match conditions")
    backend_refs: list[HTTPRouteBackendRef] = Field(default_factory=list, description="Backend references")


class HTTPRouteSpec(BaseModel):
    """HTTPRoute spec configuration."""

    rules: list[HTTPRouteRule] = Field(default_factory=list, description="Route rules")


class HTTPRouteResource(BaseModel):
    """HTTPRoute CRD resource from Gateway API."""

    metadata: K8sMetadata
    spec: HTTPRouteSpec = Field(default_factory=HTTPRouteSpec)


class AIMServiceSpec(BaseModel):
    model: dict[str, Any] = Field(default_factory=dict)
    replicas: int = Field(1, description="The current replicas count")
    overrides: dict[str, Any] | None = Field(default=None)
    routing: dict[str, Any] = Field(default_factory=dict)
    cache_model: bool = True
    runtime_config_name: str | None = None
    template: dict[str, Any] = Field(default_factory=dict)
    # Scaling policy fields
    min_replicas: int | None = Field(None, description="Minimum replicas for autoscaling")
    max_replicas: int | None = Field(None, description="Maximum replicas for autoscaling")
    auto_scaling: dict[str, Any] | None = Field(None, description="Advanced autoscaling config")
    env: list[dict[str, Any]] = Field(default_factory=list)
    image_pull_secrets: list[dict[str, Any]] = Field(default_factory=list)


class AIMServiceRuntime(BaseModel):
    """Runtime scaling status from AIMService CRD status.runtime."""

    current_replicas: int | None = None
    desired_replicas: int | None = None
    min_replicas: int | None = None
    max_replicas: int | None = None
    replicas: str | None = None


class ResolvedRef(BaseModel):
    """Resolved reference (template name). Only name is used; scope/uid from K8s are not returned."""

    name: str | None = Field(None, description="Template name")


class AIMServiceStatusFields(BaseModel):
    status: AIMServiceStatusEnum = AIMServiceStatusEnum.PENDING
    routing: dict[str, Any] = Field(default_factory=dict)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    observed_generation: int | None = None
    runtime: AIMServiceRuntime = Field(default_factory=AIMServiceRuntime)
    resolved_model: ResolvedRef | None = None
    resolved_template: ResolvedRef | None = None


class AIMServiceResource(BaseModel):
    metadata: K8sMetadata
    spec: AIMServiceSpec = Field(default_factory=AIMServiceSpec)  # type: ignore
    status: AIMServiceStatusFields = Field(default_factory=AIMServiceStatusFields)  # type: ignore
    httproute: HTTPRouteResource | None = Field(None, repr=False, exclude=True)
    inference_service_name: str | None = Field(None, repr=False, exclude=True)

    @computed_field
    def id(self) -> str | None:
        return self.metadata.labels.get(WORKLOAD_ID_LABEL)
