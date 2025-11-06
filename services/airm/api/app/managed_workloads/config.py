# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

CHAT_STREAM_HTTP_TIMEOUT = float(os.environ.get("CHAT_STREAM_HTTP_TIMEOUT", 20.0))
