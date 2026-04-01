#!/bin/bash
# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

cd "$(dirname "$0")" || exit 1

unformatted=$(gofmt -l .)
if [ -n "$unformatted" ]; then
    echo "Error: The following Go files are not formatted:"
    echo "$unformatted"
    echo "Run: make format"
    exit 1
fi
