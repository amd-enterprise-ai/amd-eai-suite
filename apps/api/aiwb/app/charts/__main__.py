# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio

from api_common.database import dispose_db, init_db

from .registration import register_workloads


async def async_main() -> None:
    init_db()
    try:
        await register_workloads()
    finally:
        await dispose_db()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
