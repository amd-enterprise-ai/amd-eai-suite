// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { WorkloadType } from '@amdenterpriseai/types';

import { LogLevel, LogType, WorkloadStatus } from './enums/workloads';

export type ProjectUtilization = {
  date: string;
  memoryUsage: number;
  deviceUsage: number;
};

export type AllocatedResources = {
  gpuCount: number | null;
  vram: number | null;
};

/** Embedded project on workload payloads (e.g. org-wide or cross-namespace lists). */
export type WorkloadEmbeddedProject = {
  id: string;
  name: string;
  description?: string | null;
  clusterId?: string;
  status?: string;
  statusReason?: string | null;
};

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
  userInputs?: any;
  output?: WorkloadOutput;
  chartId?: string | null;
  datasetId?: string | null;
  aimId?: string | null;
  clusterAuthGroupId?: string | null;
  allocatedResources?: AllocatedResources;
  endpoints?: {
    internal?: string;
    external?: string;
  };
  project?: WorkloadEmbeddedProject;
  tags?: string[];
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
