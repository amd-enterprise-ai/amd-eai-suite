# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

RABBITMQ_ADMIN_USER = os.getenv("RABBITMQ_ADMIN_USER", "guest")
RABBITMQ_ADMIN_PASSWORD = os.getenv("RABBITMQ_ADMIN_PASSWORD", "guest")
RABBITMQ_MANAGEMENT_URL = os.getenv("RABBITMQ_MANAGEMENT_URL", "http://localhost:15672/api")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_AIRM_COMMON_VHOST = "vh_airm_common"
RABBITMQ_AIRM_COMMON_QUEUE = "airm_common"
