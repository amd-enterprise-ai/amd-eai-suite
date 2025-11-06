<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# CodeQL Security Analysis

This directory contains CodeQL security analysis tools for the repository.

## Files

- `codeql.dockerfile` - CodeQL container for security analysis
- `run-codeql-analysis.sh` - Script to run CodeQL analysis locally

## Usage

### Local Analysis

```bash
# Build the container
docker build -f tooling/codeql/codeql.dockerfile -t codeql-analysis .

# Run analysis (results saved to codeql-results/)
docker run --rm -v $(pwd)/codeql-results:/workspace/results codeql-analysis
```

### CI Integration

CodeQL analysis runs automatically on:

- Push to main branch
- Weekly schedule (Sundays at 2 AM UTC)
- Manual workflow dispatch

Results are available in:

- GitHub Security tab (SARIF format)
- CI artifacts (CSV format)

## Architecture Requirements

- **x86_64 runners required** - CodeQL binaries are not compatible with ARM64
- Minimum 8GB RAM recommended for large codebases
- Analysis typically takes 10-15 minutes
