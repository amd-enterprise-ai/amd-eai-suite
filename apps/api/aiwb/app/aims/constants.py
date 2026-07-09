# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Constants for AIM resources."""

from typing import Final

from ..config import AIWB_METADATA_PREFIX

# CRD definitions
AIM_API_GROUP = "aim.eai.amd.com"
# All AIM kinds (AIMService, AIMClusterModel, AIMModel, AIMProfile, AIMClusterProfile) live under v1alpha2.
AIM_API_VERSION: Final[str] = "v1alpha2"
AIM_CLUSTER_MODEL_PLURAL = "aimclustermodels"
AIM_MODEL_PLURAL = "aimmodels"
AIM_SERVICE_RESOURCE = "AIMService"
AIM_SERVICE_PLURAL = "aimservices"
AIM_CLUSTER_PROFILE_PLURAL = "aimclusterprofiles"
AIM_PROFILE_PLURAL = "aimprofiles"
AIM_ARTIFACT_PLURAL = "aimartifacts"
AIM_CLUSTER_MODEL_LABEL = f"{AIM_API_GROUP}/cluster-model.name"
AIM_MODEL_LABEL = f"{AIM_API_GROUP}/model.name"
# Role aim-engine stamps on profiles it derives; base-role profiles emitted by the
# namespace base-image model define the runtime matrix any derived (BYOM) model inherits.
AIM_PROFILE_ROLE_LABEL = f"{AIM_API_GROUP}/profile-role"
AIM_PROFILE_ROLE_BASE = "base"

# HTTPRoute (Gateway API) definitions
HTTP_ROUTE_API_GROUP = "gateway.networking.k8s.io"
HTTP_ROUTE_PLURAL = "httproutes"

# KServe definitions
KSERVE_API_GROUP = "serving.kserve.io"
KSERVE_INFERENCE_SERVICE_PLURAL = "inferenceservices"

# Tag to identify chattable AIM deployments
CHAT_TAG_VALUE = "chat"

# Annotation key on AIMService resources that contains the cluster-auth group ID
CLUSTER_AUTH_GROUP_ANNOTATION = "cluster-auth/allowed-group"

# Annotation key that forces aim-engine to route AIMService reconciliation through
# the v1alpha2 profile pipeline (which writes status.resolvedProfile) instead of
# the default v1alpha1 template pipeline. Without this, AIMServices that only set
# spec.model fall back to v1alpha1's `selectPipeline()` template path and never
# populate status.resolvedProfile — breaking the FE's profile join.
# TODO(EAI-6783): drop once aim-engine removes v1alpha1 and the profile pipeline
# becomes the default. https://amd.atlassian.net/browse/EAI-6783
RECONCILER_PIPELINE_ANNOTATION = f"{AIM_API_GROUP}/reconciler-pipeline"
RECONCILER_PIPELINE_PROFILE = "profile"

# Label stamped on AIMService CRs deployed from namespace-scoped fine-tuned models
FINE_TUNED_LABEL = f"{AIWB_METADATA_PREFIX}/fine-tuned"

# Label stamped on AIMService CRs deployed from namespace-scoped AIMModels
# (fine-tuned and custom-onboarded).
NAMESPACE_AIM_MODEL_LABEL = f"{AIWB_METADATA_PREFIX}/namespace-aim-model"

# AIMService condition types
AIM_COND_INFERENCE_SERVICE_READY = "InferenceServiceReady"
AIM_COND_HTTP_ROUTE_READY = "HTTPRouteReady"

# Conditions that must all be True for a service to be chattable
AIM_CHATTABLE_CONDITIONS = (AIM_COND_INFERENCE_SERVICE_READY, AIM_COND_HTTP_ROUTE_READY)
