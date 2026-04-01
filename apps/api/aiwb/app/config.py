# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CLUSTER_HOST = os.getenv("CLUSTER_HOST", "http://localhost:8080")
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
