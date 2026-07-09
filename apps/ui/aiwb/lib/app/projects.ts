// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError } from '@amdenterpriseai/utils/app';
import { getErrorMessage } from '@amdenterpriseai/utils/app';
import {
  TimeSeriesResponse,
  SortDirection,
  ServerSideSortDirection,
  WorkloadType,
} from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';
import type {
  WorkloadMetricsResponse,
  ProjectsResponse,
  WorkloadStatsResponse,
} from '@/types/projects';

// Map UI field names to backend field names
const FIELD_NAME_MAP: Record<string, string> = {
  createdAt: 'createdAt',
  createdBy: 'createdBy',
  displayName: 'displayName',
  name: 'name',
  type: 'type',
  status: 'status',
};

export interface FetchProjectWorkloadMetricsParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: SortDirection;
  workloadTypes?: WorkloadType[];
  statusFilter?: WorkloadStatus[];
}

export const fetchProjectWorkloadMetrics = async (
  project: string,
  options: FetchProjectWorkloadMetricsParams = {},
): Promise<WorkloadMetricsResponse> => {
  const {
    page = 1,
    pageSize = 10,
    sortBy,
    sortOrder,
    workloadTypes,
    statusFilter,
  } = options;

  const params = new URLSearchParams({
    page: page.toString(),
    pageSize: pageSize.toString(),
  });

  if (sortBy) {
    const backendField = FIELD_NAME_MAP[sortBy] ?? sortBy;
    params.set('sortBy', backendField);
    params.set(
      'sortOrder',
      sortOrder === SortDirection.ASC
        ? ServerSideSortDirection.ASC
        : ServerSideSortDirection.DESC,
    );
  }

  for (const type of workloadTypes ?? []) {
    params.append('workloadType', type);
  }

  for (const status of statusFilter ?? []) {
    params.append('statusFilter', status);
  }

  const response = await fetch(
    `/api/projects/${project}/workloads/metrics?${params}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project workload metrics: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchProjectWorkloadStats = async (
  project: string,
): Promise<WorkloadStatsResponse> => {
  const response = await fetch(`/api/projects/${project}/workloads/stats`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project workload stats: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchProjectGPUMemoryUtilization = async (
  project: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
  });

  const response = await fetch(
    `/api/projects/${project}/workloads/metrics/gpu_memory_utilization?${params}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project GPU memory utilization: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchProjectGPUDeviceUtilization = async (
  project: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
  });

  const response = await fetch(
    `/api/projects/${project}/workloads/metrics/gpu_device_utilization?${params}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project GPU device utilization: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchProjects = async (): Promise<ProjectsResponse> => {
  const response = await fetch(`/api/projects`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get projects: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();

  const transformedData = {
    data: (json.data || []).map((project: string) => ({
      id: project,
      name: project,
    })),
  };

  return transformedData;
};
