<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AMD Resource Manager and AI Workbench API

The centralized API component handles both AI Resource Manager and AI Workbench functionality. It is responsible for managing access control, clusters, and provides AI Workbench features including AIMs (AMD Inference Microservices) deployment, model fine-tuning, dataset management, AI workspaces, and API keys for programmatic access.

## Installation

### Development environment

Dependencies are handled with `uv` which must be installed first. `uv` will create virtual environment and in order to utilize the environment, commands should be with `uv run`. There is _no_ need to manually install packages or activate environments.

More details about `uv` can be read from our [dependency management guidelines](../../../docs/guidelines/dependency-management.md).

### Running AIRM API locally

Note: If you are on a mac and see this error: Error: pg_config executable not found.
Please install the postgresql package using brew:

```bash
brew install postgresql
```

### Steps to run

If you want to test everything locally, you need to use `.env` and run `docker compose up -d`. This will spin up everything except the AIRM service, which you need to run with `uv run -m app`.

Set up environment variables by first copying the .env.local file and making edits to secrets and other parameters:

```bash
cp .env.local .env
```

Start Docker services:

```bash
docker compose up -d
```

Start AIRM API service:

```bash
uv run -m app
```

As part of the docker-compose, there will be some seed data installed into the database so you don't need to manually create any organization. The created organization will match the AMD organization on keycloak, to which you should have been added as a member.

The next steps involve starting up the UI and onboarding a cluster to the AMD Resource Manager application.
Once you have setup the UI, you can follow the standard user guide and dispatcher application's README for next steps.

### Application credentials

As part of the application startup, the following user is created in both keycloak and the database: `devuser@amd.com` with password `password`.

If you want to create new users, you can do so by logging into the keycloak admin portal at `http://localhost:8080/admin/master/console/` with credentials from the docker compose file and add users and add them to the AMD organization.
Alternatively, if you want to use the user invitation functionality from the AIRM application, login to the admin portal and setup SMTP credentials for the AIRM realm.

### Accessing Swagger UI

Once the app is running, you can access the Swagger UI at http://localhost:8001/docs.
To authenticate, the Authentication scheme to use is `OpenIdAuthorization (OAuth2, implicit)` and the client id for the dev keycloak instance is "354a0fa1-35ac-4a6d-9c4d-d661129c2cd0" (should be pre-populated).
This scheme does not need a client secret and you should be able to authenticate by clicking the "Authorize" button.

### Other Docker Compose profiles

- `log` - starts a log generator that will create mock logs for testing purposes
  - run `docker compose --profile log up -d` to start the stack with the log generator
- `export` - starts a service that can be used to export the keycloak realm for AIRM
  - run `docker compose --profile export run --rm keycloak-export` to export the realm to `./airm-realm.json`. Please note that the keycloak container should NOT be running when you run this command.
- `workbench` - starts the containers that are needed to register AIMs and charts into the database
  - run `docker compose --profile workbench up -d` to start the stack with aims-registration and charts-registration services

### MCP (Model Context Protocol) Integration

The AIRM API includes built-in support for the Model Context Protocol (MCP), allowing Large Language Models to interact with API endpoints as tools. MCP endpoints are available at:

- `GET /mcp` - Server information and capabilities
- `POST /mcp/messages/` - Message handling for tool execution

For detailed configuration examples and usage instructions, see the [MCP Integration Documentation](../../../docs/internal-docs/tutorials/mcp-integration.md).

### RabbitMQ Management UI

RabbitMQ Management UI should be accessible here: http://localhost:15672.
Use the values of RABBITMQ_ADMIN_USER and RABBITMQ_ADMIN_PASS variables from docker-compose.yml to log in.

### Vault

HashiCorp Vault is used for secret management. The Vault service is running in Docker and is accessible at http://localhost:8200.

### Liquibase

As part of running docker-compose, liquibase should also automatically run, and will mount changes from the `migrations` directory into the database. If you need to run liquibase manually, you can do so with the following command (really shouldn't be needed):

```bash
docker run --rm -v "`pwd`/migrations:/liquibase/changelog" docker.io/liquibase/liquibase:latest --url="jdbc:postgresql://host.docker.internal:5432/airm" --username="postgres" --password="postgres" --changeLogFile=changelog/changelog.xml --logLevel=info update
```

## Testing

### Unit Tests (pytest)

Ensure docker is running on your machine and run the tests.

```bash
# Run all tests in parallel (recommended default)
uv run pytest -n auto

# Run all tests without parallelization (for debugging)
uv run pytest -n 0

# Run tests for a specific module (single process for focused testing)
uv run pytest tests/users/

# Run with coverage in parallel
uv run pytest --cov=app -n auto
```

### End-to-End Tests (Robot Framework)

Tests run locally on your machine but connect to the Kubernetes cluster currently active on your context. Requires manual token setup to authenticate to the application. Note that some tests might require permissions that your personal account doesn't have.

**Getting Tokens for Local Testing:**

You need to authenticate with the appropriate Keycloak realm of the application. Use the service's Swagger UI for the easiest token retrieval:

```bash
# 1. Set up port forward for getting the token
kubectl port-forward svc/airm-api -n airm 8003:80

# 2. Get token via Swagger UI
# - Open http://localhost:8003/docs in browser
# - Click "Authorize" and complete the implicit OAuth flow
# - Run a query with the UI and extract the token from the CURL request
export KEYCLOAK_TOKEN=<your-token>
```

Once you have the token, you can run E2E tests with robot.
Port-forwarding is no longer needed, as the tests automatically establish the necessary connections.

```bash
# Run all Robot Framework specs
uv run robot ../specs

# Run a specific test file
uv run robot ../specs/health.robot

# Run with output directory and detailed logging
uv run robot --outputdir results --loglevel DEBUG ../specs

# Run specific test tags
uv run robot --include smoke ../specs
```

### Parallel Testing

The test suite uses pytest-xdist for parallel execution with automatic cleanup:

- **Default**: Use `-n auto` for optimal performance (~1-2 minutes)
- **Single process**: Use for debugging specific modules or tests
- **Database isolation**: Each worker gets its own PostgreSQL database instance
- **Automated cleanup**: Orphaned Docker containers are automatically cleaned up

**When to use different approaches:**

- **`-n auto`**: Default for full test suite runs (fastest)
- **Single process**: When debugging specific modules or tests
- **Manual worker count** (`-n 2`): For CI environments or when auto detection isn't optimal

## Builds and deployment

### Docker image build

Docker image building process is done at each push event for each branch, main included.
The docker images have the following format:

```txt
amdenterpriseai/airm-api:<branch-name>-<commit-hash>
```

E.g. amdenterpriseai/airm-api:main-b973967
