<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AMD Enterprise AI Suite

This repository contains the main services and common Python packages that power the AMD Enterprise AI platform. The suite is composed of **AI Workbench** (an interface for developers to manage the lifecycle of their AI workloads, including features like AI workspaces, AIMs catalog and fine-tuning) and **AI Resource Manager** (the infrastructure layer for authentication, access control, and cluster coordination). The two components currently share API and UI, and are located together in `services/airm`.

The main components include:

- **API** – The central API layer for AMD Resource Manager, handling authentication, access control, and cluster coordination.
- **UI** – The frontend interface to interact with resource management features, integrated with the AIRM API and authentication services.
- **Dispatcher** – The agent responsible for dispatching compute workloads to registered Kubernetes clusters and managing their lifecycle.

---

## Components Overview

### API

The API layer handles both AI Resource Manager and AI Workbench functionality, coordinating organizations, projects, quotas, and clusters across environments. It also provides AI Workbench features including AIMs (AMD Inference Microservices) deployment, model fine-tuning, dataset management, AI workspaces, and API keys for programmatic access. The API exposes a Swagger UI and supports OAuth2 authentication.

- **Docs**: [`services/airm/api/README.md`](services/airm/api/README.md)
- **Tech**: FastAPI, PostgreSQL, Keycloak, RabbitMQ, MinIO
- **Testing**: `uv run pytest`

### UI

The UI allows users to onboard clusters, allocate resources, and monitor jobs visually. It also provides AI Workbench features including interactive chat, model comparison, AI workspaces management, model catalog browsing, and fine-tuning job configuration. Built with Next.js and uses Keycloak-based SSO.

- **Docs**: [`services/airm/ui/README.md`](services/airm/ui/README.md)
- **Tech**: Next.js, Hero UI, Keycloak SSO
- **Testing**: `pnpm test`

### Dispatcher

A cluster-side component that receives instructions from the API and interacts with Kubernetes via KubeAPI. Intended to run directly on Kubernetes clusters.

- **Docs**: [`services/airm/dispatcher/README.md`](services/airm/dispatcher/README.md)
- **Tech**: Python, FastAI
- **Testing**: `uv run pytest`

---

## Setup Instructions

### Prerequisites

- Python 3.13
- Pre-commit (`pip install pre-commit`)
- Docker & Docker Compose
- Node.js & `pnpm` for frontend
- `uv` for Python dependency management

> 💡 Windows users should use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) for full compatibility.

### Repository Setup

```bash
git clone <this-repo>
cd <repo>

# Install pre-commit hooks (both pre-commit and pre-push)
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
```

> **Note**: The pre-push hooks will automatically run tests with coverage for any changed components, and it would exit at the first failed test:
>
> - **UI changes**: Runs tests in `services/airm/ui`
> - **API changes**: Runs tests in `services/airm/api`
> - **Dispatcher changes**: Runs tests in `services/airm/dispatcher`
>
> These hooks help catch issues before pushing to remote and ensure code quality standards are met.
