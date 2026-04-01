# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Constants for AIM resources."""

# CRD definitions
AIM_API_GROUP = "aim.eai.amd.com"
AIM_CLUSTER_MODEL_PLURAL = "aimclustermodels"
AIM_SERVICE_RESOURCE = "AIMService"
AIM_SERVICE_PLURAL = "aimservices"
AIM_CLUSTER_SERVICE_TEMPLATE_PLURAL = "aimclusterservicetemplates"
AIM_CLUSTER_MODEL_LABEL = f"{AIM_API_GROUP}/cluster-model.name"

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
