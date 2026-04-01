# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from api_common.schemas import BaseEntityPublic

from .constants import CLUSTER_AUTH_GROUP_ANNOTATION
from .crds import AIMClusterModelResource, AIMServiceResource, HTTPRouteResource
from .enums import AIMServiceStatus as AIMServiceStatusEnum
from .enums import OptimizationMetric
from .utils import extract_endpoints


class ScalingPolicyMixin(BaseModel):
    """Mixin for scaling policy fields.

    For autoscaling, all three fields (minReplicas, maxReplicas, autoScaling) must be
    provided together. For fixed replicas, use only the 'replicas' field instead.

    NOTE: aim-engine enables KEDA when minReplicas/maxReplicas are set, so these fields
    should only be used with a valid autoScaling configuration containing KEDA metrics.
    """

    min_replicas: Annotated[
        int | None,
        Field(
            ge=1,
            alias="minReplicas",
            description="Minimum number of replicas for autoscaling. Requires autoScaling config.",
        ),
    ] = None
    max_replicas: Annotated[
        int | None,
        Field(
            ge=1,
            alias="maxReplicas",
            description="Maximum number of replicas for autoscaling. Requires autoScaling config.",
        ),
    ] = None
    auto_scaling: Annotated[
        dict[str, Any] | None,
        Field(
            alias="autoScaling",
            description=(
                "KEDA autoscaling configuration with custom metrics. Required when using minReplicas/maxReplicas. "
                "Example: {'metrics': [{'type': 'PodMetric', 'podmetric': {'metric': {...}, 'target': {...}}}]}"
            ),
        ),
    ] = None

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


class AIMResponse(AIMClusterModelResource):
    """AIMResponse API response schema."""

    pass


class AIMDeployRequest(ScalingPolicyMixin):
    """Schema for deploying an AIM with optional scaling policy configuration."""

    model: str = Field(
        ...,
        description="AIMClusterModel resource name (e.g., 'meta-llama-3-8b'). Must reference an existing model in the cluster.",
    )
    replicas: int = Field(
        1,
        description="Number of replicas for this service.",
    )
    image_pull_secrets: list[str] | None = Field(
        None,
        description="Names of the secrets for pulling AIM container images.",
        alias="imagePullSecrets",
    )
    hf_token: str | None = Field(
        None,
        description="Hugging Face token for accessing private models (if required).",
        alias="hfToken",
    )
    metric: OptimizationMetric | None = Field(
        None,
        description="Performance optimization metric (latency or throughput). If not specified, default optimization will be used.",
    )
    allow_unoptimized: bool = Field(
        False,
        description="Allow unoptimized deployment configurations if available in the cluster.",
        alias="allowUnoptimized",
    )

    model_config = ConfigDict(populate_by_name=True)


class AIMServicePatchRequest(ScalingPolicyMixin):
    """Request schema for patching an AIMService.

    All fields are optional. Include only the fields you want to update.
    For scaling policy, all three fields (minReplicas, maxReplicas, autoScaling) must be provided together.
    """

    model_config = ConfigDict(populate_by_name=True)


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
        if self.status.status != AIMServiceStatusEnum.RUNNING:
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

    model_config = ConfigDict(from_attributes=True)
