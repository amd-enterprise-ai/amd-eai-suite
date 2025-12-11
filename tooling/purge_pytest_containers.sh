#!/bin/bash

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# Use this script to purge all Docker containers with names starting with pytest- that
# are left over from previous test runs.

# Get a list of all Docker containers with names starting with pytest-
containers=$(docker ps -a --filter "name=^pytest" --format "{{.ID}}")

# Check if there are any containers to remove
if [ -z "$containers" ]; then
  echo "No pytest containers found."
else
  # Remove each container
  for container in $containers;
  do
    docker rm -f "$container"
    echo "Removed container $container"
  done
fi
