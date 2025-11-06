# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import datetime

test_run_id_value = None


def test_run_id():
    """Returns a unique test run id. It is generated once and then cached."""
    global test_run_id_value
    if test_run_id_value is None:
        test_run_id_value = generate_test_run_id()
    return test_run_id_value


def generate_test_run_id():
    now = datetime.datetime.now()
    milliseconds = int(now.microsecond / 1000)
    return f"t{now.strftime('%Y%m%d-%H%M%S')}-{milliseconds}"
