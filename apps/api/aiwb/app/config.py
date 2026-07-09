# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CLUSTER_HOST = os.getenv("CLUSTER_HOST", "http://localhost:8080")
# Host interactive workspaces are served on (e.g. https://workspaces.<domain>).
# Kept separate from CLUSTER_HOST (the workloads/inference host) so workspaces get
# their own gateway virtual host and stay clear of the inference routes' exact-match
# vhost and cluster-auth gate on workloads.<domain>.
WORKSPACES_HOST = os.getenv("WORKSPACES_HOST", "http://localhost:8080")
API_SERVICE_PORT = int(os.getenv("API_SERVICE_PORT", 8002))

# Standalone mode: restrict access to default namespace only.
# Combined mode (false): allow access to user's project namespaces.
STANDALONE_MODE = os.getenv("STANDALONE_MODE", "true").lower() == "true"

# Metadata prefixes for labels and annotations on Kubernetes resources
EAI_APPS_METADATA_PREFIX = os.getenv(
    "EAI_APPS_METADATA_PREFIX", "airm.silogen.ai"
)  # TODO: Will change to "apps.eai.amd.com" in the future
AIWB_METADATA_PREFIX = os.getenv("AIWB_METADATA_PREFIX", "aiwb.apps.eai.amd.com")

# Shared annotation key for tracking who submitted a resource
SUBMITTER_ANNOTATION = f"{EAI_APPS_METADATA_PREFIX}/submitter"

# AI Gateway Prometheus metric names — configurable so deployments using a
# different AI gateway or OTel collector can point at their own metric names.
AI_GW_TOKEN_USAGE_METRIC = os.getenv("AI_GW_TOKEN_USAGE_METRIC", "gen_ai_client_token_usage_sum")
AI_GW_REQUEST_DURATION_METRIC = os.getenv(
    "AI_GW_REQUEST_DURATION_METRIC", "gen_ai_server_request_duration_seconds_count"
)
