# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Resource    resources/common/airm_resource_cleanup.resource
Resource    resources/api/common.resource

*** Test Cases ***
Test Resource Tracking Keywords
    # Test lazy-initializing tracking keywords
    Track Project For Cleanup    test-project-id
    Track Secret For Cleanup    test-secret-id
    Track Storage For Cleanup    test-storage-id
    Track Workload For Cleanup    test-workload-id

    # These should have created the suite variables
    Log    ${CREATED_PROJECT_IDS}
    Log    ${CREATED_SECRET_IDS}
    Log    ${CREATED_STORAGE_IDS}
    Log    ${CREATED_WORKLOAD_IDS}
