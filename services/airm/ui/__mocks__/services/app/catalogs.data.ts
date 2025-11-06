// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { CatalogItem } from '@/types/catalog';
import {
  CatalogItemCategory,
  CatalogItemType,
  CatalogUsageScope,
} from '@/types/enums/catalog';

export const mockCatalogItems: CatalogItem[] = [
  {
    id: '1',
    name: 'test-workload-1',
    displayName: 'Test workload 1',
    slug: 'test-workload-1',
    description: 'Test description 1',
    longDescription: 'Detailed description for Test workload 1',
    type: CatalogItemType.WORKSPACE,
    category: CatalogItemCategory.DEVELOPMENT,
    createdAt: '2023-01-01T00:00:00Z',
    tags: ['tag1', 'tag2'],
    featuredImage: '',
    requiredResources: {
      gpuCount: 1,
      gpuMemory: 8,
      cpuCoreCount: 4,
      systemMemory: 16,
    },
    available: true,
    externalUrl: 'https://example.com/workload-1',
    workloadsCount: 0,
    workloads: [],
    usageScope: CatalogUsageScope.USER,
  },
  {
    id: '2',
    name: 'test-workload-2',
    displayName: 'Test workload 2',
    slug: 'test-workload-2',
    description: 'Test description 2',
    longDescription: 'Detailed description for Test workload 2',
    type: CatalogItemType.WORKSPACE,
    category: CatalogItemCategory.DEVELOPMENT,
    createdAt: '2023-01-02T00:00:00Z',
    tags: ['tag3'],
    featuredImage: '',
    requiredResources: {
      gpuCount: 2,
      gpuMemory: 16,
      cpuCoreCount: 8,
      systemMemory: 32,
    },
    available: false,
    externalUrl: 'https://example.com/workload-2',
    workloadsCount: 0,
    workloads: [],
    usageScope: CatalogUsageScope.USER,
  },
];

export const mockProjectScopedCatalogItems: CatalogItem[] = [
  {
    displayName: 'MLflow Tracking Server',
    slug: 'mlflow',
    description: 'ML experiment tracking and model management',
    longDescription:
      'MLflow is an open-source platform for managing the machine learning lifecycle, including experimentation, reproducibility, deployment, and a central model registry. This deployment provides a centralized MLflow tracking server for logging metrics, parameters, and artifacts from machine learning experiments.',
    category: CatalogItemCategory.DEVELOPMENT,
    tags: ['mlflow', 'experiment-tracking', 'model-management'],
    featuredImage: 'https://avatars.githubusercontent.com/u/39938107',
    requiredResources: {
      gpuCount: 0,
      gpuMemory: 0,
      cpuCoreCount: 1,
      systemMemory: 20,
    },
    externalUrl: 'https://mlflow.org/',
    name: 'dev-tracking-mlflow',
    type: CatalogItemType.WORKSPACE,
    id: '28d2eee1-616e-47ae-a73d-19c72a939d27',
    createdAt: '2025-09-24T09:53:26.239368Z',
    usageScope: CatalogUsageScope.PROJECT,
    workloadsCount: 0,
    workloads: [],
  },
];
