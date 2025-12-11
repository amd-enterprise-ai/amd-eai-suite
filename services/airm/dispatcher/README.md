<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AMD Resource Manager Dispatcher

The de-centralized dispatcher component of the AMD Resource Manager which is responsible for dispatching commands on the compute clusters

## Installation & Setup

The AIRM is intended to run within a Kubernetes cluster so the correct heartbeats and other cron jobs are triggered.
However, it is possible to run the dispatcher locally for development purposes, while pointing to a kubernetes cluster (configured by your current kube-context) to which commands are dispatched. This is highly discouraged.

You need to have setup the AIRM API at minimum and optionally the UI. Follow the user guide to onboard a cluster and copy the values of the Auth ID and Connection Token that are provided as part of the cluster onboarding

### Development environment

Dependencies are handled with `uv` which must be installed first. `uv` will create virtual environment and in order to utilize the environment, commands should be with `uv run`. There is _no_ need to manually install packages or activate environments.

### Running dispatcher locally

#### Pre-requisites

- Make sure the AMD Resource Manager API and corresponding docker compose are running
- Onboard a cluster via AMD Resource Manager and copy the values of the Auth ID and Connection Token that are provided as part of the cluster onboarding.
- Set up environment variables by first copying the `.env.example` file and replace the RABBITMQ_USER and RABBITMQ_PASSWORD in the `.env` file of the dispatcher directory with the values for Auth ID and Connection Token respectively.

```bash
cp .env.example .env
```

#### Running dispatcher on a local kubernetes cluster

Running the dispatcher on a local kubernetes cluster is the recommended way to run the dispatcher for development purposes.

##### Setting up a local kubernetes cluster

- Make sure you have kind installed on your machine (https://kind.sigs.k8s.io/docs/user/quick-start/)
- Clone kaiwo (https://github.com/silogen/kaiwo) repository so it coexists with amd-eai-suite:

```bash
└── projects
    ├── amd-eai-suite/
    ├── kaiwo/

```

Create a cluster with the following command from the root of the `amd-eai-suite/` repository:

```bash
kind create cluster --config ./services/airm/dispatcher/local/kind-config.yaml
```

Verify you can access the cluster

```bash
kubectl cluster-info --context kind-kind
```

Switch your kube context to the newly created cluster:

```bash
kubectl config use-context kind-kind
```

##### Installing Kaiwo and other dependencies

Install dependencies for the local cluster by following the instructions in the links below.

Links:

- https://silogen.github.io/kaiwo/admin/installation/
- https://external-secrets.io/main/introduction/getting-started/#installing-with-helm
- https://kyverno.io/docs/installation/methods/#standalone-installation

After these steps, your local cluster should be ready to run the dispatcher application.

##### Running Dispatcher in Kubernetes

Run from the root of the `amd-eai-suite/` repository:

```bash
kubectl kustomize services/airm/dispatcher/local/. --enable-helm | kubectl apply -f -
```

This will deploy the dispatcher application in the `airm` namespace, along with necessary cron-jobs and service accounts.

The application is volume mounted and has hot-reloading enabled, so everytime you make a code change, the code in the cluster will reload.
If everything goes well, you should see in the UI that the cluster has successfully onboarded to AIRM.

### Applying the ExternalSecret resource

At some point it may be necessary to test secrets management in the AIRM.
The easiest way to test the external secrets management is to use the functionality via the AIRM UI.
Once a cluster has been onboarded, navigate to the "Secrets" tab of the organization and add the following External Secret.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: my-app-secrets
spec:
  refreshInterval: 1m
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend-dev
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
    - secretKey: secret1
      remoteRef:
        key: test # 'test' is the KV key path under local-testing/
        property: secret1
    - secretKey: secret2
      remoteRef:
        key: test
        property: secret2
```

Assign the secret to a project and validate the secret is created in the cluster.

#### Running without a Kubernetes cluster

⚠️ Not recommended since there is no way of controlling how many local environments are connected to a cluster and you may be overwriting others' work.

#### Setting up access to a kubernetes cluster

Make sure you have access to a kubernetes cluster with kaiwo installed and have the correct kube-context set
Set environment variable 'USE_LOCAL_KUBE_CONTEXT' to `true` in the `.env` file

##### Running dispatcher locally

Run the following command from the dispatcher directory of the `amd-eai-suite/` repository:

```bash
uv run -m app
```

Since there are no cron-jobs running as part of the local setup, you will have to routinely stop and start the dispatcher application to simulate cron-jobs being triggered, if you want to submit workloads or quotas to the cluster.

## Testing

Run tests in the dispatcher directory

```bash
uv run pytest
```

## Builds and deployment

### Docker image build

Docker image building process is done at each push event for each branch, main included.
The docker images have the following format:

```txt
amdenterpriseai/airm-dispatcher:<branch-name>-<commit-hash>
```

E.g. amdenterpriseai/airm-dispatcher:main-b973967
