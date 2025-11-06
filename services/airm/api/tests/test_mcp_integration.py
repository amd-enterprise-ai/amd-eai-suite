# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Basic MCP (Model Context Protocol) integration tests.

These tests verify that the FastAPI MCP server is properly mounted and configured.
For comprehensive MCP protocol testing, see test_mcp_real_integration.py."""


def test_airm_app_has_mcp_integration():
    """Test that the AIRM app has MCP routes properly mounted."""
    from app import app

    # Check that MCP routes exist in the main app
    route_paths = [route.path for route in app.routes if hasattr(route, "path")]
    mcp_routes = [route for route in route_paths if "/mcp" in route]

    # Should have the main MCP routes
    assert len(mcp_routes) >= 2, f"Expected MCP routes, found: {mcp_routes}"
    assert "/mcp" in route_paths, "MCP SSE endpoint should exist"
    assert "/mcp/messages/" in route_paths, "MCP messages endpoint should exist"

    # Verify route methods are correct
    mcp_route = next(route for route in app.routes if hasattr(route, "path") and route.path == "/mcp")
    messages_route = next(route for route in app.routes if hasattr(route, "path") and route.path == "/mcp/messages/")

    assert "GET" in mcp_route.methods, "MCP SSE endpoint should accept GET"
    assert "POST" in messages_route.methods, "MCP messages endpoint should accept POST"
