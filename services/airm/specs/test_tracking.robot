# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Resource    resources/common/resource_tracking.resource
Resource    resources/api/common.resource

*** Test Cases ***
Test Resource Tracking Keywords
    # Test initialization keywords
    Initialize Project Tracking
    Initialize Secret ID Tracking
    Initialize storage ID tracking
    Initialize Workload ID Tracking
    Initialize Workspace ID Tracking
    Initialize Dataset Tracking

    # These should create the suite variables
    Log    ${CREATED_PROJECT_IDS}
    Log    ${CREATED_SECRET_IDS}
    Log    ${CREATED_STORAGE_IDS}
    Log    ${CREATED_WORKLOAD_IDS}
    Log    ${CREATED_WORKSPACE_IDS}
    Log    ${CREATED_DATASET_IDS}
