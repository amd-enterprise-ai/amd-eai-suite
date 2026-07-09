# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Constants for namespaces module."""

from ..config import EAI_APPS_METADATA_PREFIX

# Label used to identify and discover workbench namespaces
# Any namespace with this label is considered a valid workbench namespace
NAMESPACE_ID_LABEL = f"{EAI_APPS_METADATA_PREFIX}/project-id"
