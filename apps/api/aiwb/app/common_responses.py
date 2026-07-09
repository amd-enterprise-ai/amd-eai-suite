# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Reusable OpenAPI ``responses=`` fragments for FastAPI route decorators.

These dicts describe the documented failure modes raised by common dependencies
(``ensure_access_to_project`` / ``ensure_access_to_workbench_namespace``) and
shared service-layer exception paths. Compose with the spread operator:

    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "AIM deployment not found in the project."},
    }

If the underlying access-check dependency or exception handler ever changes
(e.g. an exception type is remapped to a different status code), update the
matching dict here rather than the individual route decorators.
"""

# Raised by ensure_access_to_project / ensure_access_to_workbench_namespace.
# 403: caller lacks the project group claim (combined mode), the project
#      does not match the standalone default (standalone mode), or the
#      namespace is not a workbench namespace.
# 404: project namespace does not exist in Kubernetes.
PROJECT_ACCESS_RESPONSES: dict[int | str, dict] = {
    403: {"description": "Caller does not have access to the project, or the project is not a workbench namespace."},
    404: {"description": "Project or namespace not found."},
}

# For endpoints that require cluster-auth to be enabled (api-keys router).
CLUSTER_AUTH_RESPONSES: dict[int | str, dict] = {
    503: {
        "description": "Cluster-auth is disabled or unavailable; API key operations require CLUSTER_AUTH_ENABLED=true."
    },
}

# Raised by ensure_user_logged_in (applied to all secured routes via api_secured_router).
# 401: Authorization header is missing, expired, or JWT validation fails.
# 403: JWT is valid but missing the email claim (misconfigured token / wrong audience).
#      Endpoints that also spread PROJECT_ACCESS_RESPONSES will override this 403
#      description with their own project-access wording.
AUTH_RESPONSES: dict[int | str, dict] = {
    401: {"description": "Missing or invalid authentication token."},
    403: {"description": "Token is valid but missing required claims (e.g. email)."},
}
