<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# Shell Script Testing and Linting

This directory contains tools for testing and linting shell scripts in the project.

## ShellCheck Integration

[ShellCheck](https://www.shellcheck.net/) is a static analysis tool for shell scripts that provides warnings and suggestions for bash/sh shell scripts. It's integrated into our pre-commit hooks to automatically check shell scripts before committing.

### Setup

1. ShellCheck is already configured in the pre-commit hooks. When you run `pre-commit install`, it will be set up automatically.

2. The configuration for ShellCheck is in the `.shellcheckrc` file at the root of the repository.

### Running ShellCheck Manually

To run ShellCheck manually on a specific script:

```bash
shellcheck path/to/your/script.sh
```

To run ShellCheck on all shell scripts in the repository:

```bash
pre-commit run shellcheck --all-files
```

### Fixing Common ShellCheck Issues

We've provided a script to automatically fix common ShellCheck issues:

```bash
./scripts/fix_shellcheck_issues.sh
```

This script will:

1. Add missing shebangs to scripts
2. Fix SC2155 (declare and assign separately)
3. Fix SC2064 (use single quotes in trap commands)
4. Fix SC2162 (add -r flag to read commands)

### Common ShellCheck Issues and How to Fix Them

1. **SC2148: Missing shebang**
   - Add `#!/usr/bin/env bash` at the beginning of your script

2. **SC2155: Declare and assign separately**
   - Instead of: `local var=$(command)`
   - Use:
     ```bash
     local var
     var=$(command)
     ```

3. **SC2064: Use single quotes in trap**
   - Instead of: `trap "rm -f $file" EXIT`
   - Use: `trap 'rm -f "$file"' EXIT`

4. **SC2162: read without -r**
   - Instead of: `read var`
   - Use: `read -r var`

5. **SC2086: Double quote to prevent globbing and word splitting**
   - Instead of: `command $var`
   - Use: `command "$var"`

For more information, visit the [ShellCheck Wiki](https://github.com/koalaman/shellcheck/wiki).

# Scripts Directory

This directory contains utility scripts for the project.

## fix_shellcheck_issues.sh

A script to automatically fix common ShellCheck issues in shell scripts. This script is used as a pre-commit hook to ensure shell scripts follow best practices.

### Features

- Preserves file permissions when modifying scripts
- Fixes common ShellCheck issues:
  - SC2148: Missing shebang
  - SC2155: Declare and assign separately
  - SC2064: Use single quotes in trap
  - SC2162: read without -r
  - SC2236: Use -n instead of ! -z
  - SC2086: Double quote to prevent globbing and word splitting
  - SC2012: Use find instead of ls
  - SC2024: sudo doesn't affect redirects

### Usage

```bash
# Run on all shell scripts in the repository
./scripts/fix_shellcheck_issues.sh

# Run on specific files
./scripts/fix_shellcheck_issues.sh path/to/script1.sh path/to/script2.sh
```

The script is also configured as a pre-commit hook in `.pre-commit-config.yaml`.
