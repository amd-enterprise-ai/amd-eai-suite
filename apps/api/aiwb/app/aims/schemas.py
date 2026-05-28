# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from typing import Any

from pydantic import Field, computed_field, model_validator

from api_common.schemas import BaseEntityPublic, BaseModel

from .constants import (
    AIM_CHATTABLE_CONDITIONS,
    CLUSTER_AUTH_GROUP_ANNOTATION,
)
from .crds import AIMClusterModelResource, AIMServiceResource, HTTPRouteResource
from .enums import AIMServiceStatus, OptimizationMetric
from .utils import extract_endpoints, is_condition_true


class ScalingPolicyMixin(BaseModel):
    """Mixin for scaling policy fields.

    For autoscaling, all three fields (minReplicas, maxReplicas, autoScaling) must be
    provided together. For fixed replicas, use only the 'replicas' field instead.

    NOTE: aim-engine enables KEDA when minReplicas/maxReplicas are set, so these fields
    should only be used with a valid autoScaling configuration containing KEDA metrics.
    """

    min_replicas: int | None = Field(
        None,
        ge=1,
        description="Minimum number of replicas for autoscaling. Requires autoScaling config.",
    )
    max_replicas: int | None = Field(
        None,
        ge=1,
        description="Maximum number of replicas for autoscaling. Requires autoScaling config.",
    )
    auto_scaling: dict[str, Any] | None = Field(
        None,
        description=(
            "KEDA autoscaling configuration with custom metrics. Required when using minReplicas/maxReplicas. "
            "Example: {'metrics': [{'type': 'PodMetric', 'podmetric': {'metric': {...}, 'target': {...}}}]}"
        ),
    )

    @model_validator(mode="after")
    def validate_scaling_policy(self) -> "ScalingPolicyMixin":
        """Validate that autoscaling fields are provided together."""
        fields = [self.min_replicas, self.max_replicas, self.auto_scaling]
        fields_set = sum(1 for f in fields if f is not None)

        # All three must be provided together or none at all
        # This prevents accidentally enabling KEDA without valid triggers in aim-engine
        if fields_set > 0 and fields_set < 3:
            raise ValueError(
                "Autoscaling requires all three fields: minReplicas, maxReplicas, and autoScaling. "
                "For fixed replicas, use only the 'replicas' field instead."
            )

        # Validate max_replicas >= min_replicas
        if self.min_replicas is not None and self.max_replicas is not None:
            if self.max_replicas < self.min_replicas:
                raise ValueError(f"maxReplicas ({self.max_replicas}) must be >= minReplicas ({self.min_replicas})")

        # autoScaling must not be empty (would cause KEDA errors)
        if self.auto_scaling is not None and self.auto_scaling == {}:
            raise ValueError("autoScaling cannot be empty - provide valid KEDA metrics configuration")

        return self


class AIMServiceTemplateQuery(BaseModel):
    aim_resource_name: str = Field(..., description="AIMClusterModel resource name")


class AIMServiceListQuery(BaseModel):
    status_filter: list[AIMServiceStatus] | None = Field(default=None, description="Filter by status(es)")


class AIMResponse(AIMClusterModelResource):
    """AIMResponse API response schema."""

    pass


class AIMDeployRequest(ScalingPolicyMixin):
    """Schema for deploying an AIM with optional scaling policy configuration.

    The `model` field can reference either a cluster-scoped AIMClusterModel or a
    namespace-scoped AIMModel (fine-tuned). The API auto-detects which type it is.
    """

    model: str = Field(
        ...,
        description=(
            "Model resource name. Either an AIMClusterModel name (e.g., 'meta-llama-3-8b') "
            "or a namespace-scoped AIMModel name (fine-tuned model UUID). "
            "The API auto-detects which type it is."
        ),
    )
    replicas: int = Field(
        1,
        description="Number of replicas for this service.",
    )
    image_pull_secrets: list[str] | None = Field(
        None,
        description="Names of the secrets for pulling AIM container images. Only applies to cluster-scoped AIMClusterModel deployments.",
    )
    hf_token: str | None = Field(
        None,
        description="Hugging Face token for accessing private models (if required). Only applies to cluster-scoped AIMClusterModel deployments.",
    )
    metric: OptimizationMetric | None = Field(
        None,
        description="Performance optimization metric (latency or throughput). Only applies to cluster-scoped AIMClusterModel deployments.",
    )
    allow_unoptimized: bool = Field(
        False,
        description="Allow unoptimized deployment configurations if available in the cluster.",
    )
    precision: str | None = Field(
        None,
        description="Runtime precision (e.g. fp8, fp16). Passed to AIMServiceOverrides.precision. Only applies to cluster-scoped AIMClusterModel deployments.",
    )
    gpu_model: str | None = Field(
        None,
        description="GPU model (e.g. MI300X). Passed to AIMServiceOverrides.hardware. Only applies to cluster-scoped AIMClusterModel deployments.",
    )
    gpu_count: int | None = Field(
        None,
        ge=1,
        description="Number of GPUs per replica. Passed to AIMServiceOverrides.hardware. Only applies to cluster-scoped AIMClusterModel deployments.",
    )
    template_name: str | None = Field(
        None,
        description="Explicit AIMServiceTemplate name (profile). When set, spec.template.name is used.",
    )


class AIMServicePatchRequest(ScalingPolicyMixin):
    """Request schema for patching an AIMService.

    All fields are optional. Include only the fields you want to update.
    For scaling policy, all three fields (minReplicas, maxReplicas, autoScaling) must be provided together.
    """


class AIMServiceResponse(AIMServiceResource):
    """AIMService API response schema.

    Inherits all fields from AIMServiceResource (metadata, spec, status).
    This is the live K8s CRD data with namespace already in metadata.
    """

    httproute: HTTPRouteResource | None = Field(None, exclude=True)
    inference_service_name: str | None = Field(None, exclude=True)

    @computed_field
    def status_value(self) -> str:
        return self.status.status.value

    @computed_field
    def endpoints(self) -> dict[str, str]:
        # Endpoints require both routing and inference service to be ready.
        # We check both conditions because endpoints represent inference service URLs
        # and should only be shown when the full stack is functional.
        if not all(is_condition_true(self.status.conditions, c) for c in AIM_CHATTABLE_CONDITIONS):
            return {}
        return extract_endpoints(self, httproute=self.httproute, inference_service_name=self.inference_service_name)

    @computed_field
    def cluster_auth_group_id(self) -> str | None:
        """Extract cluster-auth group ID from routing annotations."""
        if not self.spec.routing:
            return None
        routing_annotations = self.spec.routing.get("annotations", {})
        return routing_annotations.get(CLUSTER_AUTH_GROUP_ANNOTATION)


class AIMServiceHistoryResponse(BaseEntityPublic):
    """AIMService history data from database."""

    model: str = Field(..., description="AIM model resource name")
    status: str = Field(..., description="Status")
    metric: OptimizationMetric | None = Field(None, description="Performance optimization metric")


# ---------------------------------------------------------------------------
# Replica response schema
# ---------------------------------------------------------------------------
# These models mirror the subset of Kubernetes pod fields that are useful for
# displaying replica status. Field names follow camelCase via alias_generator,
# with one explicit override: podIP (Kubernetes uses uppercase "IP", not "Ip").
# ---------------------------------------------------------------------------


class ReplicaContainerStatus(BaseModel):
    ready: bool | None = None
    restart_count: int | None = None
    state: dict[str, Any] | None = None


class ReplicaCondition(BaseModel):
    type: str | None = None
    status: str | None = None
    reason: str | None = None
    message: str | None = None


class ReplicaStatus(BaseModel):
    phase: str | None = None
    # sanitize_for_serialization produces "podIP" (K8s JSON format); the serialization alias
    # uses "podIp" (standard camelCase) so the API response is consistent with other fields.
    pod_ip: str | None = Field(None, alias="podIP", serialization_alias="podIp")
    container_statuses: list[ReplicaContainerStatus] | None = None
    conditions: list[ReplicaCondition] | None = None


class ReplicaResources(BaseModel):
    limits: dict[str, str] | None = None


class ReplicaContainer(BaseModel):
    resources: ReplicaResources | None = None


class ReplicaSpec(BaseModel):
    node_name: str | None = None
    containers: list[ReplicaContainer] | None = None


class ReplicaMetadata(BaseModel):
    name: str
    creation_timestamp: str | None = None


class AIMServiceReplicaResponse(BaseModel):
    """Kubernetes pod data for a single AIM service replica."""

    metadata: ReplicaMetadata
    status: ReplicaStatus | None = None
    spec: ReplicaSpec | None = None
