// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { WorkloadStatus } from './enums/workloads';
import { Project } from './projects';

export type UtilizationResponse = {
  timestamp: string;
  utilizationByProject: ProjectUtilizationMetric[];
  totalUtilizedGpusCount: number;
  totalRunningWorkloadsCount: number;
  totalPendingWorkloadsCount: number;
};

export type ProjectUtilizationMetric = {
  project: Project;
  allocatedGpusCount: number;
  utilizedGpusCount: number;
  runningWorkloadsCount: number;
  pendingWorkloadsCount: number;
};

export type ProjectStatusCount = {
  status: WorkloadStatus;
  count: number;
};

export type WorkloadStatusStatsResponse = {
  name: string;
  totalWorkloads: number;
  statusCounts: ProjectStatusCount[];
};
