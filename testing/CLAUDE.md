<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# Claude Code Guide: Shared Testing Infrastructure

This document provides context and guidance for Claude Code when working with the shared E2E testing infrastructure under `testing/`.

For app-specific test guidance, see each app's `specs/CLAUDE.md`. For the human-readable overview, see `README.md`.

## SSL Certificate Verification

E2E tests disable SSL certificate verification by default via the `${VERIFY_SSL}` variable (defined in `testing/resources/api/endpoints.resource`). This handles clusters with self-signed certificates, missing certificate extensions, or corporate MITM proxies.

To enable SSL verification: `--variable VERIFY_SSL:${TRUE}` on the command line or in `arguments.txt`.

All HTTP calls must use `verify=${VERIFY_SSL}`:

- Safe wrappers (`common.resource`) pass it automatically on every request
- Direct POST/PUT calls for multipart uploads must include it explicitly
- `KubeconfigAuth.py` always uses `verify=False` (Python library, cannot read RF variables)

When adding new HTTP calls, follow one of these patterns:

- Use Safe wrappers (`Safe Get Request`, `Safe Post Request`, etc.) which handle verify automatically
- For direct `POST`/`PUT` calls (e.g., multipart file uploads that cannot use Safe wrappers), add `verify=${VERIFY_SSL}` explicitly
- For `Create Session` calls to external endpoints, add `verify=${VERIFY_SSL}`
