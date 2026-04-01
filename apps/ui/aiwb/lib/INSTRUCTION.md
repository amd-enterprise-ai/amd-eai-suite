<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AIWB Library

AIWB-specific utilities and functions that are not shared with other apps.

## Guidelines

- Place AIWB-only logic here instead of shared packages (`@amdenterpriseai/services`, `@amdenterpriseai/utils`)
- Move shared code to the appropriate package if reuse is needed elsewhere
- Place the data transformation or parsing logic here.
