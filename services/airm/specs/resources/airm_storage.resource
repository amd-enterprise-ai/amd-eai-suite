# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Core storage management keywords for AIRM testing.
...                 Provides initialization, tracking, and cleanup for storage resources across test suites.
...                 This resource should be imported by test suites to enable automatic storage cleanup.
Resource            api/storage.resource
Resource            common/resource_tracking.resource
Library             Collections


*** Variables ***
${TEST_STORAGE_ID}           ${None}
${SECOND_STORAGE_ID}         ${None}
${TEST_STORAGE_SECRET_ID}    ${None}
@{CREATED_STORAGE_IDS}       # List to track created storage IDs for cleanup


*** Keywords ***
# Initialize storage ID tracking is now imported from common/resource_tracking.resource
# Clean up all created storage is now imported from common/resource_tracking.resource
