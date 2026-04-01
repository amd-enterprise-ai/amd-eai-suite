#!/usr/bin/env bash
# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# Run Spectral linting on an API's OpenAPI spec
# This script exports the OpenAPI schema and runs Spectral validation
#
# Usage:
#   run_spectral.sh <api_dir>          # Runs lint and cleans up openapi.json
#   run_spectral.sh <api_dir> --keep   # Runs lint and keeps openapi.json
#
# Example:
#   tooling/spectral/run_spectral.sh apps/api/airm

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -z "$1" || "$1" == "--keep" ]]; then
    echo "Usage: $0 <api_dir> [--keep]" >&2
    echo "Example: $0 apps/api/airm" >&2
    exit 1
fi

API_DIR="$1"
KEEP_FILE=false
if [[ "${2:-}" == "--keep" ]]; then
    KEEP_FILE=true
fi

# Security: Validate API_DIR doesn't contain path traversal
if [[ "$API_DIR" == *".."* ]] || [[ "$API_DIR" == /* ]]; then
    echo "Error: API_DIR must be a relative path without '..' or absolute paths" >&2
    echo "Provided: $API_DIR" >&2
    exit 1
fi

# Validate API directory exists
if [[ ! -d "$REPO_ROOT/$API_DIR" ]]; then
    echo "Error: API directory does not exist: $REPO_ROOT/$API_DIR" >&2
    exit 1
fi

# Change to API directory
cd "$REPO_ROOT/$API_DIR"

# Export OpenAPI schema
echo "Exporting OpenAPI schema..." >&2
uv run python "$SCRIPT_DIR/export_openapi.py" openapi.json

# Run Spectral lint (ruleset is in repo root)
echo "Running Spectral lint..." >&2
npx @stoplight/spectral-cli@6.15.0 lint openapi.json --ruleset "$REPO_ROOT/.spectral.yaml" --fail-severity error

# Cleanup unless --keep flag is set
if [[ "$KEEP_FILE" == "false" ]]; then
    echo "Cleaning up openapi.json..." >&2
    rm -f openapi.json
fi
