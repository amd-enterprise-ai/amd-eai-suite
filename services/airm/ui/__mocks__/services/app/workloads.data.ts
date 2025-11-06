// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterStatus } from '@/types/enums/cluster-status';
import { ProjectStatus } from '@/types/enums/projects';
import {
  WorkloadStatus,
  WorkloadType,
  LogLevel,
} from '@/types/enums/workloads';
import { Workload, LogEntry } from '@/types/workloads';
import { ModelOnboardingStatus } from '@/types/models';

/**
 * Mock log entries for testing workload logs
 */
export const mockWorkloadLogEntries: LogEntry[] = [
  {
    timestamp: '2023-01-01T00:00:00Z',
    level: LogLevel.INFO,
    message: 'First log entry',
  },
  {
    timestamp: '2023-01-01T00:00:01Z',
    level: LogLevel.WARNING,
    message: 'Second log entry',
  },
  {
    timestamp: '2023-01-01T00:00:02Z',
    level: LogLevel.ERROR,
    message: 'Third log entry',
  },
];

/**
 * Mock data for workloads to be used in tests
 */
export const mockWorkloads: Workload[] = [
  {
    id: 'workload-1',
    name: 'Llama 7B Inference',
    displayName: 'Llama 7B Inference',
    createdBy: 'test-user',
    chartId: 'chart-1',
    clusterId: 'cluster-1',
    type: WorkloadType.INFERENCE,
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-01T00:00:00Z',
      status: ClusterStatus.HEALTHY,
    },
    project: {
      id: 'project-1',
      name: 'Test Project',
      description: 'Test project description',
      status: ProjectStatus.READY,
      statusReason: null,
      clusterId: 'cluster-1',
    },
    modelId: 'model-1',
    model: {
      id: 'model-1',
      name: 'Llama 7B',
      canonicalName: 'meta/llama-7b',
      createdAt: '2023-01-01T00:00:00Z',
      onboardingStatus: ModelOnboardingStatus.READY,
      createdBy: 'test',
      modelWeightsPath: '/models/llama-7b',
    },
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T01:00:00Z',
    status: WorkloadStatus.RUNNING,
    output: {
      externalHost: 'https://example.com/inference',
      internalHost: 'https://example.com/inference',
    },
    allocatedResources: {
      gpuCount: 1,
      vram: 2147483648.0,
    },
  },
  {
    id: 'workload-2',
    name: 'SDXL Download',
    displayName: 'Stable Diffusion XL Download',
    createdBy: 'test-user',
    chartId: 'chart-2',
    clusterId: 'cluster-1',
    type: WorkloadType.MODEL_DOWNLOAD,
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-02T00:00:00Z',
      status: ClusterStatus.HEALTHY,
    },
    modelId: 'model-2',
    model: {
      id: 'model-2',
      name: 'Stable Diffusion XL',
      canonicalName: 'stabilityai/stable-diffusion-xl',
      createdAt: '2023-01-02T00:00:00Z',
      onboardingStatus: ModelOnboardingStatus.PENDING,
      createdBy: 'test',
      modelWeightsPath: '/models/sdxl',
    },
    createdAt: '2023-01-02T00:00:00Z',
    updatedAt: '2023-01-02T01:00:00Z',
    status: WorkloadStatus.PENDING,
    allocatedResources: {
      gpuCount: 2,
      vram: 4294967296.0,
    },
  },
  {
    id: 'workload-3',
    name: 'Jupyter Workspace',
    displayName: 'Jupyter Workspace',
    createdBy: 'test-user',
    chartId: 'chart-3',
    clusterId: 'cluster-2',
    type: WorkloadType.WORKSPACE,
    cluster: {
      id: 'cluster-2',
      name: 'Dev Cluster',
      lastHeartbeatAt: '2023-01-03T00:00:00Z',
      status: ClusterStatus.HEALTHY,
    },
    createdAt: '2023-01-03T00:00:00Z',
    updatedAt: '2023-01-03T01:00:00Z',
    status: WorkloadStatus.RUNNING,
    output: {
      externalHost: 'https://jupyter.example.com',
      internalHost: 'https://jupyter.example.com',
    },
    allocatedResources: {
      gpuCount: 0,
      vram: 1073741824.0,
    },
  },
  {
    id: 'workload-4',
    name: 'Model fine-tuning',
    displayName: 'Model fine-tuning Job',
    createdBy: 'test-user',
    chartId: 'chart-4',
    clusterId: 'cluster-1',
    type: WorkloadType.FINE_TUNING,
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-04T00:00:00Z',
      status: ClusterStatus.HEALTHY,
    },
    createdAt: '2023-01-04T00:00:00Z',
    updatedAt: '2023-01-04T01:00:00Z',
    status: WorkloadStatus.FAILED,
    allocatedResources: {
      gpuCount: 4,
      vram: 8589934592.0,
    },
  },
  {
    id: 'workload-5',
    name: 'Deleted Workload',
    displayName: 'Deleted Inference',
    createdBy: 'test-user',
    chartId: 'chart-5',
    clusterId: 'cluster-1',
    type: WorkloadType.INFERENCE,
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-05T00:00:00Z',
      status: ClusterStatus.HEALTHY,
    },
    createdAt: '2023-01-05T00:00:00Z',
    updatedAt: '2023-01-05T01:00:00Z',
    status: WorkloadStatus.DELETED,
    allocatedResources: {
      gpuCount: 1,
      vram: 2147483648.0,
    },
  },
  {
    id: 'workload-6',
    name: 'Fine-tuning Workload with Dataset',
    displayName: 'Fine-tuning Model with Dataset',
    createdBy: 'user-2',
    chartId: 'chart-6',
    clusterId: 'cluster-1',
    type: WorkloadType.FINE_TUNING,
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-06T00:00:00Z',
      status: ClusterStatus.HEALTHY,
    },
    modelId: 'model-3',
    model: {
      id: 'model-3',
      name: 'GPT-4 Base',
      canonicalName: 'openai/gpt-4-base',
      createdAt: '2023-01-03T00:00:00Z',
      onboardingStatus: ModelOnboardingStatus.READY,
      createdBy: 'test',
      modelWeightsPath: '/models/gpt-4-base',
    },
    datasetId: 'dataset-1',
    createdAt: '2023-01-06T00:00:00Z',
    updatedAt: '2023-01-06T01:00:00Z',
    status: WorkloadStatus.PENDING,
    userInputs: {
      datasetPath: '/datasets/fine-tuning-dataset',
    },
    allocatedResources: {
      gpuCount: 3,
      vram: 8589934592.0,
    },
  },
  {
    id: 'workload-7',
    name: 'Production Cluster Workload',
    displayName: 'Production Workspace',
    createdBy: 'user-3',
    chartId: 'chart-7',
    clusterId: 'cluster-2',
    type: WorkloadType.WORKSPACE,
    cluster: {
      id: 'cluster-2',
      name: 'Production Cluster',
      lastHeartbeatAt: '2023-01-07T00:00:00Z',
      status: ClusterStatus.UNHEALTHY,
    },
    modelId: 'model-1',
    createdAt: '2023-01-07T00:00:00Z',
    updatedAt: '2023-01-07T01:00:00Z',
    status: WorkloadStatus.DELETING,
    output: {
      externalHost: 'https://workspace.example.com/workload-7',
      internalHost: 'https://workspace.example.com/workload-7',
    },
    allocatedResources: {
      gpuCount: 3,
      vram: 8589934592.0,
    },
  },
  {
    id: 'workload-8',
    name: 'Delete Failed Inference',
    displayName: 'Delete Failed Inference',
    createdBy: 'user-2',
    chartId: 'chart-8',
    clusterId: 'cluster-1',
    type: WorkloadType.INFERENCE,
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-08T00:00:00Z',
      status: ClusterStatus.HEALTHY,
    },
    modelId: 'model-2',
    createdAt: '2023-01-08T00:00:00Z',
    updatedAt: '2023-01-08T01:00:00Z',
    status: WorkloadStatus.DELETE_FAILED,
    userInputs: {
      error: 'Unable to delete due to active connections',
    },
    allocatedResources: {
      gpuCount: 3,
      vram: 8589934592.0,
    },
  },
  {
    id: 'workload-9',
    name: 'Unhealthy Cluster Fine-tuning',
    displayName: 'Fine-tuning on Unhealthy Cluster',
    createdBy: 'user-1',
    chartId: 'chart-9',
    clusterId: 'cluster-2',
    type: WorkloadType.FINE_TUNING,
    cluster: {
      id: 'cluster-2',
      name: 'Production Cluster',
      lastHeartbeatAt: '2023-01-09T00:00:00Z',
      status: ClusterStatus.UNHEALTHY,
    },
    modelId: 'model-3',
    createdAt: '2023-01-09T00:00:00Z',
    updatedAt: '2023-01-09T01:00:00Z',
    status: WorkloadStatus.DELETED,
    allocatedResources: {
      gpuCount: null,
      vram: null,
    },
  },
  {
    id: 'workload-10',
    name: 'Model Download with Evaluation',
    displayName: 'Model Download with Evaluation Config',
    createdBy: 'user-3',
    chartId: 'chart-10',
    clusterId: 'cluster-1',
    type: WorkloadType.MODEL_DOWNLOAD,
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-10T00:00:00Z',
      status: ClusterStatus.VERIFYING,
    },
    modelId: 'model-1',
    createdAt: '2023-01-10T00:00:00Z',
    updatedAt: '2023-01-10T01:00:00Z',
    status: WorkloadStatus.UNKNOWN,
    userInputs: {
      evaluationConfig: {
        metrics: ['accuracy', 'perplexity'],
        batchSize: 16,
      },
    },
    allocatedResources: {
      gpuCount: 3,
      vram: 8589934592.0,
    },
  },
];
