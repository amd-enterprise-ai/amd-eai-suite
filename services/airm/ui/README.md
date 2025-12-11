<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AMD Resource Manager and AI Workbench UI

The frontend interface for both AI Resource Manager and AI Workbench. It provides resource management features (cluster onboarding, quota allocation, job monitoring) as well as AI Workbench features including interactive chat, AI workspaces management, AIMs catalog browsing and deployment, and fine-tuning job configuration.

## Settings

### Environment variables

The app has various settings and features that can be set or toggled using environment variables:

- NEXTAUTH_SECRET: the secret used by next-auth for authentication. See the `.env.local.example` file.
- NEXTAUTH_URL: the url the app will run on. This is used by next-auth for authentication. See the `.env.local.example` file.
- KEYCLOAK_ID: ID for the keycloak client used by next-auth for authentication
- KEYCLOAK_SECRET: the secret for the keycloak authentication client used by next-auth for authentication
- KEYCLOAK_ISSUER: the URL to the Keycloak issuer (something like https://auth.dev.silogen.ai/realms/airm with the realms)
- AIRM_API_SERVICE_URL: the URL for the AIRM SERVICE API (`https://airm-api.dev.silogen.ai` for current dev environment) for local development set to `http://localhost:8001`

## Running locally

You will need all the values specified in the [environment variables section](#environment-variables) - If you are running the AIRM API locally, you can use the pre-populated values for all environment variables.
However, if your UI is connecting to the AIRM API in a different environment (OCI for example), the following 3 variables need to correspond to the environment where the API is running (ask a colleague)

- `KEYCLOAK_SECRET`, `KEYCLOAK_ID`, and `KEYCLOAK_ISSUER` for authentication.

Here are the instructions for running locally:

- Install pnpm: https://pnpm.io/installation
- Run `pnpm install`
- Copy the `.env.local.example` to `.env.local` and configure the variables.

  - setup connection to other services, for example locally:

    - `AIRM_API_SERVICE_URL=http://localhost:8001`

  - Configure authentication:
    - Setup Keycloak authentication by configuring the environment variables `KEYCLOAK_SECRET`, `KEYCLOAK_ID`
      and `KEYCLOAK_ISSUER` if you are not running the AIRM API locally.
      The easiest way is to get these values from someone in the team.

- Run `pnpm dev`
- Access the app at http://localhost:8010

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

## Builds and deployment

### Build the docker image

Docker image building process is done at each push event for each branch, main included.
The docker images have the following format:

```txt
amdenterpriseai/airm-ui:<branch-name>-<commit-hash>
```

E.g. amdenterpriseai/airm-ui:main-b973967
