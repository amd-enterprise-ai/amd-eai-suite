# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Export the AMD Resource Manager OpenAPI spec to JSON.

Usage: python apps/api/airm/scripts/export_openapi.py <output.json>

Run via ``make docs-api`` (which invokes it inside this app's uv environment).
"""

import sys
from pathlib import Path

# Make ``app`` importable regardless of the current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api_common.openapi import export_openapi  # noqa: E402
from app import app  # type: ignore[attr-defined]  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: export_openapi.py <output.json>")
    written = export_openapi(app, sys.argv[1])
    print(f"Wrote {written}")
