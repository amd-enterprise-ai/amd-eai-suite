// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { DocEntry } from './RelevantDocs';

export enum AirmDocsPage {
  DASHBOARD = 'dashboard',
  CLUSTERS = 'clusters',
  PROJECTS = 'projects',
  SECRETS = 'secrets',
  STORAGE = 'storage',
  USERS = 'users',
}

type AirmDocumentationMapping = Record<AirmDocsPage, DocEntry[]>;

export const airmDocumentationMapping: AirmDocumentationMapping = {
  [AirmDocsPage.DASHBOARD]: [
    {
      title: 'Resource Manager Quick Start',
      description:
        'Learn how to get started with AMD Resource Manager by onboarding users, understanding key terminology, and managing projects.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/quick-start.html',
    },
    {
      title: 'AMD Resource Manager Overview',
      description:
        'The AMD Resource Manager provides administrators with tools to oversee and control the platform\u2019s computational resources and user access.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/overview.html',
    },
    {
      title: 'What the Dashboard Shows',
      description:
        'See onboarded clusters and GPU availability, track running and pending workloads, and review GPU utilization and project usage over time.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/dashboard.html',
    },
  ],
  [AirmDocsPage.CLUSTERS]: [
    {
      title: 'Clusters Overview',
      description:
        'See all onboarded clusters and their health, available nodes, quota-backed GPU/CPU/memory allocation, and running workloads; drill into a cluster for project and per-node details.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/clusters/overview.html',
    },
    {
      title: 'Accessing the Cluster',
      description:
        'Learn how to access the cluster by extracting the kubeconfig and logging in via kubectl.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/workloads/accessing-the-cluster.html',
    },
    {
      title: 'Resource Manager Quick Start',
      description:
        'Learn how to get started with AMD Resource Manager by onboarding users, understanding key terminology, and managing projects.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/quick-start.html',
    },
  ],
  [AirmDocsPage.PROJECTS]: [
    {
      title: 'Manage Projects',
      description:
        'Learn what a project is, how quotas and access work, and how admins create, edit, and delete projects.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/projects/manage-projects.html',
    },
    {
      title: 'Project Dashboard',
      description:
        'The project dashboard is the main view for a project. It provides resource utilization metrics and information about the project\u2019s workloads. You can open project settings from there to edit details.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/projects/project-dashboard.html',
    },
    {
      title: 'Project Settings',
      description:
        'Project settings are where you manage that project\u2019s access and resources. Among other things, you can set guaranteed quotas, attach org-level storage and secrets, add or invite users, or delete the project.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/projects/project-settings.html',
    },
  ],
  [AirmDocsPage.SECRETS]: [
    {
      title: 'Secrets Overview',
      description:
        'Secrets provide a centralized and secure mechanism for storing, retrieving, and distributing sensitive data. This page explains External Secrets (e.g. AWS, GCP, Azure) versus native Kubernetes Secrets, organization- versus project-scoped secrets, and access control.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/secrets/overview.html',
    },
    {
      title: 'Manage Secrets',
      description:
        'Secrets provide a secure way to store sensitive information such as API keys, database credentials, or tokens. They are created at the organizational level and can be assigned to one or more projects.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/secrets/manage-secrets.html',
    },
    {
      title: 'Create a Hugging Face token',
      description:
        'Learn how to create and securely store Hugging Face tokens, which are required to download and access gated models from Hugging Face.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/tutorials/create-hugging-face-token.html',
    },
  ],
  [AirmDocsPage.STORAGE]: [
    {
      title: 'Storage Overview',
      description:
        'Storage resources allow you to securely manage and distribute data storage configurations\u2014such as S3 buckets and their credentials\u2014across your organization and projects.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/storage/overview.html',
    },
    {
      title: 'Manage Storage',
      description:
        'Storage resources allow you to securely manage and distribute data storage configurations\u2014such as S3 buckets and their credentials\u2014across your organization and projects. This guide explains how to create, assign, and delete storage resources using the Resource Manager UI.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/storage/manage-storage.html',
    },
    {
      title: 'Manage Secrets',
      description:
        'If you need to create a new secret for your storage, follow the instructions in Manage Secrets. The storage creation workflow will prompt you to select an existing secret or create a new one.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/secrets/manage-secrets.html',
    },
  ],
  [AirmDocsPage.USERS]: [
    {
      title: 'Users Overview',
      description:
        'Learn about AMD Resource Manager\u2019s user roles: platform administrator, super administrator, and team member.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/users/overview.html',
    },
    {
      title: 'Manage Users',
      description:
        'Learn how to use the Users page to list and search people, open a user to update their name and project assignments or role, invite users, and delete accounts.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/users/manage-users.html',
    },
    {
      title: 'Set Up User Management',
      description:
        'Resource Manager offers flexible user management options to meet different organizational requirements. The following page outlines approaches to user authentication and provisioning.',
      url: 'https://enterprise-ai.docs.amd.com/en/latest/resource-manager/users/set-up/overview.html',
    },
  ],
};
