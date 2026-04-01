# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for AIWB using Browser Library (Playwright).
...                 Tests verify UI behavior for AIM versioning, deployment, and workload tracking.

Resource            resources/common/suite_setup.resource

Suite Setup         Validate UI test prerequisites
