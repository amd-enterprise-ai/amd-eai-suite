#!/usr/bin/env bash
# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# Robot Framework dry-run validation for pre-push hook.
# Validates keyword names, argument counts, imports, and variable syntax
# without executing any tests.
#
# Scoped to affected specs directories based on changed files.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Determine which specs directories need validation based on changed files.
# Compare against the merge base with the remote tracking branch or origin/main.
BASE_BRANCH="$(git rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || echo 'origin/main')"
MERGE_BASE="$(git merge-base HEAD "$BASE_BRANCH" 2>/dev/null || echo 'HEAD~1')"

CHANGED_FILES="$(git diff --name-only "$MERGE_BASE"..HEAD 2>/dev/null || git diff --name-only HEAD)"

run_aiwb=false
run_aiwb_ui=false
run_airm=false

while IFS= read -r file; do
    case "$file" in
        apps/api/aiwb/specs/*.robot | apps/api/aiwb/specs/*.resource | \
        apps/api/aiwb/specs/arguments.txt | \
        apps/api/aiwb/specs/libraries/*.py | \
        apps/api/aiwb/specs/config/*)
            run_aiwb=true
            ;;
        apps/ui/aiwb/specs/*.robot | apps/ui/aiwb/specs/*.resource | \
        apps/ui/aiwb/specs/arguments.txt | \
        apps/ui/aiwb/specs/libraries/*.py)
            run_aiwb_ui=true
            ;;
        apps/api/airm/specs/*.robot | apps/api/airm/specs/*.resource | \
        apps/api/airm/specs/arguments.txt | \
        apps/api/airm/specs/config/*)
            run_airm=true
            ;;
        # AIRM shared resources are used by AIWB (API and UI) via pythonpath
        apps/api/airm/specs/resources/*)
            run_aiwb=true
            run_aiwb_ui=true
            run_airm=true
            ;;
        # Shared test infrastructure used by both AIRM and AIWB
        testing/*)
            run_aiwb=true
            run_aiwb_ui=true
            run_airm=true
            ;;
    esac
done <<< "$CHANGED_FILES"

if ! $run_aiwb && ! $run_aiwb_ui && ! $run_airm; then
    echo "robot-dryrun: No Robot Framework files changed, skipping."
    exit 0
fi

exit_code=0

run_dryrun() {
    local label="$1"
    local specs_dir="$2"
    local project_path="$3"

    echo "robot-dryrun: Validating ${label} specs..."

    # Capture output and preserve robot's exit code via pipefail
    set +e
    output="$(cd "$specs_dir" && \
        uv run --project "$project_path" robot --dryrun \
            --argumentfile arguments.txt \
            --output NONE --log NONE --report NONE \
            . 2>&1)"
    rc=$?
    set -e

    # Show summary lines (test counts and any errors)
    echo "$output" | grep -E "(tests|FAIL|PASS|Error|No keyword)" | tail -10

    if [ $rc -eq 0 ]; then
        echo "robot-dryrun: ${label} specs OK"
    else
        echo "robot-dryrun: ${label} specs FAILED"
        exit_code=1
    fi
    echo ""
}

if $run_airm; then
    run_dryrun "AIRM" "$REPO_ROOT/apps/api/airm/specs" ".."
fi

if $run_aiwb; then
    run_dryrun "AIWB API" "$REPO_ROOT/apps/api/aiwb/specs" ".."
fi

if $run_aiwb_ui; then
    run_dryrun "AIWB UI" "$REPO_ROOT/apps/ui/aiwb/specs" ".."
fi

exit $exit_code
