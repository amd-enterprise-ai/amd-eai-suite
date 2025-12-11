# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Core secret management keywords for AIRM testing.
...                 Provides initialization, tracking, and cleanup for secrets across test suites.
...                 This resource should be imported by test suites to enable automatic secret cleanup.
Resource            api/secrets.resource
Resource            common/resource_tracking.resource
Library             Collections


*** Variables ***
${TEST_SECRET_ID}           ${None}
${SECOND_SECRET_ID}         ${None}
@{CREATED_SECRET_IDS}       # List to track created secret IDs for cleanup
${SECOND_PROJECT_ID}        ${None}


*** Keywords ***
# Initialize Secret ID Tracking is now imported from common/resource_tracking.resource
# Clean Up All Created Secrets is now imported from common/resource_tracking.resource
