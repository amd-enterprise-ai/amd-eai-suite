# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

FROM python:3.13

WORKDIR /code

# Install uv and uvicorn globally
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir uv uvicorn

# Copy dependency files first for better layer caching
COPY packages/airm /code/packages/airm
COPY services/airm/dispatcher/pyproject.toml services/airm/dispatcher/uv.lock /code/services/airm/dispatcher/

# Copy application code
COPY services/airm/dispatcher/app /code/services/airm/dispatcher/app

# Create non-root user and set permissions
RUN useradd -m -u 1000 dispatcher && \
    chown -R 1000:1000 /code
USER dispatcher

# Install dependencies with uv as non-root user
WORKDIR /code/services/airm/dispatcher
RUN uv sync --locked --no-dev

# Run the application
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
