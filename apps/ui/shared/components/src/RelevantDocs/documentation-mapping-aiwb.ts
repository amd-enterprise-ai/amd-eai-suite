// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { DocEntry } from './RelevantDocs';

export enum AiwbDocsPage {
  DASHBOARD = 'dashboard',
  API_KEYS = 'api-keys',
  CHAT = 'chat',
  DATASETS = 'datasets',
  MODELS = 'models',
  SECRETS = 'secrets',
  WORKSPACES = 'workspaces',
}

type AiwbDocumentationMapping = Record<AiwbDocsPage, DocEntry[]>;

export const aiwbDocumentationMapping: AiwbDocumentationMapping = {
  [AiwbDocsPage.DASHBOARD]: [
    {
      title: 'How to Quick Start',
      description: 'Get started with deployment, fine-tuning, and inference.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/quick-start.html',
    },
    {
      title: 'AMD AI Workbench Overview',
      description: 'Manage your AI stack lifecycle with a low-code interface.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/overview.html',
    },
    {
      title: 'Model Inference Overview',
      description: 'Deploy and run models for inference.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/inference/how-to-deploy-and-inference.html',
    },
  ],
  [AiwbDocsPage.API_KEYS]: [
    {
      title: 'Deploy & Run Inference',
      description:
        'Deploy a model, find its endpoint, and connect via API key.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/inference/how-to-deploy-and-inference.html',
    },
    {
      title: 'API Keys',
      description: 'Integrate models into apps and workflows programmatically.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/api-keys.html',
    },
    {
      title: 'Manage Secrets',
      description: 'Create and assign secrets to projects.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/secrets/manage-secrets.html',
    },
  ],
  [AiwbDocsPage.CHAT]: [
    {
      title: 'Chat',
      description: 'Test deployments and inspect debug output.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/inference/chat.html',
    },
    {
      title: 'Compare Models',
      description:
        'Compare responses across models and parameters side by side.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/inference/compare.html',
    },
    {
      title: 'How to Deploy a Model and Run Inference',
      description:
        'Deploy a model and chat with it using JupyterLab interface.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/inference/how-to-deploy-and-inference.html',
    },
  ],
  [AiwbDocsPage.DATASETS]: [
    {
      title: 'Dataset Management',
      description:
        'Create and manage JSONL conversation datasets for fine-tuning.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/training/datasets.html',
    },
    {
      title: 'Training & Fine-tuning',
      description: 'Upload training data to start fine-tuning your model.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/training/overview.html',
    },
    {
      title: 'Fine-tuning Quick Start',
      description:
        'Prerequisites and steps for dataset prep and model training.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/tutorials/low-code-fine-tuning-tutorial.html',
    },
  ],
  [AiwbDocsPage.MODELS]: [
    {
      title: 'Model Catalog',
      description: 'Browse AIM Catalog, custom, and deployed models.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/models.html',
    },
    {
      title: 'Deploy Model and Run Inference',
      description:
        'Deploy from the AIM Catalog and connect to model endpoints.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/inference/how-to-deploy-and-inference.html',
    },
    {
      title: 'Hugging Face Token',
      description: 'Create and store tokens to access gated HF models.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/tutorials/create-hugging-face-token.html',
    },
  ],
  [AiwbDocsPage.SECRETS]: [
    {
      title: 'Manage Secrets',
      description:
        'Securely store API keys and tokens, assignable across projects.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/secrets/manage-secrets.html',
    },
    {
      title: 'How Secrets Work',
      description:
        'Centralized storage supporting External and Kubernetes Secrets.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/secrets/overview.html',
    },
    {
      title: 'Hugging Face Token',
      description: 'Create and store tokens to access gated HF models.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/tutorials/create-hugging-face-token.html',
    },
  ],
  [AiwbDocsPage.WORKSPACES]: [
    {
      title: 'Workspaces',
      description: 'Zero-config JupyterLab and VS Code on AMD compute.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/workspaces/overview.html',
    },
    {
      title: 'MLflow Tracking Server',
      description:
        'Log and manage ML experiments with a dedicated tracking server.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/workspaces/mlflow.html',
    },
    {
      title: 'Workloads',
      description:
        'Monitor status, access logs, and manage workspace instances.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/workbench/workloads.html',
    },
  ],
};
