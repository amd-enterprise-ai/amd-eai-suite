#!/bin/bash

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
set -euo pipefail

#
# Unified Container Entrypoint for Robot Framework Testing
#
# This script serves as a generic entrypoint for Robot Framework test containers
# supporting both AIRM and AIWB test suites.
#
# Usage: Pass the test path and any robot framework arguments
# Example: docker run image apps/api/airm/specs --tag smoke
# Example: docker run image apps/api/aiwb/specs --include gpu
#

echo "========================================"
echo "E2E Test Runner for AIRM and AIWB"
echo "========================================"
echo "Running Robot Framework tests with arguments: $*"
echo ""

# Configure kubectl with OIDC credentials if available (for in-cluster E2E runs)
if [ -n "${KEYCLOAK_SERVER_URL:-}" ] && [ -n "${KEYCLOAK_CLIENT_SECRET:-}" ]; then
    echo "Configuring kubectl with OIDC credentials..."
    # Use public URL for OIDC issuer (must match Keycloak's advertised issuer)
    OIDC_ISSUER_URL="${KEYCLOAK_PUBLIC_URL:-${KEYCLOAK_SERVER_URL}}/realms/${KEYCLOAK_REALM}"

    # Set cluster using in-cluster CA and API server
    kubectl config set-cluster in-cluster \
        --server=https://kubernetes.default.svc \
        --certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

    # Set credentials using oidc-login exec plugin
    kubectl config set-credentials e2e-user \
        --exec-command=kubectl \
        --exec-api-version=client.authentication.k8s.io/v1beta1 \
        --exec-arg=oidc-login \
        --exec-arg=get-token \
        --exec-arg=--oidc-issuer-url="${OIDC_ISSUER_URL}" \
        --exec-arg=--oidc-client-id="${KEYCLOAK_CLIENT_ID}" \
        --exec-arg=--oidc-client-secret="${KEYCLOAK_CLIENT_SECRET}" \
        --exec-arg=--username="${E2E_USERNAME}" \
        --exec-arg=--password="${E2E_PASSWORD}" \
        --exec-arg=--grant-type=password

    # Set and use context
    kubectl config set-context e2e-context \
        --cluster=in-cluster \
        --user=e2e-user
    kubectl config use-context e2e-context

    echo "kubectl configured with OIDC credentials for ${E2E_USERNAME}"
    echo ""
fi

# Set up results directory
RESULTS_DIR="/app/testing/results"
mkdir -p "$RESULTS_DIR"

# Find the test path - it's the last argument or the one starting with /code/
TEST_PATH=""
ROBOT_ARGS=()

for arg in "$@"; do
    if [[ "$arg" == /code/* ]]; then
        TEST_PATH="$arg"
    else
        ROBOT_ARGS+=("$arg")
    fi
done

# If no /code/ path found, use the last argument as test path
if [ -z "$TEST_PATH" ]; then
    TEST_PATH="${*: -1}"
    # Remove last argument from ROBOT_ARGS
    ROBOT_ARGS=("${@:1:$(($#-1))}")
fi

VENV_PATH=""
SERVICE_NAME=""

if [[ "$TEST_PATH" == *"apps/api/airm"* ]]; then
    VENV_PATH="/code/apps/api/airm/.venv"
    SERVICE_NAME="AIRM"
elif [[ "$TEST_PATH" == *"apps/api/aiwb"* ]]; then
    VENV_PATH="/code/apps/api/aiwb/.venv"
    SERVICE_NAME="AIWB"
else
    echo "ERROR: Unable to determine service from test path: $TEST_PATH"
    echo "Expected path to contain 'apps/api/airm' or 'apps/api/aiwb'"
    exit 1
fi

echo "Detected service: $SERVICE_NAME"
echo "Test path: $TEST_PATH"
echo "Virtual environment: $VENV_PATH"
echo "Results directory: $RESULTS_DIR"
echo ""

# Activate the appropriate virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo "ERROR: Virtual environment not found at: $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"
echo "Activated virtual environment: $VENV_PATH"
echo ""

# Run the Robot Framework tests
echo "Starting test execution..."
echo "========================================"
set +e  # Temporarily disable exit on error

# Check for arguments.txt file in the test directory
ARGS_FILE="$TEST_PATH/arguments.txt"

# For AIWB tests, add AIRM specs to PYTHONPATH for shared resources
if [[ "$SERVICE_NAME" == "AIWB" ]]; then
    export PYTHONPATH="/code/apps/api/airm/specs:${PYTHONPATH:-}"
    echo "Added AIRM specs to PYTHONPATH for shared resources"
fi

# Change to test directory so relative paths in arguments.txt work correctly
cd "$TEST_PATH"
echo "Working directory: $(pwd)"
echo ""

if [ -f "$ARGS_FILE" ]; then
    echo "Using arguments file: $ARGS_FILE"
    # Place -d flag AFTER --argumentfile to override any outputdir in the arguments file
    robot --argumentfile "$ARGS_FILE" -d "$RESULTS_DIR" "${ROBOT_ARGS[@]}" .
else
    echo "No arguments file found, running with default configuration"
    robot -d "$RESULTS_DIR" "${ROBOT_ARGS[@]}" .
fi

# Get the test execution status
TEST_STATUS=$?
set -e  # Re-enable exit on error

echo "========================================"
echo "Tests completed with status: $TEST_STATUS"
echo ""

# Display results information
echo "Output files generated in $RESULTS_DIR:"
if ! ls -la "$RESULTS_DIR"/*.html "$RESULTS_DIR"/output.xml 2>/dev/null; then
    echo "Warning: Expected output files not found"
fi
echo ""

# Store test status for result retrieval
echo "Creating test status file..."
echo "$TEST_STATUS" > "$RESULTS_DIR/test_status"

# Keep the container alive for result retrieval (5 minutes max)
echo "Container ready for result retrieval."
echo "Robot Framework artifacts (output.xml, log.html, report.html) are available."
echo "Container will remain alive for 5 minutes to allow result retrieval..."
echo ""

# Wait for 5 minutes before exiting
sleep 300

echo "========================================"
echo "Exiting with status code: $TEST_STATUS"
echo "Service: $SERVICE_NAME"
echo "========================================"
exit $TEST_STATUS
