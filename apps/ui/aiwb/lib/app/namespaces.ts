// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError } from '@amdenterpriseai/utils/app';
import { getErrorMessage } from '@amdenterpriseai/utils/app';
import {
  TimeSeriesResponse,
  SortDirection,
  ServerSideSortDirection,
  WorkloadStatus,
  WorkloadType,
} from '@amdenterpriseai/types';
import type {
  NamespaceMetricsResponse,
  NamespacesResponse,
  NamespaceStatsResponse,
} from '@/types/namespaces';

// Map UI field names to backend field names
const FIELD_NAME_MAP: Record<string, string> = {
  createdAt: 'created_at',
  createdBy: 'created_by',
  displayName: 'display_name',
  name: 'name',
  type: 'type',
  status: 'status',
};

export interface FetchNamespaceMetricsParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: SortDirection;
  workloadTypes?: WorkloadType[];
  statusFilter?: WorkloadStatus[];
}

export const fetchNamespaceMetrics = async (
  namespace: string,
  options: FetchNamespaceMetricsParams = {},
): Promise<NamespaceMetricsResponse> => {
  const {
    page = 1,
    pageSize = 20,
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
  }

  if (sortOrder) {
    params.set(
      'sortOrder',
      sortOrder === SortDirection.ASC
        ? ServerSideSortDirection.ASC
        : ServerSideSortDirection.DESC,
    );
  }

  for (const type of workloadTypes ?? []) {
    params.append('workload_type', type);
  }

  for (const status of statusFilter ?? []) {
    params.append('status_filter', status);
  }

  const response = await fetch(
    `/api/namespaces/${namespace}/metrics?${params}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get namespace metrics: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchNamespaceStats = async (
  namespace: string,
): Promise<NamespaceStatsResponse> => {
  const response = await fetch(`/api/namespaces/${namespace}/stats`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get namespace stats: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchNamespaceGPUMemoryUtilization = async (
  namespace: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
  });

  const response = await fetch(
    `/api/namespaces/${namespace}/metrics/gpu_memory_utilization?${params}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get namespace GPU memory utilization: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchNamespaceGPUDeviceUtilization = async (
  namespace: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
  });

  const response = await fetch(
    `/api/namespaces/${namespace}/metrics/gpu_device_utilization?${params}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get namespace GPU device utilization: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchNamespaces = async (): Promise<NamespacesResponse> => {
  const response = await fetch(`/api/namespaces`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get namespaces: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();

  const transformedData = {
    data: (json.data || []).map((namespace: string) => ({
      id: namespace,
      name: namespace,
    })),
  };

  return transformedData;
};
