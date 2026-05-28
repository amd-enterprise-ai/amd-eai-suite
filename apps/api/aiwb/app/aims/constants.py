# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Constants for AIM resources."""

from typing import Final

from ..config import AIWB_METADATA_PREFIX

# CRD definitions
AIM_API_GROUP = "aim.eai.amd.com"
# Pin AIM CRDs to v1alpha1. v1alpha2 introduces breaking changes
# (renamed CRDs, restructured specs) and is tracked separately as EAI-2440.
# Switching to v1alpha2 means flipping this constant — every AIM gateway
# call reads from here, no dynamic resolution.
AIM_API_VERSION: Final[str] = "v1alpha1"
AIM_CLUSTER_MODEL_PLURAL = "aimclustermodels"
AIM_MODEL_PLURAL = "aimmodels"
AIM_SERVICE_RESOURCE = "AIMService"
AIM_SERVICE_PLURAL = "aimservices"
AIM_CLUSTER_SERVICE_TEMPLATE_PLURAL = "aimclusterservicetemplates"
AIM_SERVICE_TEMPLATE_PLURAL = "aimservicetemplates"
AIM_CLUSTER_MODEL_LABEL = f"{AIM_API_GROUP}/cluster-model.name"
AIM_MODEL_LABEL = f"{AIM_API_GROUP}/model.name"  # label AIM Engine puts on namespace-scoped AIMServiceTemplates

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

# Label stamped on AIMService CRs deployed from namespace-scoped fine-tuned models
FINE_TUNED_LABEL = f"{AIWB_METADATA_PREFIX}/fine-tuned"

# AIMService condition types
AIM_COND_INFERENCE_SERVICE_READY = "InferenceServiceReady"
AIM_COND_HTTP_ROUTE_READY = "HTTPRouteReady"

# Conditions that must all be True for a service to be chattable
AIM_CHATTABLE_CONDITIONS = (AIM_COND_INFERENCE_SERVICE_READY, AIM_COND_HTTP_ROUTE_READY)
