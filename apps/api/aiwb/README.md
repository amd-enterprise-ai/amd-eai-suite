<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AI Workbench API

## Overview

The AI Workbench (AIWB) API provides AI development and deployment features independently from the AI Resource Manager (AIRM). This standalone deployment is suitable for scenarios where you want AI Workbench capabilities (AIMs, workloads, workspaces, fine-tuning) without integrated cluster resource management.

## Deployment Modes

The AI Workbench can be deployed in three modes:

### Standalone AIWB

Deploy only AI Workbench features without integrated resource management. This service provides:

- AIMs (AMD Inference Microservices) catalog and deployment
- AI Workloads management (Managing, Tracking & Metrics, Chatting, etc.)
- AI Workspaces (JupyterLab, VS Code, etc.)
- Model fine-tuning
- Dataset management
- Secrets management
- API keys for programmatic access

In standalone mode, the API is scoped to a single Kubernetes namespace configured via `DEFAULT_NAMESPACE` (default: `workbench`). This namespace is created and configured during Helm installation along with the required Kyverno policies and secrets. The API rejects requests targeting any other namespace because standalone mode lacks the group-based authorization that AIRM provides, and the platform has no control over permissions or resources outside the namespace it manages.

Authentication is handled via Keycloak, but namespace-level authorization relies on the single-namespace constraint rather than JWT group claims.

### Standalone AIRM

Deploy only AI Resource Manager features. See [`apps/api/airm/README.md`](../airm/README.md) for standalone AIRM deployment.

### Combined AIWB + AIRM

Deploy both services together for full integration of AI development tools with enterprise resource management. See [`apps/api/airm/README.md`](../airm/README.md) for combined deployment configuration.

## Local Development Setup

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) - For running PostgreSQL and other services
- [uv](https://docs.astral.sh/uv/) - Python package manager
- Access to a Kubernetes cluster (for full functionality)

### Quick Start

1. **Initialize the project** (first time setup):

   ```bash
   make init
   ```

   This will:
   - Install all dependencies (API packages and workloads_manager)
   - Initialize the workloads repository
   - Start Docker services

2. **Run the API**:

   ```bash
   make dev
   ```

3. **Access the API**:
   - API: http://localhost:8002
   - Swagger docs: http://localhost:8002/docs

### Available Make Targets

```bash
make init         # Initialize project (first time setup)
make dev          # Run the API server (default)
make test         # Run tests
make docker-up    # Start Docker services (PostgreSQL, etc.)
make docker-down  # Stop and remove Docker services
```

### AI Assistant Rules

This project uses a hierarchical AI rules system to provide context to AI coding assistants (Cursor, Claude, GitHub Copilot).

Rules are split across `AI_RULES.md` files at different levels:

- `/AI_RULES.md` - General (git, Jira, PRs)
- `/apps/api/AI_RULES.md` - FastAPI (async, Pydantic, testing)
- `/apps/api/aiwb/AI_RULES.md` - AIWB-specific (k8s-first, layers)

Run `make ai-rules` from the repo root to concatenate these into tool-specific files (`.cursorrules`, `CLAUDE.md`, `.github/copilot-instructions.md`). These generated files are gitignored.

### Environment Variables

Create a `.env` file (copy from `.env.example`). Key configurations include:

- **Database**: PostgreSQL connection string
- **AIWB**: Deployment mode and namespace configuration
  - `STANDALONE_MODE`: Set to `true` or `false` (default: `true`)
  - `DEFAULT_NAMESPACE`: Name of the namespace to use in standalone mode (default: `workbench`)
  - When `STANDALONE_MODE=true`: All API access is restricted to `DEFAULT_NAMESPACE`. The API returns 403 for requests targeting any other namespace. The UI hides the project selector.
  - When `STANDALONE_MODE=false`: Users can access namespaces matching their JWT group claims. Namespace lifecycle is managed by AIRM.
- **Keycloak/Auth**: OpenID Connect client credentials (required for user authentication)
- **MinIO**: Object storage endpoint and credentials (for dataset and model storage)
- **Kubernetes**: Cluster access configuration for workload deployment

See `.env.example` for complete configuration options.

### API Endpoints

The AIWB API definition can be found under the Swagger UI at http://localhost:8002/docs for interactive API documentation.

### Development Workflow

1. **Database Setup**: The PostgreSQL database is managed via Docker Compose. Migrations are applied automatically on startup.

2. **Running Tests**:

   ```bash
   make test
   ```

3. **Dependency Management**: Uses `uv` for fast Python dependency management. Run `make init` to install dependencies, or `uv sync` directly when dependencies change.
