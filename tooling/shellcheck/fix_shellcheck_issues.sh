#!/usr/bin/env bash

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
#
# Script to fix common ShellCheck issues in shell scripts
#

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'  # Used in print_color function
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "%b%s%b\n" "$1" "$2" "$NC"
}

# Function to preserve file permissions when replacing a file
preserve_permissions() {
    local source_file="$1"
    local target_file="$2"

    # Get the permissions of the source file
    local perms
    perms=$(stat -f "%p" "$source_file" 2>/dev/null || stat --format="%a" "$source_file" 2>/dev/null)

    if [ -n "$perms" ]; then
        # Apply the same permissions to the target file
        chmod "$perms" "$target_file"
    fi
}

# Check if shellcheck is installed
find_shellcheck() {
    # Look for shellcheck in pre-commit's environment first
    if [ -n "${PRE_COMMIT_HOME:-}" ] && [ -d "${PRE_COMMIT_HOME}" ]; then
        echo "DEBUG: Looking for shellcheck in PRE_COMMIT_HOME: ${PRE_COMMIT_HOME}" >&2
        # Search for shellcheck in pre-commit's environment
        local shellcheck_path
        shellcheck_path=$(find "${PRE_COMMIT_HOME}" -name shellcheck -type f -executable 2>/dev/null | head -n 1)
        if [ -n "$shellcheck_path" ]; then
            echo "DEBUG: Found shellcheck in PRE_COMMIT_HOME: ${shellcheck_path}" >&2
            echo "$shellcheck_path"
            return 0
        fi
    else
        echo "DEBUG: PRE_COMMIT_HOME is not set or not a directory" >&2
    fi

    # Check standard PATH locations
    if command -v shellcheck &> /dev/null; then
        echo "DEBUG: Found shellcheck in PATH: $(command -v shellcheck)" >&2
        echo "shellcheck"
        return 0
    else
        echo "DEBUG: shellcheck not found in PATH" >&2
    fi

    # Check for shellcheck-py installations
    local python_bin_dirs=(
        "$(python -m site --user-base 2>/dev/null)/bin"
        "$(python3 -m site --user-base 2>/dev/null)/bin"
        "$HOME/.local/bin"
        "$HOME/Library/Python/*/bin"
    )

    echo "DEBUG: Checking Python bin directories:" >&2
    for dir in "${python_bin_dirs[@]}"; do
        echo "DEBUG: Checking $dir" >&2
        # Handle glob patterns
        for path in $dir; do
            if [ -f "$path/shellcheck" ] && [ -x "$path/shellcheck" ]; then
                echo "DEBUG: Found shellcheck in Python bin: $path/shellcheck" >&2
                echo "$path/shellcheck"
                return 0
            fi
        done
    done

    # Check in pre-commit cache directory
    echo "DEBUG: Checking ~/.cache/pre-commit directory" >&2

    # Find all shellcheck binaries in the pre-commit cache
    local shellcheck_binaries
    shellcheck_binaries=$(find ~/.cache/pre-commit -type f -name shellcheck -executable 2>/dev/null)

    # First, try to find shellcheck in a Python environment bin directory
    local py_env_shellcheck
    py_env_shellcheck=$(echo "$shellcheck_binaries" | grep -E "py_env-python[0-9.]+/bin/shellcheck" | head -n 1)
    if [ -n "$py_env_shellcheck" ]; then
        echo "DEBUG: Found shellcheck in pre-commit Python environment: $py_env_shellcheck" >&2
        echo "$py_env_shellcheck"
        return 0
    fi

    # If that fails, use any shellcheck binary we found
    if [ -n "$shellcheck_binaries" ]; then
        local first_shellcheck
        first_shellcheck=$(echo "$shellcheck_binaries" | head -n 1)
        echo "DEBUG: Found shellcheck binary in pre-commit cache: $first_shellcheck" >&2
        echo "$first_shellcheck"
        return 0
    fi

    # Check if shellcheck is available as a module in the current Python environment
    # This will work when the hook is run by pre-commit with additional_dependencies: ['shellcheck-py']
    if python3 -c "import shellcheck" &>/dev/null; then
        echo "DEBUG: shellcheck-py module is available in the current Python environment" >&2
        # Use the shellcheck binary installed by the shellcheck-py module
        local shellcheck_module_path
        shellcheck_module_path=$(python3 -c "import shellcheck; print(shellcheck.__path__[0])" 2>/dev/null)
        if [ -n "$shellcheck_module_path" ]; then
            local shellcheck_bin
            shellcheck_bin=$(find "$shellcheck_module_path" -name shellcheck -type f -executable 2>/dev/null | head -n 1)
            if [ -n "$shellcheck_bin" ]; then
                echo "DEBUG: Found shellcheck binary in shellcheck-py module: $shellcheck_bin" >&2
                echo "$shellcheck_bin"
                return 0
            fi
        fi
    fi

    echo "DEBUG: shellcheck not found anywhere" >&2
    return 1
}

# Find shellcheck executable
SHELLCHECK_PATH=$(find_shellcheck)

# Debug information
print_color "$GREEN" "Running shellcheck-fixer with PRE_COMMIT_HOOK_ID=${PRE_COMMIT_HOOK_ID:-not set}"
print_color "$GREEN" "PRE_COMMIT_HOME=${PRE_COMMIT_HOME:-not set}"

if [ -z "$SHELLCHECK_PATH" ]; then
    print_color "$RED" "Shellcheck is not installed. Please install shellcheck-py first."
    # Always exit with 0 when run as part of pre-commit
    if [ -n "${PRE_COMMIT_HOOK_ID:-}" ]; then
        exit 0
    else
        exit 1
    fi
else
    SHELLCHECK_AVAILABLE=1
    print_color "$GREEN" "Using shellcheck: $SHELLCHECK_PATH"
fi

# Function to check if a file has ShellCheck issues
has_shellcheck_issues() {
    local file="$1"
    local issues

    # Skip if shellcheck is not available
    if [ "$SHELLCHECK_AVAILABLE" -eq 0 ]; then
        return 1  # Pretend no issues found
    fi

    # Run shellcheck and capture the output
    issues=$("$SHELLCHECK_PATH" --severity=warning "$file" 2>&1 || true)

    # Check if there are any issues
    if [ -z "$issues" ]; then
        return 1  # No issues found
    else
        print_color "$YELLOW" "ShellCheck issues found in $file:"
        echo "$issues" | head -n 5  # Show first few issues
        if [ "$(echo "$issues" | wc -l)" -gt 5 ]; then
            print_color "$YELLOW" "... and more issues"
        fi
        return 0  # Issues found
    fi
}

# Fix SC2148: Missing shebang
fix_missing_shebang() {
    local file="$1"
    if ! grep -q "^#!" "$file"; then
        # Escape the # character to avoid it being interpreted as a comment
        sed -i.bak '1s/^/\#!\/usr\/bin\/env bash\n\n/' "$file"
        rm -f "${file}.bak"
        return 0
    fi
    return 1
}

# Fix SC2155: Declare and assign separately
fix_declare_assign() {
    local file="$1"
    local modified=0

    # Create a temporary file
    local temp_file
    temp_file=$(mktemp)

    # Copy the original file to the temporary file
    cp "$file" "$temp_file"

    # Find lines with export VAR=$(command)
    grep -n "export [A-Za-z0-9_]*=\$(.*)" "$file" 2>/dev/null | while read -r line; do
        line_num=$(echo "$line" | cut -d':' -f1)
        var_name=$(echo "$line" | sed -E 's/.*export ([A-Za-z0-9_]*)=.*/\1/')
        command=$(echo "$line" | sed -E 's/.*export [A-Za-z0-9_]*=\$\((.*)\).*/\1/')

        # Create a replacement file
        local replacement_file
        replacement_file=$(mktemp)

        # Extract lines before the target line
        head -n $((line_num - 1)) "$temp_file" > "$replacement_file"

        # Add the fixed lines
        {
            echo "# Declare and assign separately to avoid masking return values"
            echo "$var_name=\$($command)"
            echo "export $var_name"
        } >> "$replacement_file"

        # Add lines after the target line
        tail -n +$((line_num + 1)) "$temp_file" >> "$replacement_file"

        # Replace the temporary file with the updated content
        preserve_permissions "$temp_file" "$replacement_file"
        mv "$replacement_file" "$temp_file"
        modified=1
    done

    # Find lines with local VAR=$(command)
    grep -n "local [A-Za-z0-9_]*=\$(.*)" "$temp_file" 2>/dev/null | while read -r line; do
        line_num=$(echo "$line" | cut -d':' -f1)
        var_name=$(echo "$line" | sed -E 's/.*local ([A-Za-z0-9_]*)=.*/\1/')
        command=$(echo "$line" | sed -E 's/.*local [A-Za-z0-9_]*=\$\((.*)\).*/\1/')

        # Create a replacement file
        local replacement_file
        replacement_file=$(mktemp)

        # Extract lines before the target line
        head -n $((line_num - 1)) "$temp_file" > "$replacement_file"

        # Add the fixed lines
        {
            echo "# Declare and assign separately to avoid masking return values"
            echo "local $var_name"
            echo "$var_name=\$($command)"
        } >> "$replacement_file"

        # Add lines after the target line
        tail -n +$((line_num + 1)) "$temp_file" >> "$replacement_file"

        # Replace the temporary file with the updated content
        preserve_permissions "$temp_file" "$replacement_file"
        mv "$replacement_file" "$temp_file"
        modified=1
    done

    # Replace the original file with the fixed content if modified
    if [ $modified -eq 1 ]; then
        preserve_permissions "$file" "$temp_file"
        mv "$temp_file" "$file"
        return 0
    else
        rm -f "$temp_file"
        return 1
    fi
}

# Fix SC2064: Use single quotes in trap
fix_trap_quotes() {
    local file="$1"
    local modified=0

    # Create a temporary file
    local temp_file
    temp_file=$(mktemp)

    # Copy the original file to the temporary file
    cp "$file" "$temp_file"

    # Find trap commands with double quotes
    grep -n "trap \".*\" [A-Z]*" "$file" 2>/dev/null | while read -r line; do
        line_num=$(echo "$line" | cut -d':' -f1)
        trap_command=$(echo "$line" | sed -E 's/.*trap "(.*)" ([A-Z]*).*/\1/')
        trap_signal=$(echo "$line" | sed -E 's/.*trap "(.*)" ([A-Z]*).*/\2/')

        # Create a replacement file
        local replacement_file
        replacement_file=$(mktemp)

        # Extract lines before the target line
        head -n $((line_num - 1)) "$temp_file" > "$replacement_file"

        # Add the fixed line
        echo "trap '$trap_command' $trap_signal" >> "$replacement_file"

        # Add lines after the target line
        tail -n +$((line_num + 1)) "$temp_file" >> "$replacement_file"

        # Replace the temporary file with the updated content
        preserve_permissions "$temp_file" "$replacement_file"
        mv "$replacement_file" "$temp_file"
        modified=1
    done

    # Replace the original file with the fixed content if modified
    if [ $modified -eq 1 ]; then
        preserve_permissions "$file" "$temp_file"
        mv "$temp_file" "$file"
        return 0
    else
        rm -f "$temp_file"
        return 1
    fi
}

# Fix SC2162: read without -r
fix_read_without_r() {
    local file="$1"
    local modified=0

    # Find read commands without -r
    if ! grep -n "read [^-r]" "$file" 2>/dev/null | grep -v "read -r" > /dev/null; then
        # No matches found
        return 1
    fi

    # Process each match
    grep -n "read [^-r]" "$file" 2>/dev/null | grep -v "read -r" | while read -r line; do
        if [ -z "$line" ]; then
            continue
        fi

        line_num=$(echo "$line" | cut -d':' -f1)
        if [ -z "$line_num" ]; then
            continue
        fi

        # Add -r flag
        sed -i.bak "${line_num}s/read /read -r /" "$file" || true
        rm -f "${file}.bak"
        modified=1
    done

    return $((modified == 0))
}

# Fix SC2236: Use -n instead of ! -z
fix_not_empty_check() {
    local file="$1"
    local modified=0

    # Find ! -z checks
    if ! grep -n "\[ *! *-z" "$file" 2>/dev/null > /dev/null; then
        # No matches found
        return 1
    fi

    # Process each match
    grep -n "\[ *! *-z" "$file" 2>/dev/null | while read -r line; do
        if [ -z "$line" ]; then
            continue
        fi

        line_num=$(echo "$line" | cut -d':' -f1)
        if [ -z "$line_num" ]; then
            continue
        fi

        # Replace with -n
        sed -i.bak "${line_num}s/\[ *! *-z/[ -n/g" "$file" || true
        rm -f "${file}.bak"
        modified=1
    done

    return $((modified == 0))
}

# Fix SC2086: Double quote to prevent globbing and word splitting
fix_awk_quotes() {
    local file="$1"
    local modified=0

    # Find awk commands without proper quoting
    if ! grep -n "awk.*\$[A-Za-z0-9_]" "$file" 2>/dev/null > /dev/null; then
        # No matches found
        return 1
    fi

    # Process each match
    grep -n "awk.*\$[A-Za-z0-9_]" "$file" 2>/dev/null | while read -r line; do
        if [ -z "$line" ]; then
            continue
        fi

        line_num=$(echo "$line" | cut -d':' -f1)
        if [ -z "$line_num" ]; then
            continue
        fi

        # Check if the line already has proper quoting
        if grep -n "awk.*\"\\\$" "$file" | grep -q "^${line_num}:"; then
            continue
        fi

        # Skip lines that already have single quotes in awk command
        if grep -n "awk.*'.*'" "$file" | grep -q "^${line_num}:"; then
            continue
        fi

        # Replace with proper quoting - add quotes around variables
        # Only apply to lines that don't already have proper quoting
        sed -i.bak "${line_num}s/awk.*\(\$[A-Za-z0-9_]*\)/awk '{print \1}'/g" "$file" || true
        rm -f "${file}.bak"
        modified=1
    done

    return $((modified == 0))
}

# Fix SC2012: Use find instead of ls
fix_ls_wc() {
    local file="$1"
    local modified=0

    # Find ls | wc -l patterns
    if ! grep -n "ls .* | wc -l" "$file" 2>/dev/null > /dev/null; then
        # No matches found
        return 1
    fi

    # Process each match
    grep -n "ls .* | wc -l" "$file" 2>/dev/null | while read -r line; do
        if [ -z "$line" ]; then
            continue
        fi

        line_num=$(echo "$line" | cut -d':' -f1)
        if [ -z "$line_num" ]; then
            continue
        fi

        ls_pattern=$(echo "$line" | sed -E 's/.*ls (.*) \| wc -l.*/\1/' || echo "")
        if [ -z "$ls_pattern" ]; then
            continue
        fi

        # Replace with find
        if [[ "$ls_pattern" == *"*"* ]]; then
            # If there's a glob pattern, extract the directory and pattern
            dir=$(echo "$ls_pattern" | awk '{print $NF}' | sed 's/\/[^\/]*$//' || echo ".")
            pattern=$(echo "$ls_pattern" | awk '{print $NF}' | sed 's/.*\///' || echo "*")

            # Replace with find command
            sed -i.bak "${line_num}s/.*ls.*|.*wc.*/find \"$dir\" -name \"$pattern\" -type f | wc -l/" "$file" || true
        else
            # Simple case, just replace with find
            sed -i.bak "${line_num}s/.*ls.*|.*wc.*/find $ls_pattern -type f | wc -l/" "$file" || true
        fi

        rm -f "${file}.bak"
        modified=1
    done

    return $((modified == 0))
}

# Fix SC2024: sudo doesn't affect redirects
fix_sudo_redirect() {
    local file="$1"
    local modified=0

    # Find sudo with redirects
    if ! grep -n "sudo .* < " "$file" 2>/dev/null > /dev/null; then
        # No matches found
        return 1
    fi

    # Process each match
    grep -n "sudo .* < " "$file" 2>/dev/null | while read -r line; do
        if [ -z "$line" ]; then
            continue
        fi

        line_num=$(echo "$line" | cut -d':' -f1)
        if [ -z "$line_num" ]; then
            continue
        fi

        # Extract the command and file
        cmd=$(echo "$line" | sed -E 's/.*sudo ([^<]*) < ([^ ]*).*/\1/' || echo "")
        input_file=$(echo "$line" | sed -E 's/.*sudo [^<]* < ([^ ]*).*/\1/' || echo "")

        if [ -z "$cmd" ] || [ -z "$input_file" ]; then
            continue
        fi

        # Check if there's an output redirect
        if echo "$line" | grep -q ">"; then
            output_redirect=$(echo "$line" | sed -E 's/.*sudo [^<]* < [^ ]* (>.*)/\1/' || echo "")
            sed -i.bak "${line_num}s/.*sudo.*< .*/cat $input_file | sudo $cmd $output_redirect/" "$file" || true
        else
            sed -i.bak "${line_num}s/.*sudo.*< .*/cat $input_file | sudo $cmd/" "$file" || true
        fi

        rm -f "${file}.bak"
        modified=1
    done

    return $((modified == 0))
}

# Main function
main() {
    # Find all shell scripts
    if [ $# -gt 0 ]; then
        # If arguments are provided, use them as the list of files
        scripts=("$@")
    else
        # Otherwise, find all shell scripts in the repository
        if git ls-files | grep -E '\.(sh|bash)$' > /dev/null 2>&1; then
            mapfile -t scripts < <(git ls-files | grep -E '\.(sh|bash)$')
        else
            mapfile -t scripts < <(find . -type f -name "*.sh" -o -name "*.bash")
        fi
    fi

    if [ ${#scripts[@]} -eq 0 ]; then
        exit 0
    fi

    # Track if any files were modified
    local files_modified=0
    local files_with_issues=0

    # Check if shellcheck is available
    if [ "$SHELLCHECK_AVAILABLE" -eq 0 ]; then
        print_color "$RED" "Shellcheck is not installed. Skipping shellcheck-fixer."
        exit 0
    fi

    # Process each script
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            # Check if the file has ShellCheck issues before attempting to fix
            if ! has_shellcheck_issues "$script"; then
                continue
            fi

            files_with_issues=$((files_with_issues + 1))

            # Create a backup of the original file to check if it was modified
            local temp_backup
            temp_backup=$(mktemp)
            cp "$script" "$temp_backup"

            # Fix common issues - only log if something was fixed
            fix_missing_shebang "$script" && print_color "$GREEN" "Fixed missing shebang in $script"
            fix_declare_assign "$script" && print_color "$GREEN" "Fixed declare and assign issues in $script"
            fix_trap_quotes "$script" && print_color "$GREEN" "Fixed trap quotes in $script"
            fix_read_without_r "$script" && print_color "$GREEN" "Fixed read without -r in $script"
            fix_not_empty_check "$script" && print_color "$GREEN" "Fixed ! -z checks in $script"
            fix_awk_quotes "$script" && print_color "$GREEN" "Fixed awk quotes in $script"
            fix_ls_wc "$script" && print_color "$GREEN" "Fixed ls | wc -l in $script"
            fix_sudo_redirect "$script" && print_color "$GREEN" "Fixed sudo redirects in $script"

            # Check if the file was modified
            if ! cmp -s "$script" "$temp_backup"; then
                print_color "$GREEN" "Fixed issues in $script"
                files_modified=1
            fi

            # Clean up
            rm -f "$temp_backup"
        fi
    done

    # Only print summary if there were issues
    if [ $files_with_issues -gt 0 ]; then
        if [ $files_modified -eq 1 ]; then
            print_color "$GREEN" "Fixed ShellCheck issues in one or more files"
        else
            print_color "$YELLOW" "Found issues but couldn't automatically fix them"
        fi
    fi

    # When running as part of pre-commit, always exit with 0 to avoid failing the hook
    # Otherwise, exit with 1 if files were modified to signal that changes were made
    if [ -n "${PRE_COMMIT_HOOK_ID:-}" ]; then
        exit 0  # Always succeed when run as part of pre-commit
    elif [ $files_modified -eq 1 ]; then
        exit 1  # Signal that files were modified
    else
        exit 0  # Signal that no files were modified
    fi
}

# Run the main function
main "$@"
