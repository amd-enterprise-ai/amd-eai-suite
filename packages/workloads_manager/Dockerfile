# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy the package directory
COPY . /app/workloads_manager

# ai-workloads repository should be cloned directly into
# workloads_manager/data/ai-workloads
# by the CI/CD pipeline before building the Docker image

# Create a non-root user
RUN useradd -m -u 1000 manager && \
    chown -R manager:manager /app
USER manager

# Install the workloads_manager package in development mode
WORKDIR /app/workloads_manager
RUN uv venv && uv sync --locked

# Initialize and patch workloads during build
RUN uv run wm init

ENTRYPOINT ["uv", "run", "wm"]
CMD ["register", "all", "--yes"]
