# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Shared Keycloak configuration.

Common configuration used by both AIRM and AIWB for Keycloak authentication.
"""

import os

KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://localhost:8080")
KEYCLOAK_PUBLIC_URL = os.getenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "platform")
OPENID_CONFIGURATION_URL = os.getenv(
    "OPENID_CONFIGURATION_URL", f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
)
DISABLE_JWT_VALIDATION = os.getenv("DISABLE_JWT_VALIDATION", "false") == "true"
