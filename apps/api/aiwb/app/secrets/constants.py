# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Constants for secrets module."""

from ..config import EAI_APPS_METADATA_PREFIX

# Label used to identify the use case of a secret
USE_CASE_LABEL = f"{EAI_APPS_METADATA_PREFIX}/use-case"

# AIRM writes use-case labels with "airm.silogen.com" (a known typo, should be .ai).
# Until AIRM is fixed (SDA-3326), we check this label as a fallback when reading secrets.
AIRM_USE_CASE_LABEL = "airm.silogen.com/use-case"

# Annotation used to identify which user submitted the secret (imported from config)
# Uses annotation (not label) so emails with @ and other special characters are stored as-is.
