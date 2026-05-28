# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
This entrypoint is used to run the API locally for development purposes.
It sets up a uvicorn server to host the FastAPI application on localhost:8001.
"""

from pathlib import Path

import uvicorn

# This is used to reload the app when the code changes while developing
# Not used in production
_repo_root = Path(__file__).resolve().parents[4]
airm_app_path = _repo_root / "apps" / "api" / "airm"
api_common_path = _repo_root / "apps" / "api" / "api_common"

uvicorn.run(
    "app:app",
    port=8001,
    reload=True,
    reload_dirs=[str(airm_app_path), str(api_common_path)],
)
