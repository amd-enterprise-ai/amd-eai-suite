# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
from ..quotas.constants import DEFAULT_CATCH_ALL_QUOTA_NAME

MAX_PROJECTS_PER_CLUSTER = 1000
# Groups that have been "reserved" on keycloak by the platform team.
RESERVED_GROUP_NAMES = ["minio-users", "platformadmins"]

# Names that have other meanings in the system and should be avoided for projects
RESTRICTED_PROJECT_NAMES = [DEFAULT_CATCH_ALL_QUOTA_NAME] + RESERVED_GROUP_NAMES

# 63 characters - len("-predictor") - len(workload-id) - 1
# This is because kserve runs into issues if {workload-name}-predictor-{namespace} length > 63
# Workload ID is 11 chars (mw-{8-char-hash})
MAX_PROJECT_NAME_LENGTH = 41
