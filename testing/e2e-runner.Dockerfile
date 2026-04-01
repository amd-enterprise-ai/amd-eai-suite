# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# Unified E2E Test Dockerfile for AIRM and AIWB APIs
# This Dockerfile is specifically for running end-to-end tests in CI/CD pipelines
# and includes all testing dependencies and test specifications for both services.

FROM python:3.13 AS base

# Helm binary install
WORKDIR /tmp
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
RUN chmod 700 get_helm.sh
RUN ./get_helm.sh
RUN rm get_helm.sh

# kubectl binary install
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
RUN chmod +x kubectl
RUN mv kubectl /usr/local/bin/

# kubelogin (kubectl oidc-login plugin) for OIDC authentication
RUN KUBELOGIN_VERSION=v1.31.0 && \
    curl -LO "https://github.com/int128/kubelogin/releases/download/${KUBELOGIN_VERSION}/kubelogin_linux_amd64.zip" && \
    python3 -c "import zipfile; zipfile.ZipFile('kubelogin_linux_amd64.zip').extractall('kubelogin_tmp')" && \
    mv kubelogin_tmp/kubelogin /usr/local/bin/kubectl-oidc_login && \
    chmod +x /usr/local/bin/kubectl-oidc_login && \
    rm -rf kubelogin_linux_amd64.zip kubelogin_tmp
# -------------------

WORKDIR /code

# Install uv globally
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir uv

# ========================================
# Shared packages (required by AIWB as editable deps)
# ========================================

# Copy only pyproject.toml and package source (not venvs/caches)
COPY apps/api/api_common/pyproject.toml /code/apps/api/api_common/pyproject.toml
COPY apps/api/api_common/api_common /code/apps/api/api_common/api_common
COPY apps/api/workloads_manager/pyproject.toml /code/apps/api/workloads_manager/pyproject.toml
COPY apps/api/workloads_manager/workloads_manager /code/apps/api/workloads_manager/workloads_manager

# ========================================
# AIRM E2E Test Dependencies
# ========================================

# Copy AIRM dependency files (for installing test dependencies like robotframework)
COPY apps/api/airm/pyproject.toml apps/api/airm/uv.lock /code/apps/api/airm/

# Copy AIRM test specs
COPY apps/api/airm/specs /code/apps/api/airm/specs

# ========================================
# AIWB E2E Test Dependencies
# ========================================

# Copy AIWB dependency files (for installing test dependencies like robotframework)
COPY apps/api/aiwb/pyproject.toml apps/api/aiwb/uv.lock /code/apps/api/aiwb/

# Copy AIWB test specs
COPY apps/api/aiwb/specs /code/apps/api/aiwb/specs

# ========================================
# Testing Infrastructure
# ========================================

# Copy testing infrastructure
COPY testing/entrypoint.sh /code/testing/entrypoint.sh
COPY testing/resources /code/testing/resources
COPY testing/libraries /code/testing/libraries

# Create non-root user and set permissions
RUN useradd -m -u 1000 apiserver && \
    chown -R 1000:1000 /code && \
    chmod +x /code/testing/entrypoint.sh

USER apiserver

# ========================================
# Install Dependencies
# ========================================

# Install AIRM test dependencies with uv (no app code needed, just test deps)
WORKDIR /code/apps/api/airm
RUN uv sync --locked --no-install-project

# Install AIWB test dependencies with uv
WORKDIR /code/apps/api/aiwb
RUN uv sync --locked --no-install-project

# ========================================
# Entrypoint Configuration
# ========================================

# Set working directory for test execution
WORKDIR /code

# Set the entrypoint for test execution
ENTRYPOINT ["/code/testing/entrypoint.sh"]

# Default command runs AIRM tests (can be overridden)
CMD ["apps/api/airm/specs"]
