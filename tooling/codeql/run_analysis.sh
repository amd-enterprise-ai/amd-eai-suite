#!/bin/bash

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
set -e

# Ensure results directories exist
mkdir -p /workspace/results/python /workspace/results/javascript

echo "Creating Python CodeQL database..."
codeql database create /workspace/pbrtCodeqlDB-python --language=python --source-root=/workspace/source

echo "Creating JavaScript CodeQL database..."
codeql database create /workspace/pbrtCodeqlDB-javascript --language=javascript --source-root=/workspace/source

echo "Analyzing Python database..."
codeql database analyze /workspace/pbrtCodeqlDB-python --format=sarif-latest --output=/workspace/results/python/results.sarif --ram=2048 -- python-security-extended.qls
codeql database analyze /workspace/pbrtCodeqlDB-python --format=csv --output=/workspace/results/python/results.csv --ram=2048 -- python-security-extended.qls

echo "Analyzing JavaScript database..."
codeql database analyze /workspace/pbrtCodeqlDB-javascript --format=sarif-latest --output=/workspace/results/javascript/results.sarif --ram=4096 -- javascript-security-extended.qls
codeql database analyze /workspace/pbrtCodeqlDB-javascript --format=csv --output=/workspace/results/javascript/results.csv --ram=4096 -- javascript-security-extended.qls

echo "Analysis complete! Results are in /workspace/results/"
