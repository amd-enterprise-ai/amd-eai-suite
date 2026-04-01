// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  LogLevel,
  LogType,
  WorkloadStatus,
  WorkloadType,
} from './enums/workloads';
import { ProjectBasicInfo } from './projects';

export type ProjectUtilization = {
  date: string;
  memoryUsage: number;
  deviceUsage: number;
};

export type AllocatedResources = {
  gpuCount: number | null;
  vram: number | null;
};

// reference: apps/api/airm/app/managed_workloads/schemas.py
export interface Workload {
  id: string;
  type: WorkloadType;
  name: string;
  displayName: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  updatedBy?: string | null;
  status: WorkloadStatus;
  project: ProjectBasicInfo;
  userInputs?: any;
  output?: WorkloadOutput;
  chartId?: string | null;
  modelId?: string | null;
  datasetId?: string | null;
  aimId?: string | null;
  clusterAuthGroupId?: string | null;
  allocatedResources?: AllocatedResources;
  endpoints?: {
    internal?: string;
    external?: string;
  };
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
  data: LogEntry[];
  pagination: WorkloadLogPagination;
}

export type WorkloadLogParams = {
  startDate?: string;
  endDate?: string;
  pageToken?: string;
  limit?: number;
  level?: LogLevel;
  direction?: 'forward' | 'backward';
  logType?: LogType;
};

export interface WorkloadOutput {
  internalHost?: string;
  externalHost?: string;
  host?: string;
}

export type WorkloadsStats = {
  runningWorkloadsCount: number;
  pendingWorkloadsCount: number;
};

export interface WorkloadFilterItem {
  key: string;
  label: string;
  showDivider?: boolean;
}
