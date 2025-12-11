# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

FROM --platform=linux/amd64 ubuntu:22.04

# Install dependencies
RUN apt-get update -qq && apt-get install -y -qq \
    wget \
    tar \
    curl \
    git \
    python3 \
    python3-pip \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://nodejs.org/dist/v22.11.0/node-v22.11.0-linux-x64.tar.xz -o node.tar.xz \
    && tar -xJf node.tar.xz -C /usr/local --strip-components=1 \
    && rm node.tar.xz \
    && node --version \
    && npm --version

# Set working directory
WORKDIR /workspace

# Download and extract CodeQL
RUN wget -q https://github.com/github/codeql-action/releases/download/codeql-bundle-v2.20.6/codeql-bundle-linux64.tar.gz \
    && tar -xzf codeql-bundle-linux64.tar.gz \
    && rm codeql-bundle-linux64.tar.gz

# Add CodeQL to PATH
ENV PATH="/workspace/codeql:$PATH"

# Copy and set up analysis script first
COPY tooling/codeql/run_analysis.sh /workspace/run_analysis.sh
RUN chmod +x /workspace/run_analysis.sh

# Copy source code (excluding components to reduce scan time)
COPY . /workspace/source

# Create directories for results
RUN mkdir -p /workspace/results/python /workspace/results/javascript

# Set default command
CMD ["/workspace/run_analysis.sh"]
