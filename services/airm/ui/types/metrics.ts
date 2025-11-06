// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { WorkloadStatus } from './enums/workloads';
import { Project } from './projects';

export type TimeSeriesDataPoint = {
  timestamp: string;
  value: number | null;
};

export type TimeSeriesData = {
  metadata: Record<string, Record<string, string> | string>;
  values: TimeSeriesDataPoint[];
};

export type TimeSeriesAllocationData = {
  numerator: TimeSeriesDataPoint[];
  denominator: TimeSeriesDataPoint[];
};

export type TimeSeriesResponse = {
  data: TimeSeriesData[];
  range: {
    start: string;
    end: string;
    intervalSeconds: number;
    timestamps: string[];
  };
};

export type TimeSeriesRequest = {
  start: Date;
  end: Date;
};

export type PlotPoint = {
  date: string;
  [key: string]: number | string | null;
};

export type TimeRange = {
  start: Date;
  end: Date;
};

export type UtilizationResponse = {
  timestamp: string;
  utilizationByProject: ProjectUtilization[];
  totalUtilizedGpusCount: number;
  totalRunningWorkloadsCount: number;
  totalPendingWorkloadsCount: number;
};

export type ProjectUtilization = {
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

export type ProjectWorkloadsStatusesResponse = {
  name: string;
  totalWorkloads: number;
  statusCounts: ProjectStatusCount[];
};

export type MetricScalarResponse = {
  data: number;
  range: {
    start: string;
    end: string;
  };
};
