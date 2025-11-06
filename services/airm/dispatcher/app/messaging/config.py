# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_AIRM_COMMON_VHOST = os.getenv("RABBITMQ_AIRM_COMMON_VHOST", "vh_airm_common")
RABBITMQ_AIRM_COMMON_QUEUE = os.getenv("RABBITMQ_AIRM_COMMON_QUEUE", "airm_common")

RABBITMQ_AIRM_CLUSTER_VHOST = f"vh_{RABBITMQ_USER}"
RABBITMQ_AIRM_CLUSTER_INBOUND_QUEUE = RABBITMQ_USER
