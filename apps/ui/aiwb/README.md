<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AMD AI Workbench UI

The frontend interface for AMD AI Workbench. This UI connects to the AIWB API and provides AI development features including interactive chat, AI workspaces management, AIMs catalog browsing and deployment, and fine-tuning job configuration.

> **Note:** If you are new to the project or new hired, please read the [LOCAL_SETUP](https://github.com/silogen/dev_helpers/blob/main/LOCAL_SETUP.md) before you continue.

## Settings

### Environment variables

The app has various settings and features that can be set or toggled using environment variables:

- NEXTAUTH_SECRET: the secret used by next-auth for authentication. See the `.env.local.example` file.
- NEXTAUTH_URL: the url the app will run on. This is used by next-auth for authentication. See the `.env.local.example` file.
- KEYCLOAK_ID: ID for the keycloak client used by next-auth for authentication
- KEYCLOAK_SECRET: the secret for the keycloak authentication client used by next-auth for authentication
- KEYCLOAK_ISSUER: the URL to the Keycloak issuer (something like https://auth.dev.silogen.ai/realms/airm with the realms)
- AIRM_API_SERVICE_URL: the URL for the AIWB API backend (for local development set to `http://localhost:8002`)
- STANDALONE_MODE: when `true`, the UI operates in single-namespace mode. The project selector is hidden, namespace fetching from the API is disabled, and the UI uses `DEFAULT_NAMESPACE` as the only active project. When `false`, the UI fetches accessible namespaces from the API based on the user's JWT group claims and shows the project selector.
- DEFAULT_NAMESPACE: the namespace to use as the active project in standalone mode (default: `workbench`). Must match the namespace created during Helm installation.

> [!NOTE]
> **Runtime Environment Variables**
>
> Environment variables are dynamically passed to the frontend at runtime via the `/api/config` route. This approach enables configuration changes without requiring Docker image rebuilds, for example switching between standalone mode and resource-managed mode (`STANDALONE_MODE: false`).
>
> **Why not `NEXT_PUBLIC_*` variables?**
>
> Next.js bakes `NEXT_PUBLIC_*` variables into the bundle during the build phase, making them static and unable to change at runtime. For dynamic configuration needs, runtime-fetched environment variables are required. See [Next.js Environment Variables documentation](https://nextjs.org/docs/app/guides/environment-variables#bundling-environment-variables-for-the-browser) for more details.

## Running locally

You will need all the values specified in the [environment variables section](#environment-variables) - If you are running the AIWB API locally, you can use the pre-populated values for all environment variables.
However, if your UI is connecting to the AIWB API in a different environment (OCI for example), the following 3 variables need to correspond to the environment where the API is running (ask a colleague)

- `KEYCLOAK_SECRET`, `KEYCLOAK_ID`, and `KEYCLOAK_ISSUER` for authentication.

Here are the instructions for running locally:

- Install pnpm: https://pnpm.io/installation
- Run `pnpm install`
- Copy the `.env.local.example` to `.env.local` and configure the variables.
  - setup connection to other services, for example locally:

    - `AIRM_API_SERVICE_URL=http://localhost:8002`

  - Configure authentication:
    - Setup Keycloak authentication by configuring the environment variables `KEYCLOAK_SECRET`, `KEYCLOAK_ID`
      and `KEYCLOAK_ISSUER` if you are not running the AIWB API locally.
      The easiest way is to get these values from someone in the team.

- Run `pnpm dev`
- Access the app at http://localhost:8011

> **Note:** The default username and password is `devuser@amd.com` and `password`.

## Setup pre-commit for linting and formatting

Just be sure to be in the root of the repo and run the following command:

```bash
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
```

This will install the pre-commit hooks and will run the formatting and linting before each commit and run tests before pushing.

### How to skip the pre-commit hooks

Just add the `--no-verify` or `-n` flag to the `git commit` command.

## Running tests locally

Prior to submitting a pull request, make sure that the tests pass locally.
To run tests, run the following from the root of the UI code base

```bash
pnpm test
```

## Running E2E tests

Browser-based E2E tests live in `specs/` and use Robot Framework with Browser Library (Playwright).

```bash
cd apps/ui/aiwb/specs
uv sync --project ..
uv run --project .. rfbrowser init chromium
uv run --project .. robot --argumentfile arguments.txt --exclude gpu .
```

Requires a running AIWB deployment with a valid kubeconfig context (or set `AIWB_UI_URL` directly).

Results are written to `specs/results/`. Open `log.html` for the full execution log. Failed tests include linked screenshots named by test case, also available as files in the results directory. See `specs/CLAUDE.md` for architecture details and tag reference.

## Builds and deployment

### Build the docker image

Docker image building process is done at each push event for each branch, main included.
The docker images have the following format:

```txt
ghcr.io/silogen/core/aiwb-ui:<branch-name>-<commit-hash>
```

E.g. ghcr.io/silogen/core/aiwb-ui:main-b973967
