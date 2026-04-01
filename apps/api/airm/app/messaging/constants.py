# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

DEAD_LETTER_EXCHANGE = "dlx_exchange"
DEAD_LETTER_ROUTING_KEY = "dlx_key"
DEAD_LETTER_QUEUE_NAME = "dlx_queue"

DEFAULT_QUEUE_ARGUMENTS = {
    "x-queue-type": "quorum",
    "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
    "x-dead-letter-routing-key": DEAD_LETTER_ROUTING_KEY,
}
