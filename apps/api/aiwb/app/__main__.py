# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
This entrypoint is used to run the API locally for development purposes.
It sets up a uvicorn server to host the FastAPI application.
"""

from pathlib import Path

import uvicorn

from .config import API_SERVICE_PORT, LOG_LEVEL


def main():
    # This is used to reload the app when the code changes while developing
    # Not used in production
    api_common_path = Path(__file__).resolve().parents[3] / "packages" / "api_common"
    aiwb_api_path = Path(__file__).resolve().parent
    env_path = Path(__file__).resolve().parents[1] / ".env"

    uvicorn.run(
        "app:app",
        port=API_SERVICE_PORT,
        reload=True,
        reload_dirs=[str(aiwb_api_path), str(api_common_path)],
        reload_includes=["*.py"],
        env_file=str(env_path),
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
