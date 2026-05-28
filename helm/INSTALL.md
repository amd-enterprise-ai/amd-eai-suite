<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AMD enterprise AI reference stack - Helm Installation Guide

This guide provides step-by-step instructions for deploying the AMD enterprise AI reference stack
on a Kubernetes cluster using the Helm charts in this repository.

> **Automated deployment**: For production deployments, consider using
> [Cluster Forge](https://github.com/silogen/cluster-forge), which automates the entire
> stack deployment including all dependencies via GitOps.
>
> **Official documentation**: For comprehensive platform documentation, visit
> <https://enterprise-ai.docs.amd.com>.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Deployment Modes](#deployment-modes)
- [Step 1: Install Cluster Dependencies](#step-1-install-cluster-dependencies)
  - [Tier 1 - Operators and CRDs](#tier-1---operators-and-crds)
  - [Tier 2 - Platform Services](#tier-2---platform-services)
  - [Tier 3 - AI/ML Stack (Compute Plane)](#tier-3---aiml-stack-compute-plane)
  - [Optional Dependencies](#optional-dependencies)
- [Step 2: Create Secrets](#step-2-create-secrets)
  - [Option A: External Secrets Operator](#option-a-external-secrets-operator)
  - [Option B: Manual Secret Creation](#option-b-manual-secret-creation)
- [Step 3: Install Infrastructure Charts](#step-3-install-infrastructure-charts)
- [Step 4: Install Application Charts](#step-4-install-application-charts)
- [Step 5: Onboard a Cluster](#step-5-onboard-a-cluster)
- [Verification](#verification)
- [Validation with E2E Tests](#validation-with-e2e-tests)

---

## Overview

The AMD enterprise AI reference stack consists of two main applications:

- **AI Resource Manager (AIRM)** -- Multi-tenant resource management, authentication,
  cluster coordination, and resource allocation.
- **AI Workbench (AIWB)** -- AI development tools including model deployment (AIMs),
  workspaces, fine-tuning, and dataset management.

The Helm charts are organized as follows:

```
helm/
├── airm/                          # AIRM umbrella chart (API + UI + Agent)
│   └── charts/
│       ├── airm-api/              # AIRM API and UI
│       └── airm-agent/            # AIRM cluster agent
├── aiwb/                          # AIWB API and UI
├── infrastructure/
│   ├── airm-cnpg/                 # PostgreSQL cluster for AIRM
│   ├── aiwb-cnpg/                 # PostgreSQL cluster for AIWB
│   ├── airm-rabbitmq/             # RabbitMQ cluster for AIRM
│   ├── airm-external-secrets/     # ExternalSecret resources for AIRM
│   └── aiwb-external-secrets/     # ExternalSecret resources for AIWB
└── eai-e2e/                       # E2E test support (optional)
```

## Prerequisites

- **Kubernetes** 1.28+ cluster with AMD GPUs
- **Helm** 3.x
- **kubectl** configured for your cluster
- A **domain name** for ingress routing (referred to as `<YOUR-DOMAIN>` throughout this guide)
- A **secrets backend** (e.g., HashiCorp Vault, OpenBao) or the ability to create
  Kubernetes Secrets manually
- A **StorageClass** available in your cluster. The infrastructure charts default to a
  StorageClass named `default`. If your cluster uses a different name (e.g., `standard`
  on kind clusters), override it during installation with
  `--set storage.storageClass=<YOUR-STORAGE-CLASS>`.

## Deployment Modes

The platform supports three deployment modes:

| Mode                       | Description                                               | Charts to Install                                         |
| -------------------------- | --------------------------------------------------------- | --------------------------------------------------------- |
| **Combined (AIRM + AIWB)** | Full platform with resource management and AI workbench   | `airm` + `aiwb` + all infrastructure                      |
| **Standalone AIRM**        | Resource management only                                  | `airm` + AIRM infrastructure                              |
| **Standalone AIWB**        | Single-namespace AI workbench without resource management | `aiwb` + AIWB infrastructure (set `standAloneMode: true`) |

---

## Step 1: Install Cluster Dependencies

The following components must be installed on the cluster before deploying the
application charts. They are organized into tiers based on install order.

### Tier 1 - Operators and CRDs

These operators and CRD providers must be installed first, as other components depend on them.

| Component                          | Purpose                                                                                                                                                                                                                          | Installation                                                                                                                                                                                                                    |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **cert-manager**                   | TLS certificate management. Used by RabbitMQ for TLS and by the AIRM agent for webhook certificates.                                                                                                                             | [cert-manager docs](https://cert-manager.io/docs/installation/helm/)                                                                                                                                                            |
| **CloudNative-PG (CNPG) Operator** | Manages PostgreSQL database clusters. AIRM and AIWB each require a PostgreSQL instance.                                                                                                                                          | [CNPG docs](https://cloudnative-pg.io/documentation/current/installation_upgrade/)                                                                                                                                              |
| **RabbitMQ Cluster Operator**      | Manages RabbitMQ clusters. Used for messaging between the AIRM API and the cluster Agent.                                                                                                                                        | [RabbitMQ Operator docs](https://www.rabbitmq.com/kubernetes/operator/install-operator). Recommended: install via `kubectl apply -f https://github.com/rabbitmq/cluster-operator/releases/latest/download/cluster-operator.yml` |
| **External Secrets Operator**      | Synchronizes secrets from an external backend (Vault, OpenBao, etc.) into Kubernetes Secrets. Used by all infrastructure charts. Can be skipped if creating secrets manually (see [Option B](#option-b-manual-secret-creation)). | [ESO docs](https://external-secrets.io/latest/introduction/getting-started/)                                                                                                                                                    |
| **Gateway API CRDs + KGateway**    | Kubernetes-native HTTP routing. All services (AIRM API/UI, AIWB API/UI, Keycloak) are exposed via HTTPRoute resources through a Gateway.                                                                                         | [Gateway API docs](https://gateway-api.sigs.k8s.io/guides/#installing-gateway-api), [KGateway docs](https://kgateway.dev/docs/)                                                                                                 |
| **OpenTelemetry Operator**         | Manages OpenTelemetry collectors. AIWB deploys a DaemonSet-based collector on GPU nodes for vLLM inference metrics.                                                                                                              | [OTel Operator docs](https://opentelemetry.io/docs/platforms/kubernetes/operator/)                                                                                                                                              |

### Tier 2 - Platform Services

These services should be deployed after the operators are running.

| Component                      | Purpose                                                                                                                                                                             | Installation                                                                                                                                                                                                      |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Keycloak**                   | Identity and access management. Provides authentication and authorization for both AIRM and AIWB. Requires an `airm` realm to be configured with the appropriate clients and users. | [Keycloak Operator docs](https://www.keycloak.org/operator/installation)                                                                                                                                          |
| **MinIO Operator + Tenant**    | S3-compatible object storage. Used by AIWB for dataset and model storage. Not required for standalone AIRM deployments.                                                             | [MinIO Operator docs](https://min.io/docs/minio/kubernetes/upstream/operations/install-deploy-manage/deploy-operator-helm.html)                                                                                   |
| **Observability Stack (LGTM)** | Prometheus, Loki, Grafana, Tempo, Mimir. Provides metrics, logs, and traces. Both AIRM and AIWB query Prometheus for GPU and workload metrics.                                      | [Grafana LGTM docs](https://grafana.com/docs/grafana/latest/)                                                                                                                                                     |
| **cluster-auth**               | Kubernetes RBAC integration service. Used by AIWB for API key management and inference endpoint authentication. Not required for standalone AIRM deployments.                       | Deploy via [Cluster Forge](https://github.com/silogen/cluster-forge), or provide an existing endpoint and configure AIWB with `clusterAuth.url` plus a `cluster-auth-admin-token` Secret in the `aiwb` namespace. |

### Tier 3 - AI/ML Stack (Compute Plane)

These components enable GPU workloads and AI model serving on compute clusters.

| Component                       | Purpose                                                                                                                                                                                                                                                                 | Installation                                                                                              |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **AMD GPU Operator**            | GPU device plugin, drivers, and node feature discovery for AMD GPUs.                                                                                                                                                                                                    | [AMD GPU Operator docs](https://github.com/ROCm/gpu-operator)                                             |
| **AMD Device Metrics Exporter** | Exports per-GPU metrics (utilization, VRAM, temperature, power, PCIe). AIRM relies on these metrics for all GPU dashboards and workload monitoring. Must be deployed on every GPU node. See the [configuration note](#amd-device-metrics-exporter-configuration) below. | [Device Metrics Exporter docs](https://instinct.docs.amd.com/projects/device-metrics-exporter/en/latest/) |
| **Kaiwo**                       | AI workload orchestration. Manages job scheduling, queue configuration, and GPU resource allocation. Includes its own dependencies: **Kueue** (job queueing) and **KubeRay** (distributed computing).                                                                   | [Kaiwo docs](https://github.com/silogen/kaiwo)                                                            |
| **AIM Engine**                  | Operator for `AIMService` CRDs. Handles AI model deployment, discovery (`AIMClusterModel`), and inference routing. Includes **KServe** as a transitive dependency for `InferenceService` management.                                                                    | [AIM Engine docs](https://github.com/amd-enterprise-ai/aim-engine)                                        |

#### AMD Device Metrics Exporter Configuration

The AMD Device Metrics Exporter requires a ConfigMap named `gpu-config` in the
`kube-amd-gpu` namespace. This ConfigMap controls which GPU fields are collected and,
critically, includes the custom labels that AIRM needs to associate metrics with clusters,
projects, and workloads.

A reference configuration is available at
[cluster-forge/sources/amd-gpu-operator-config](https://github.com/silogen/cluster-forge/blob/main/sources/amd-gpu-operator-config/ConfigMap_amd-gpu-metrics-exporter-config.yaml).

Apply it to your cluster (replace `<YOUR-CLUSTER-NAME>` with the name you will register
in AIRM):

```bash
kubectl create namespace kube-amd-gpu 2>/dev/null || true

kubectl apply -f - <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-config
  namespace: kube-amd-gpu
data:
  config.json: |
    {
      "GPUConfig": {
        "Fields": [
          "GPU_NODES_TOTAL",
          "GPU_PACKAGE_POWER",
          "GPU_AVERAGE_PACKAGE_POWER",
          "GPU_EDGE_TEMPERATURE",
          "GPU_JUNCTION_TEMPERATURE",
          "GPU_MEMORY_TEMPERATURE",
          "GPU_HBM_TEMPERATURE",
          "GPU_GFX_ACTIVITY",
          "GPU_UMC_ACTIVITY",
          "GPU_MMA_ACTIVITY",
          "GPU_VCN_ACTIVITY",
          "GPU_JPEG_ACTIVITY",
          "GPU_VOLTAGE",
          "GPU_GFX_VOLTAGE",
          "GPU_MEMORY_VOLTAGE",
          "PCIE_SPEED",
          "PCIE_MAX_SPEED",
          "PCIE_BANDWIDTH",
          "GPU_ENERGY_CONSUMED",
          "PCIE_REPLAY_COUNT",
          "PCIE_RECOVERY_COUNT",
          "PCIE_REPLAY_ROLLOVER_COUNT",
          "PCIE_NACK_SENT_COUNT",
          "PCIE_NAC_RECEIVED_COUNT",
          "GPU_CLOCK",
          "GPU_POWER_USAGE",
          "GPU_TOTAL_VRAM",
          "GPU_USED_VRAM",
          "GPU_FREE_VRAM",
          "GPU_TOTAL_VISIBLE_VRAM",
          "GPU_USED_VISIBLE_VRAM",
          "GPU_FREE_VISIBLE_VRAM",
          "GPU_TOTAL_GTT",
          "GPU_USED_GTT",
          "GPU_FREE_GTT",
          "GPU_ECC_CORRECT_TOTAL",
          "GPU_ECC_UNCORRECT_TOTAL"
        ],
        "Labels": [
          "GPU_UUID",
          "SERIAL_NUMBER",
          "GPU_ID",
          "POD",
          "NAMESPACE",
          "CONTAINER",
          "CLUSTER_NAME",
          "CARD_SERIES",
          "CARD_MODEL",
          "CARD_VENDOR",
          "DRIVER_VERSION",
          "VBIOS_VERSION",
          "HOSTNAME"
        ],
        "ExtraPodLabels": {
          "WORKLOAD_ID": "airm.silogen.ai/workload-id",
          "PROJECT_ID": "airm.silogen.ai/project-id"
        },
        "CustomLabels": {
          "KUBE_CLUSTER_NAME": "<YOUR-CLUSTER-NAME>"
        }
      }
    }
EOF
```

**Key fields explained:**

| Field                            | Purpose                                                                                                                                                                                                                                                                                               |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ExtraPodLabels.WORKLOAD_ID`     | Maps the `airm.silogen.ai/workload-id` pod label into GPU metrics so AIRM can attribute utilization to individual workloads.                                                                                                                                                                          |
| `ExtraPodLabels.PROJECT_ID`      | Maps the `airm.silogen.ai/project-id` pod label so metrics roll up to projects.                                                                                                                                                                                                                       |
| `CustomLabels.KUBE_CLUSTER_NAME` | **Must match the cluster name registered in AIRM** (e.g., `demo-cluster`). This is the primary identifier AIRM uses to correlate GPU metrics with the correct cluster. If the exporter is not deployed or this label is absent, the AIRM Agent falls back to its `CLUSTER_NAME` environment variable. |

> **Important**: The cluster name must be consistent across three places:
>
> 1. The `KUBE_CLUSTER_NAME` value in this ConfigMap
> 2. The cluster name registered in AIRM during [Step 5](#step-5-onboard-a-cluster)
> 3. The Agent deployment's `KUBE_CLUSTER_NAME` environment variable (currently defaults
>    to `demo-cluster` in
>    [airm-agent/templates/agent/deployment.yaml](airm/charts/airm-agent/templates/agent/deployment.yaml)).
>    See the [Agent README](airm/charts/airm-agent/README.md) for configuration details.
>
> If these drift out of sync, GPU metrics will not appear in the AIRM dashboards.

### Optional Dependencies

| Component   | When Needed                                                                                                                                                                                                                             | Installation                                                  |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **Kyverno** | Only when deploying AIWB in standalone mode (`standAloneMode: true`). Provides a `ClusterPolicy` that auto-labels workloads with `workload-id`. Not needed for the default combined AIRM + AIWB deployment where AIRM handles labeling. | [Kyverno docs](https://kyverno.io/docs/installation/methods/) |

---

## Step 2: Create Secrets

The application charts expect certain Kubernetes Secrets to exist before installation.
There are two approaches to providing these secrets.

### Option A: External Secrets Operator

If you have External Secrets Operator installed with a configured `ClusterSecretStore`,
use the infrastructure ExternalSecret charts to sync secrets from your backend.

The charts expect a `ClusterSecretStore` named `openbao-secret-store` by default
(configurable via the `externalSecretStore` value in each chart).

Your secret backend must contain the following keys. Each key must be stored as an
object with a `value` field (e.g., `{"value": "postgres"}`), not as a raw string,
because the ExternalSecret templates read `property: value` from each entry.

**AIRM Secrets** (synced by `infrastructure/airm-external-secrets`):

| Secret Name                  | Backend Keys                                                         | Purpose                           |
| ---------------------------- | -------------------------------------------------------------------- | --------------------------------- |
| `airm-cnpg-superuser`        | `airm-cnpg-superuser-username`, `airm-cnpg-superuser-password`       | PostgreSQL superuser credentials  |
| `airm-cnpg-user`             | `airm-cnpg-user-username`, `airm-cnpg-user-password`                 | PostgreSQL application user       |
| `airm-keycloak-admin-client` | `airm-keycloak-admin-client-id`, `airm-keycloak-admin-client-secret` | Keycloak admin client credentials |
| `airm-keycloak-ui-creds`     | `airm-ui-keycloak-secret`                                            | Keycloak UI client secret         |
| `airm-user-credentials`      | `keycloak-initial-devuser-password`                                  | Initial dev user password         |
| `airm-rabbitmq-admin`        | `airm-rabbitmq-user-username`, `airm-rabbitmq-user-password`         | RabbitMQ admin credentials        |
| `airm-secrets-airm`          | `airm-ui-auth-nextauth-secret`                                       | AIRM UI NextAuth secret           |

**AIWB Secrets** (synced by `infrastructure/aiwb-external-secrets`):

| Secret Name                | Backend Keys                                                   | Purpose                          |
| -------------------------- | -------------------------------------------------------------- | -------------------------------- |
| `aiwb-cnpg-superuser`      | `aiwb-cnpg-superuser-username`, `aiwb-cnpg-superuser-password` | PostgreSQL superuser credentials |
| `aiwb-cnpg-user`           | `aiwb-cnpg-user-password` (username set from chart values)     | PostgreSQL application user      |
| `aiwb-ui-keycloak-secret`  | `airm-ui-keycloak-secret`                                      | Keycloak UI client secret        |
| `aiwb-nextauth-secret`     | `aiwb-ui-auth-nextauth-secret`                                 | AIWB UI NextAuth secret          |
| `minio-credentials`        | `minio-api-access-key`, `minio-api-secret-key`                 | MinIO access credentials         |
| `cluster-auth-admin-token` | `cluster-auth-admin-token`                                     | cluster-auth service token       |

### Option B: Manual Secret Creation

If you are not using External Secrets Operator, create the Kubernetes Secrets manually.
Skip the `infrastructure/*-external-secrets` chart installations and create the secrets
directly in the appropriate namespaces.

Create the namespaces first:

```bash
kubectl create namespace airm
kubectl create namespace aiwb
```

**AIRM Secrets** (namespace: `airm`):

| Secret Name                  | Required Data Keys                          |
| ---------------------------- | ------------------------------------------- |
| `airm-cnpg-superuser`        | `username`, `password`                      |
| `airm-cnpg-user`             | `username`, `password`                      |
| `airm-keycloak-admin-client` | `client-id`, `client-secret`                |
| `airm-keycloak-ui-creds`     | `KEYCLOAK_SECRET`                           |
| `airm-user-credentials`      | `USER_PASSWORD`                             |
| `airm-rabbitmq-admin`        | `username`, `password`, `default_user.conf` |
| `airm-secrets-airm`          | `NEXTAUTH_SECRET`                           |

**AIWB Secrets** (namespace: `aiwb`):

| Secret Name                | Required Data Keys                     |
| -------------------------- | -------------------------------------- |
| `aiwb-cnpg-superuser`      | `username`, `password`                 |
| `aiwb-cnpg-user`           | `username`, `password`                 |
| `aiwb-ui-keycloak-secret`  | `value`                                |
| `aiwb-nextauth-secret`     | `NEXTAUTH_SECRET`                      |
| `minio-credentials`        | `minio-access-key`, `minio-secret-key` |
| `cluster-auth-admin-token` | `value`                                |

Example commands:

```bash
# PostgreSQL credentials
kubectl create secret generic airm-cnpg-user -n airm \
  --from-literal=username=airm_user \
  --from-literal=password='<your-secure-password>'

kubectl create secret generic airm-cnpg-superuser -n airm \
  --from-literal=username=postgres \
  --from-literal=password='<your-secure-password>'

# Keycloak admin client
kubectl create secret generic airm-keycloak-admin-client -n airm \
  --from-literal=client-id='<keycloak-admin-client-id>' \
  --from-literal=client-secret='<keycloak-admin-client-secret>'

# Keycloak UI client secret
kubectl create secret generic airm-keycloak-ui-creds -n airm \
  --from-literal=KEYCLOAK_SECRET='<keycloak-ui-client-secret>'

# Initial dev user password (used by configure.sh)
kubectl create secret generic airm-user-credentials -n airm \
  --from-literal=USER_PASSWORD='<dev-user-password>'

# RabbitMQ admin -- password and default_user.conf must match
RABBITMQ_ADMIN_PASSWORD='<your-secure-password>'
kubectl create secret generic airm-rabbitmq-admin -n airm \
  --from-literal=username=admin \
  --from-literal=password="${RABBITMQ_ADMIN_PASSWORD}" \
  --from-literal=default_user.conf="$(printf 'default_user = admin\ndefault_pass = %s' "${RABBITMQ_ADMIN_PASSWORD}")"

# AIRM UI NextAuth secret
kubectl create secret generic airm-secrets-airm -n airm \
  --from-literal=NEXTAUTH_SECRET='<random-string>'

# AIWB PostgreSQL credentials
kubectl create secret generic aiwb-cnpg-user -n aiwb \
  --from-literal=username=aiwb_user \
  --from-literal=password='<your-secure-password>'

kubectl create secret generic aiwb-cnpg-superuser -n aiwb \
  --from-literal=username=postgres \
  --from-literal=password='<your-secure-password>'

# AIWB Keycloak client secret (key name is "value")
kubectl create secret generic aiwb-ui-keycloak-secret -n aiwb \
  --from-literal=value='<keycloak-ui-client-secret>'

# AIWB NextAuth secret
kubectl create secret generic aiwb-nextauth-secret -n aiwb \
  --from-literal=NEXTAUTH_SECRET='<random-string>'

# MinIO credentials
kubectl create secret generic minio-credentials -n aiwb \
  --from-literal=minio-access-key='<minio-access-key>' \
  --from-literal=minio-secret-key='<minio-secret-key>'

# cluster-auth admin token (key name is "value")
kubectl create secret generic cluster-auth-admin-token -n aiwb \
  --from-literal=value='<cluster-auth-token>'
```

---

## Step 3: Install Infrastructure Charts

Install the infrastructure charts in the following order from the `helm/` directory.
These create the PostgreSQL databases and RabbitMQ cluster that the application charts
depend on.

**1. ExternalSecret resources** (skip if using [Option B](#option-b-manual-secret-creation)):

```bash
# AIRM secrets
helm install airm-infra-external-secrets ./infrastructure/airm-external-secrets \
  -n airm --create-namespace

# AIWB secrets
helm install aiwb-infra-external-secrets ./infrastructure/aiwb-external-secrets \
  -n aiwb --create-namespace
```

Wait for the ExternalSecret resources to sync and the corresponding Kubernetes Secrets to
be created before proceeding:

```bash
kubectl get externalsecrets -n airm
kubectl get externalsecrets -n aiwb
```

All ExternalSecrets should show `SecretSynced` status.

**2. PostgreSQL clusters** (requires CNPG operator and database secrets to exist):

```bash
# AIRM database
helm install airm-infra-cnpg ./infrastructure/airm-cnpg \
  -n airm --create-namespace

# AIWB database
helm install aiwb-infra-cnpg ./infrastructure/aiwb-cnpg \
  -n aiwb --create-namespace
```

If your cluster's StorageClass is not named `default`, override it:

```bash
helm install airm-infra-cnpg ./infrastructure/airm-cnpg \
  -n airm \
  --set storage.storageClass=<YOUR-STORAGE-CLASS> \
  --set walStorage.storageClass=<YOUR-STORAGE-CLASS>
```

**3. RabbitMQ cluster** (requires cert-manager, RabbitMQ operator, and admin secret):

```bash
helm install airm-infra-rabbitmq ./infrastructure/airm-rabbitmq \
  -n airm --create-namespace
```

To override the StorageClass for RabbitMQ:

```bash
helm install airm-infra-rabbitmq ./infrastructure/airm-rabbitmq \
  -n airm \
  --set persistence.storageClassName=<YOUR-STORAGE-CLASS>
```

Wait for all infrastructure components to become ready before proceeding:

```bash
# PostgreSQL clusters should be "Cluster in healthy state"
kubectl get clusters.postgresql.cnpg.io -n airm
kubectl get clusters.postgresql.cnpg.io -n aiwb

# RabbitMQ cluster should be running
kubectl get rabbitmqclusters -n airm
```

---

## Step 4: Install Application Charts

### AIRM (AI Resource Manager)

The AIRM umbrella chart deploys the API, UI, and Agent. See the individual chart READMEs
for detailed configuration options:

- [airm/README.md](airm/README.md) -- Umbrella chart overview
- [airm/charts/airm-api/README.md](airm/charts/airm-api/README.md) -- API and UI configuration
- [airm/charts/airm-agent/README.md](airm/charts/airm-agent/README.md) -- Agent configuration

```bash
helm install airm ./airm \
  -n airm --create-namespace \
  --set airm-api.airm.appDomain=<YOUR-DOMAIN>
```

> **Gateway configuration**: The charts create HTTPRoute resources that attach to a
> Gateway named `https` in the `kgateway-system` namespace by default. If your Gateway
> uses a different name or namespace, override with
> `--set airm-api.kgateway.namespace=<NS> --set airm-api.kgateway.gatewayName=<NAME>`
> (for AIRM) and `--set kgateway.namespace=<NS> --set kgateway.gatewayName=<NAME>`
> (for AIWB).

### AIWB (AI Workbench)

> **Note**: The AIWB chart creates an `AIMClusterRuntimeConfig` resource, which requires
> AIM Engine CRDs to be installed on the cluster first (see
> [Tier 3 dependencies](#tier-3---aiml-stack-compute-plane)).

**Combined deployment** (default, with AIRM managing namespaces and authorization):

```bash
helm install aiwb ./aiwb \
  -n aiwb --create-namespace \
  --set appDomain=<YOUR-DOMAIN>
```

**Standalone deployment** (single namespace, without AIRM -- requires Kyverno):

```bash
helm install aiwb ./aiwb \
  -n aiwb --create-namespace \
  --set appDomain=<YOUR-DOMAIN> \
  --set standAloneMode=true
```

### Upgrading

To upgrade an existing installation after changing values or chart versions:

```bash
helm upgrade airm ./airm \
  -n airm \
  --set airm-api.airm.appDomain=<YOUR-DOMAIN>

helm upgrade aiwb ./aiwb \
  -n aiwb \
  --set appDomain=<YOUR-DOMAIN>
```

---

## Step 5: Onboard a Cluster

After the AIRM API is running, you must register (onboard) the Kubernetes cluster so the
AIRM Agent can communicate with the API.

The AIRM chart includes a
[configure.sh](airm/charts/airm-api/files/configure.sh) script that automates this
process: it registers the cluster, creates the Agent's RabbitMQ credentials, sets up a
default project, and adds a dev user.

When `airm-api.airm.includeDemoSetup` is `true` (the default), the Helm chart creates a
Kubernetes Job that waits for the AIRM API to become healthy and then runs the script
automatically. Monitor it with:

```bash
kubectl get jobs -n airm
kubectl logs job/airm-configure -n airm -f
```

Once the Job completes successfully, proceed to [Verification](#verification).

If you set `airm-api.airm.includeDemoSetup: false`, you can run the script manually or use the
AIRM API directly. See the script source and
[airm/charts/airm-agent/README.md](airm/charts/airm-agent/README.md) for details on the
onboarding flow and Agent configuration.

---

## Verification

After installation, verify that the core components are running:

```bash
# Check AIRM pods are running
kubectl get pods -n airm

# Check AIWB pods are running
kubectl get pods -n aiwb

# Verify PostgreSQL clusters are healthy
kubectl get clusters.postgresql.cnpg.io -n airm
kubectl get clusters.postgresql.cnpg.io -n aiwb

# Verify RabbitMQ is running
kubectl get rabbitmqclusters -n airm

# Verify HTTPRoutes are configured
kubectl get httproutes -n airm
kubectl get httproutes -n aiwb
```

Once all pods are running, the services should be accessible at:

- **AIRM UI**: `https://airmui.<YOUR-DOMAIN>`
- **AIRM API**: `https://airmapi.<YOUR-DOMAIN>`
- **AIWB UI**: `https://aiwbui.<YOUR-DOMAIN>`
- **AIWB API**: `https://aiwbapi.<YOUR-DOMAIN>`
- **Keycloak**: `https://kc.<YOUR-DOMAIN>`

---

## Validation with E2E Tests

The repository includes Robot Framework end-to-end test suites that validate a live
deployment. These cover AIRM API, AIWB API, and AIWB UI functionality. Running them
against your cluster is the recommended way to confirm the platform is working correctly
after installation.

Each test suite has its own README with prerequisites (kubeconfig OIDC setup, tooling),
commands, tag reference, and troubleshooting:

| Suite        | README                                                            |
| ------------ | ----------------------------------------------------------------- |
| **AIRM API** | [apps/api/airm/specs/README.md](../apps/api/airm/specs/README.md) |
| **AIWB API** | [apps/api/aiwb/specs/README.md](../apps/api/aiwb/specs/README.md) |
| **AIWB UI**  | [apps/ui/aiwb/specs/CLAUDE.md](../apps/ui/aiwb/specs/CLAUDE.md)   |

For shared testing infrastructure, concurrent execution, authentication details, and
CI/CD pipeline integration, see [testing/README.md](../testing/README.md).
