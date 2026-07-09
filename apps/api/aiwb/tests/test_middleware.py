# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for app-level middleware wiring."""

from fastapi.testclient import TestClient

from app import app  # type: ignore[attr-defined]


def test_mcp_messages_endpoint_excluded_from_camelcase_middleware() -> None:
    # fastapi-mcp's SSE transport posts to /mcp/messages/?session_id=...; the
    # snake_case query name is dictated by the MCP protocol, so the
    # CamelCaseMiddleware must skip this path or every MCP POST 422s.
    with TestClient(app) as client:
        response = client.post("/mcp/messages/?session_id=test-session")

    if response.status_code == 422:
        violations = response.json().get("detail", [])
        offending = [v for v in violations if isinstance(v, dict) and v.get("field") == "session_id"]
        assert not offending, (
            "CamelCaseMiddleware rejected session_id on /mcp/messages/; the path must be in exclude_path_suffixes."
        )
