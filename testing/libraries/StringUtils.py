# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import re

import yaml


def english_list(string):
    """Splits a natural language list into an array."""
    result_list = re.split(r"(?:\W*,\W*|\W+and\W+)", string)

    def strip_quotes(quoted):
        return quoted.strip("\"'")

    return list(map(strip_quotes, result_list))


def string_includes(str, substr):
    """Returns true if the string includes the substring."""
    return substr in str


def get_test_manifest_string():
    """Returns a test manifest string."""
    return yaml.dump(
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test-pod"},
            "spec": {
                "containers": [{"name": "test-container", "image": "busybox", "command": ["echo", "Hello, World!"]}]
            },
        }
    )
