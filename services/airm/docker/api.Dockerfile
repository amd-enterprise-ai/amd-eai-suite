# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

FROM python:3.13

# Helm binary install
WORKDIR /tmp
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
RUN chmod 700 get_helm.sh
RUN ./get_helm.sh
RUN rm get_helm.sh
# -------------------

WORKDIR /code

# Install uv and uvicorn globally
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir uv uvicorn

# Copy dependency files first for better layer caching
COPY packages/airm /code/packages/airm
COPY packages/workloads_manager /code/packages/workloads_manager
COPY services/airm/api/pyproject.toml services/airm/api/uv.lock /code/services/airm/api/

# Copy application code
COPY services/airm/api/app /code/services/airm/api/app
COPY services/airm/api/migrations /code/migrations

# Create non-root user and set permissions
RUN useradd -m -u 1000 apiserver && \
    chown -R 1000:1000 /code
USER apiserver

# Install dependencies with uv as non-root user
WORKDIR /code/services/airm/api
RUN uv sync --locked --no-dev

# Run the application
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
