# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Middleware for enforcing the camelCase API convention.

``api_common.schemas.BaseModel`` provides ``alias_generator=to_camel`` and
``populate_by_name=True``, which handles the translation between camelCase
(API / OpenAPI) and snake_case (Python) and generates correct OpenAPI docs.
Because ``populate_by_name`` is ``True``, Pydantic silently accepts *both*
camelCase and snake_case in incoming data.

This middleware closes that gap by rejecting snake_case keys in JSON request
bodies **and** snake_case query-parameter names at the HTTP layer, so the
external API contract is strictly camelCase while internal Python code stays
snake_case.
"""

import json
from urllib.parse import parse_qs

from pydantic.alias_generators import to_camel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


def _is_snake_case(key: str) -> bool:
    """Return True if *key* contains underscores (snake_case indicator)."""
    return "_" in key


def _find_snake_case_keys(obj: object, prefix: str = "") -> list[tuple[str, str]]:
    """Return (dotted_path, expected_camel_path) pairs for any snake_case keys in *obj*."""
    results: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key in obj:
            path = f"{prefix}.{key}" if prefix else key
            if _is_snake_case(key):
                expected = f"{prefix}.{to_camel(key)}" if prefix else to_camel(key)
                results.append((path, expected))
            results.extend(_find_snake_case_keys(obj[key], prefix=path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(_find_snake_case_keys(item, prefix=f"{prefix}[{i}]"))
    return results


def _find_snake_case_query_params(query_string: str) -> list[tuple[str, str]]:
    """Return (snake_param, camelAlias) pairs for any snake_case query params."""
    if not query_string:
        return []
    results: list[tuple[str, str]] = []
    for key in parse_qs(query_string, keep_blank_values=True):
        if _is_snake_case(key):
            results.append((key, to_camel(key)))
    return results


def _error_response(violations: list[tuple[str, str]]) -> JSONResponse:
    """Build a 422 response listing each snake_case field and its camelCase fix."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"field": snake, "expected": camel, "msg": f"use '{camel}' instead of '{snake}'"}
                for snake, camel in violations
            ]
        },
    )


class CamelCaseMiddleware(BaseHTTPMiddleware):
    """Rejects snake_case keys in JSON bodies and query parameters.

    Inspects POST / PUT / PATCH requests with ``application/json`` bodies for
    snake_case keys, and *all* HTTP methods for snake_case query-parameter
    names.  Paths matching any suffix in *exclude_path_suffixes* are skipped
    entirely (e.g. ``/chat`` for OpenAI-compatible endpoints).
    """

    def __init__(self, app: ASGIApp, exclude_path_suffixes: list[str] | None = None):
        super().__init__(app)
        self.exclude_path_suffixes = exclude_path_suffixes or []

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if any(request.url.path.endswith(s) for s in self.exclude_path_suffixes):
            return await call_next(request)

        # Check query parameters (all HTTP methods)
        bad_params = _find_snake_case_query_params(str(request.query_params))
        if bad_params:
            return _error_response(bad_params)

        # Check JSON body (POST / PUT / PATCH only)
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    data = json.loads(await request.body())
                    bad_keys = _find_snake_case_keys(data)
                    if bad_keys:
                        return _error_response(bad_keys)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

        return await call_next(request)
