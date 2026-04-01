# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       End-to-end testing of full AIM catalog.
...
...                 Auto-discovers Ready AIMs from the cluster API and generates tests
...                 for each model: deploy, verify running, inference, metrics, undeploy.
...
...                 IMPORTANT: Command-line --include/--exclude/--test do NOT work with
...                 dynamically generated tests. Use Robot Framework variables instead:
...                 | robot --variable INCLUDE_TAGS:model:aim-name aim_catalog.robot
...                 | robot --variable EXCLUDE_TAGS:requires-hf-token aim_catalog.robot
...                 | robot --variable AIM_VERSION:>=0.9.0 aim_catalog.robot
...
...                 See CLAUDE.md and README.md for comprehensive documentation.

Resource            resources/aim_catalog_templates.resource
Resource            resources/airm_projects.resource
Resource            resources/api/models.resource
Resource            resources/api_keys.resource
Suite Setup         Setup AIM catalog testing
Suite Teardown      Cleanup AIM catalog testing
Test Timeout        25 minutes


*** Variables ***
${TEST_MODE}        full        # Test mode: full, smoke, or quick
${HF_TOKEN_SECRET_NAME}    huggingface-token    # Name of the HF token secret in the cluster
${INCLUDE_TAGS}     ${None}     # Tags to include (set via --variable INCLUDE_TAGS:model:aim-xxx)
${EXCLUDE_TAGS}     ${None}     # Tags to exclude (set via --variable EXCLUDE_TAGS:requires-hf-token)
${AIM_VERSION}      ${None}     # Version filter: "0.8.5" (exact), ">=0.9.0" (range), "latest" (default dedup)
${MAX_GPU_COUNT}    1           # Set by listener to max gpu_count across all discovered models
${AIM_DEPLOY_TIMEOUT}    1200  # Seconds to wait for AIM to reach Running (20 min, covers large models)


*** Test Cases ***
Placeholder - Will be replaced by generated tests
    [Documentation]    This placeholder test will be removed when dynamic tests are generated
    ...                It has a special tag to prevent RF from filtering it out before the listener runs
    [Tags]    DYNAMIC_TEST_PLACEHOLDER    aims
    No Operation
