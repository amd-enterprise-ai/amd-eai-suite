# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
This entrypoint is used to run the API locally for development purposes.
It sets up a uvicorn server to host the FastAPI application on localhost:8001.
"""

import os
from pathlib import Path

import uvicorn

# This is used to reload the app when the code changes while developing
# Not used in production
airm_package_path = Path(__file__).resolve().parents[5] / "packages" / "airm"
airm_dispatcher_path = Path(__file__).resolve().parents[5] / "services" / "airm" / "dispatcher"

# Set to 8080 when this is run within a local kubernetes cluster
HTTP_PORT = int(os.getenv("HTTP_PORT", "8002"))

uvicorn.run(
    "app:app",
    host="0.0.0.0",
    port=HTTP_PORT,
    reload=True,
    reload_dirs=[str(airm_dispatcher_path), str(airm_package_path)],
)
