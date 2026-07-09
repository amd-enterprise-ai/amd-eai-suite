# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for AIRM UI using Browser Library (Playwright).
...                 Tests verify UI behavior for cluster management, the admin dashboard,
...                 RBAC, storage management, secrets management, and other AIRM UI
...                 features.

Resource            resources/common/suite_setup.resource

Suite Setup         Validate UI test prerequisites
