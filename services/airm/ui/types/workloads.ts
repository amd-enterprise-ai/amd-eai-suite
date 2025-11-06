// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterBasicInfo } from './clusters';
import { ProjectBasicInfo } from './projects';
import { ServerCollectionMetadata } from './data-table/server-collection';
import { Dataset } from './datasets';
import { LogLevel, WorkloadStatus, WorkloadType } from './enums/workloads';
import { SnakeCaseKeys } from './misc';
import { Model } from './models';

export type ProjectUtilization = {
  date: string;
  memoryUsage: number;
  deviceUsage: number;
};

export type ProjectWorkloadWithMetrics = {
  id: string;
  projectId: string;
  clusterId: string;
  status: WorkloadStatus;
  displayName: string | null;
  type: WorkloadType | null;
  gpuCount: number;
  vram: number;
  runTime: number;
  createdAt: string;
  createdBy: string;
};

export type ProjectWorkloadWithMetricsServer =
  SnakeCaseKeys<ProjectWorkloadWithMetrics> & {
    total_elapsed_seconds: number;
  };

export type ProjectWorkloadsMetricsResponse = {
  workloads: ProjectWorkloadWithMetrics[];
} & ServerCollectionMetadata;

export type AllocatedResources = {
  gpuCount: number | null;
  vram: number | null;
};

// reference: services/airm/api/app/managed_workloads/schemas.py
export interface Workload {
  id: string;
  type: WorkloadType;
  name: string;
  displayName: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  status: WorkloadStatus;
  userInputs?: any;
  output?: WorkloadOutput;
  capabilities?: string[];
  chartId: string;
  clusterId: string;
  cluster: ClusterBasicInfo;
  project?: ProjectBasicInfo;
  modelId?: string | null;
  model?: Model | null;
  datasetId?: string | null;
  dataset?: Dataset | null;
  aimId?: string | null;
  clusterAuthGroupId?: string | null;
  allocatedResources?: AllocatedResources;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
}

export interface WorkloadLogPagination {
  hasMore: boolean;
  pageToken: string | undefined;
  totalReturned: number;
}

export interface WorkloadLogResponse {
  logs: LogEntry[];
  pagination: WorkloadLogPagination;
}

export type WorkloadLogParams = {
  startDate?: string;
  endDate?: string;
  pageToken?: string;
  limit?: number;
  level?: LogLevel;
  direction?: 'forward' | 'backward';
};

export interface WorkloadOutput {
  internalHost?: string;
  externalHost?: string;
  host?: string;
}

export type WorkloadsStats = {
  runningWorkloadsCount: number;
};
