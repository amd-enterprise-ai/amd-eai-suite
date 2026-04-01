# Copyright (c) Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import getpass
import os
import re

_cached_prefix = None


def test_prefix():
    """Returns the test prefix for naming resources. Cached per session."""
    global _cached_prefix
    if _cached_prefix is None:
        _cached_prefix = _resolve_prefix()
    return _cached_prefix


def test_name(suffix):
    """Returns ``{prefix}{suffix}`` sanitized for Kubernetes (max 63 chars)."""
    raw = f"{test_prefix()}{suffix}"
    return _sanitize_k8s_name(raw)


def _resolve_prefix():
    explicit = os.environ.get("E2E_TEST_PREFIX")
    if explicit:
        explicit = explicit.rstrip("-")
        return f"e2e-{explicit}-"

    github_run_id = os.environ.get("GITHUB_RUN_ID")
    if github_run_id:
        return f"e2e-ci{github_run_id}-"

    ci_run_id = os.environ.get("CI_RUN_ID")
    if ci_run_id:
        return f"e2e-ci{ci_run_id}-"

    username = getpass.getuser()
    return f"e2e-{username}-"


def _sanitize_k8s_name(name):
    """Lowercase, keep only alphanumeric and hyphens, strip edge hyphens, max 63 chars."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = name.strip("-")
    return name[:63].rstrip("-")
