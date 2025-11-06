#!/bin/bash

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
set -e

# CodeQL Analysis Script
# This script builds and runs CodeQL analysis locally

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/codeql-results"

echo "🔍 Starting CodeQL Security Analysis..."
echo "Root directory: ${ROOT_DIR}"
echo "Results will be saved to: ${RESULTS_DIR}"

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Build the container
echo "🐳 Building CodeQL container..."
docker build -f "${SCRIPT_DIR}/codeql.dockerfile" -t codeql-analysis "${ROOT_DIR}"

# Run the analysis
echo "🚀 Running CodeQL analysis..."
docker run --rm -v "${RESULTS_DIR}:/workspace/results" codeql-analysis

echo "✅ Analysis complete!"
echo "📊 Results available in: ${RESULTS_DIR}"
echo "   - Python results: ${RESULTS_DIR}/python/"
echo "   - JavaScript results: ${RESULTS_DIR}/javascript/"
