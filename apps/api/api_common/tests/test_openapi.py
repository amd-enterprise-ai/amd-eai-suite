# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for the OpenAPI export sanitizer.

The exported spec is committed and drift-checked in CI, so the sanitizer must
deterministically erase environment- and time-specific values. These tests pin
that contract: the same codebase must export byte-identical JSON regardless of
the ``KEYCLOAK_*`` environment or the wall clock at export time.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from api_common.openapi import (
    OPENID_CONNECT_URL_PLACEHOLDER,
    _pin_dynamic_defaults,
    export_openapi,
    sanitize_openapi,
)


def test_pin_dynamic_defaults_replaces_datetime_values() -> None:
    node = {"default": "2025-06-11T09:30:00Z"}
    _pin_dynamic_defaults(node)
    assert node["default"] == "2024-01-01T00:00:00Z"


def test_pin_dynamic_defaults_accepts_fractional_and_offset_forms() -> None:
    for value in ("2025-06-11T09:30:00.123456+02:00", "2025-06-11T09:30:00.5Z"):
        node = {"default": value}
        _pin_dynamic_defaults(node)
        assert node["default"] == "2024-01-01T00:00:00Z"


def test_pin_dynamic_defaults_leaves_non_datetime_defaults_untouched() -> None:
    node = {"default": "active", "other": "2025-06-11T09:30:00Z"}
    _pin_dynamic_defaults(node)
    # Only ``default`` keys are pinned; an arbitrary key that happens to hold a
    # datetime string is not a schema default and must be left alone.
    assert node == {"default": "active", "other": "2025-06-11T09:30:00Z"}


def test_pin_dynamic_defaults_recurses_into_nested_structures() -> None:
    node: dict[str, Any] = {
        "properties": {"created": {"default": "2025-06-11T09:30:00Z"}},
        "items": [{"default": "2030-12-31T23:59:59Z"}],
    }
    _pin_dynamic_defaults(node)
    assert node["properties"]["created"]["default"] == "2024-01-01T00:00:00Z"
    assert node["items"][0]["default"] == "2024-01-01T00:00:00Z"


def test_sanitize_replaces_openid_connect_url() -> None:
    schema = {
        "components": {
            "securitySchemes": {
                "oidc": {
                    "type": "openIdConnect",
                    "openIdConnectUrl": "https://kc.prod.internal/realms/amd/.well-known/openid-configuration",
                },
            }
        }
    }
    sanitize_openapi(schema)
    assert schema["components"]["securitySchemes"]["oidc"]["openIdConnectUrl"] == OPENID_CONNECT_URL_PLACEHOLDER


def test_sanitize_ignores_non_openid_schemes() -> None:
    schema = {"components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}}}
    sanitize_openapi(schema)
    assert schema["components"]["securitySchemes"]["bearer"] == {"type": "http", "scheme": "bearer"}


def test_export_openapi_is_deterministic_and_writes_trailing_newline(tmp_path: Path) -> None:
    app = FastAPI(title="t")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    out = tmp_path / "nested" / "spec.json"
    export_openapi(app, out)

    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n")
    # Re-exporting the same app produces byte-identical output.
    second = tmp_path / "second.json"
    export_openapi(app, second)
    assert second.read_text(encoding="utf-8") == text
    # And it is valid JSON.
    assert json.loads(text)["info"]["title"] == "t"
