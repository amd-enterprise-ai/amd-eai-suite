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
airm_package_path = Path(__file__).resolve().parents[5] / "packages" / "airm"
airm_api_path = Path(__file__).resolve().parents[5] / "services" / "airm" / "api"

uvicorn.run("app:app", port=8001, reload=True, reload_dirs=[str(airm_api_path), str(airm_package_path)])
