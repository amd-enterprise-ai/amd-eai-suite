<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# Third-Party Components

This directory documents all third-party software components included in AMD Resource Manager and AMD AI Workbench.

## Layout

Each subdirectory represents a vendored or embedded third-party component and contains:

- `README.md` — source, version, license, and any modifications made
- License and notice files (copied from the upstream project)

## Dependency categories

### Vendored / embedded (this directory)

Components whose source files are physically present in this repository. Add a subdirectory
here when embedding a new third-party component.

### Registry-pulled dependencies (not in this directory)

Python packages (PyPI), Node.js packages (npm/pnpm), and Go modules are fetched at build
time from public registries. They are not vendored here. Their licenses and copyright notices
are catalogued in:

- [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md) — human-readable disclosure
- [`../sbom.json`](../sbom.json) — machine-readable CycloneDX 1.7 SBOM (Python + Node.js + Go, regenerate with `python3 scripts/generate-sbom.py`)

Lock files that pin exact versions:

- `apps/api/aiwb/uv.lock`
- `apps/api/airm/uv.lock`
- `apps/api/api_common/uv.lock`
- `apps/api/workloads_manager/uv.lock`
- `apps/ui/pnpm-lock.yaml`
