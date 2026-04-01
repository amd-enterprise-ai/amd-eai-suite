<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AMD Enterprise AI Suite

This repository contains the main services and common Python packages that power the AMD Enterprise AI platform. The suite is composed of **AI Workbench** (an interface for developers to manage the lifecycle of their AI workloads, including features like AI workspaces, AIMs catalog and fine-tuning) and **AI Resource Manager** (the infrastructure layer for authentication, access control, and cluster coordination). The components are organized under the `apps/` directory.

## Architecture and Deployment Modes

The platform supports three deployment modes to accommodate different use cases:

- **Standalone AIWB**: Deploy only AI Workbench features (AIMs, workloads, workspaces, fine-tuning) without resource management capabilities. Located in `apps/api/aiwb/`.
- **Standalone AIRM**: Deploy only AI Resource Manager features (cluster management, authentication, quota management) without AI development tools. Located in `apps/api/airm/`.
- **Combined AIWB + AIRM**: Deploy both services together for a full-featured platform with AI development tools and resource management.

The main components include:

- **AIWB API**: AI Workbench API for managing AIMs, workloads, workspaces, and fine-tuning jobs. Can run standalone or integrated with AIRM.
- **AIRM API**: AI Resource Manager API handling authentication, access control, cluster coordination, and quota management. Can run standalone or integrated with AIWB.
- **AIWB UI**: Frontend interface for AI Workbench features (AIMs catalog, workspaces, fine-tuning, chat). Located in `apps/ui/aiwb/`.
- **AIRM UI**: Frontend interface for Resource Manager features (cluster management, quota allocation, project management). Located in `apps/ui/airm/`.
- **Agent**: A Kubernetes cluster agent that handles resource management, messaging, and heartbeats for the AIRM system.

---

## Components Overview

### AIWB API

The AI Workbench API provides features for AI development and deployment, including AIMs (AMD Inference Microservices) deployment, model fine-tuning, dataset management, AI workspaces, and API keys for programmatic access. This service can run standalone or be integrated with AIRM for combined deployment.

- **Docs**: [`apps/api/aiwb/README.md`](apps/api/aiwb/README.md)
- **Tech**: FastAPI, PostgreSQL, Kubernetes API, MinIO
- **Testing**: `uv run pytest`

### AIRM API

The AI Resource Manager API handles authentication, access control, cluster coordination, and quota management across organizations, projects, and environments. This service can run standalone or be integrated with AIWB for combined deployment.

- **Docs**: [`apps/api/airm/README.md`](apps/api/airm/README.md)
- **Tech**: FastAPI, PostgreSQL, Keycloak, RabbitMQ, Vault
- **Testing**: `uv run pytest`

### AIWB UI

The AI Workbench UI provides the frontend interface for AI development features including interactive chat, AI workspaces management, AIMs catalog browsing and deployment, and fine-tuning job configuration.

- **Docs**: [`apps/ui/aiwb/README.md`](apps/ui/aiwb/README.md)
- **Tech**: Next.js, Hero UI, Keycloak SSO
- **Testing**: `pnpm test`

### AIRM UI

The AI Resource Manager UI provides the frontend interface for resource management features including cluster onboarding, quota allocation, project management, and job monitoring.

- **Docs**: [`apps/ui/airm/README.md`](apps/ui/airm/README.md)
- **Tech**: Next.js, Hero UI, Keycloak SSO
- **Testing**: `pnpm test`

### Agent

A Kubernetes cluster agent that handles resource management, messaging, and heartbeats for the AIRM system. Written in Go for efficient resource monitoring and cluster communication.

- **Docs**: [`apps/agent/README.md`](apps/agent/README.md)
- **Tech**: Go, Kubernetes, RabbitMQ
- **Testing**: `make test`

---

## Setup Instructions

### Prerequisites

- Python 3.13
- Go 1.24 for agent development
- Pre-commit (`uv tool pip install pre-commit`)
- Docker & Docker Compose
- Node.js & `pnpm` for frontend
- `uv` for Python dependency management

> Windows users should use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) for full compatibility.

### Repository Setup

```bash
git clone <this-repo>
cd <repo>

# Install pre-commit hooks (both pre-commit and pre-push)
uv tool run pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
```

> **Note**: The pre-push hooks will automatically run tests with coverage for any changed components, and it would exit at the first failed test:
>
> - **UI changes**: Runs tests in `apps/ui/airm`
> - **API changes**: Runs tests in `apps/api/airm`
> - **Agent changes**: Runs tests in `apps/agent`
>
> These hooks help catch issues before pushing to remote and ensure code quality standards are met.
