<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AI Workbench (AIWB) End-to-End Tests

End-to-end tests for AI Workbench features including AIMs (AI Models), datasets, models, workspaces, charts, and fine-tuning workflows.

## Quick Start

### Prerequisites

See the main AIRM E2E test README for complete prerequisites: `../../airm/specs/README.md`

Key requirements:

1. Install development tools (Redflame or silodev)
2. Configure Kubernetes authentication in kubeconfig
3. Set active Kubernetes context

### Running Tests

Tests are run using Robot Framework via `uv run robot`. The specs directory includes an `arguments.txt` file with recommended settings.

**Note:** The `arguments.txt` file includes pythonpath to AIRM specs for shared resources (authorization, deployment, common libraries).

#### Setup

```bash
# Install AIWB dev dependencies (includes Robot Framework and all required libraries)
cd apps/api/aiwb
uv sync --dev

# Navigate to the specs directory
cd specs
```

#### Running Tests

```bash
# Run all tests using arguments.txt (recommended)
uv run --project .. robot --argumentfile arguments.txt .

# Run smoke tests (quick validation)
uv run --project .. robot --argumentfile arguments.txt --include smoke .

# Exclude GPU-intensive tests
uv run --project .. robot --argumentfile arguments.txt --exclude gpu .

# Run a single test suite
uv run --project .. robot --argumentfile arguments.txt aims.robot

# Run a specific test by name
uv run --project .. robot --argumentfile arguments.txt --test "Deploy AIM successfully" .

# Override output directory if needed
uv run --project .. robot --argumentfile arguments.txt --outputdir /custom/path .

# Rerun only failed tests
uv run --project .. robot --argumentfile arguments.txt --rerunfailed results/output.xml .
```

**Common tag filtering patterns:**

```bash
# Quick smoke test (no GPU required)
uv run --project .. robot --argumentfile arguments.txt --include smoke --exclude gpu .

# Run all tests except GPU-intensive ones
uv run --project .. robot --argumentfile arguments.txt --exclude gpu .

# Run only AIM-related tests
uv run --project .. robot --argumentfile arguments.txt --include aims .

# Run only dataset tests
uv run --project .. robot --argumentfile arguments.txt --include datasets .
```

## Test Suites

AI Workbench test suites cover AIMs, API keys, charts, datasets, finetuning, models, workspaces, and AIM catalog testing. List suites with `ls *.robot`.

## Test Architecture

### Directory Structure

```
specs/
├── *.robot                              # Test suite files
├── config/                              # AIM model catalog configuration
├── libraries/                           # Python libraries (AIM catalog generator)
├── resources/
│   ├── aiwb_*.resource                  # Business logic keywords (high-level)
│   ├── api/                             # Low-level HTTP operation keywords
│   └── aims/                            # AIMS-specific resources (API keys)
└── test_data/                           # Sample datasets and chart templates
```

### Shared Resources from AIRM

AIWB tests use shared infrastructure resources from AIRM via pythonpath (authorization, deployment, project management, safe HTTP wrappers, etc.). See `arguments.txt` for the pythonpath configuration and AIRM's `CLAUDE.md` for details on shared infrastructure.

### Import Pattern

AIWB test files use `resources/` prefix for imports. The pythonpath configuration resolves these:

- Local AIWB resources from `apps/api/aiwb/specs/resources/`
- Shared AIRM resources from `apps/api/airm/specs/resources/`

Example:

```robot
*** Settings ***
# Local AIWB resources
Resource    resources/aiwb_aims.resource
Resource    resources/api/aims.resource

# Shared AIRM resources (via pythonpath)
Resource    resources/authorization.resource
Resource    resources/deployment.resource
Resource    resources/airm_projects.resource
Library     libraries.KubeConnection
```

## AIM Catalog Tests

The `aim_catalog.robot` suite auto-discovers AIM models from the cluster and tests each one (deploy → verify → inference → metrics → undeploy).

```bash
# Run full catalog
uv run --project .. robot --argumentfile arguments.txt aim_catalog.robot

# Test a specific model (use INCLUDE_TAGS — --test doesn't work with dynamically generated tests)
uv run --project .. robot --argumentfile arguments.txt --variable INCLUDE_TAGS:model:Qwen3-32B aim_catalog.robot

# Skip models requiring HuggingFace token
uv run --project .. robot --argumentfile arguments.txt --variable EXCLUDE_TAGS:requires-hf-token aim_catalog.robot

# Test only version 0.8.5
uv run --project .. robot --argumentfile arguments.txt --variable AIM_VERSION:0.8.5 aim_catalog.robot

# Test versions >= 0.9.0
uv run --project .. robot --argumentfile arguments.txt --variable AIM_VERSION:>=0.9.0 aim_catalog.robot

# Filter by version tag (alternative to AIM_VERSION)
uv run --project .. robot --argumentfile arguments.txt --variable INCLUDE_TAGS:version:0.8.5 aim_catalog.robot
```

| Variable         | Required         | Description                                                            |
| ---------------- | ---------------- | ---------------------------------------------------------------------- |
| `HF_TOKEN`       | For gated models | HuggingFace token for meta-llama and similar gated models              |
| `AIM_VERSION`    | Optional         | Version filter: `0.8.5` (exact), `>=0.9.0` (range), `latest` (default) |
| `AIWB_API_URL`   | Optional         | Override API URL (auto-resolved from cluster)                          |
| `AIWB_API_TOKEN` | Optional         | Override OIDC token (auto-acquired from kubectl)                       |

See [CLAUDE.md](CLAUDE.md) for model discovery details and filtering options.

## Configuration

The `arguments.txt` file contains common Robot Framework settings. You can override any argument:

```bash
# Override log level for debugging
uv run --project .. robot --argumentfile arguments.txt --loglevel TRACE .

# Set timeout for long-running tests
uv run --project .. robot --argumentfile arguments.txt --test-timeout 30m .

# Change output directory
uv run --project .. robot --argumentfile arguments.txt --outputdir /tmp/results .
```

See `arguments.txt` for available options and AIM catalog filtering.

## Analyzing Test Results

See the main AIRM E2E test README for complete documentation on test result analysis: `../../airm/specs/README.md`

Quick reference:

- HTML reports in `results/`: `log.html`, `report.html`
- Use `silodev services e2e extract` for terminal-based analysis
- Use Redflame `/e2e-report` for AI-powered analysis

## Related Documentation

- **[CLAUDE.md](CLAUDE.md)** - AI assistant guidance for AIWB tests
- **[AIRM E2E README](../../airm/specs/README.md)** - Complete E2E testing documentation
- **[AIRM CLAUDE.md](../../airm/specs/CLAUDE.md)** - Shared test infrastructure documentation
- **[Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)** - Official documentation
