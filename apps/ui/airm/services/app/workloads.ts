// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage, APIRequestError } from '@amdenterpriseai/utils/app';

import {
  Workload,
  WorkloadLogParams,
  WorkloadLogResponse,
} from '@amdenterpriseai/types';
import { WorkloadGpuDevicesMetricsResponse } from '@/types/workloads';
import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import {
  MetricScalarResponse,
  TimeSeriesResponse,
} from '@amdenterpriseai/types';

import { WorkloadMetricsDetails } from '@/types/workloads';

export interface WorkloadsResponse {
  data: Workload[];
  total: number;
  page: number;
  pageSize: number;
}

export const getWorkload = async (id: string): Promise<Workload | null> => {
  const response = await fetch(`/api/workloads/${id}`, { method: 'GET' });
  if (!response.ok) {
    if (response.status === 404) return null;
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const getWorkloadMetrics = async (
  id: string,
): Promise<WorkloadMetricsDetails | null> => {
  const response = await fetch(`/api/workloads/${id}/metrics`, {
    method: 'GET',
  });
  if (!response.ok) {
    if (response.status === 404) return null;
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload metrics: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteWorkload = async (id: string) => {
  const response = await fetch(`/api/workloads/${id}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to terminate workload: ${errorMessage}`,
      response.status,
    );
  }
};

export const getWorkloadGpuDevicesMetrics = async (
  workloadId: string,
): Promise<WorkloadGpuDevicesMetricsResponse> => {
  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/gpu-devices`,
    { method: 'GET' },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload GPU device metrics: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

const fetchGpuDeviceMetric = async (
  workloadId: string,
  metric: string,
  params: { start: string; end: string },
): Promise<WorkloadGpuDevicesMetricsResponse> => {
  const qs = new URLSearchParams(params).toString();
  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/gpu-devices/${metric}?${qs}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload GPU ${metric}: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const getWorkloadVramUtilization = (
  workloadId: string,
  params: { start: string; end: string },
) => fetchGpuDeviceMetric(workloadId, 'vram-utilization', params);

export const getWorkloadJunctionTemperature = (
  workloadId: string,
  params: { start: string; end: string },
) => fetchGpuDeviceMetric(workloadId, 'junction-temperature', params);

export const getWorkloadPowerUsage = (
  workloadId: string,
  params: { start: string; end: string },
) => fetchGpuDeviceMetric(workloadId, 'power-usage', params);

export const getClusterWorkloadsStats = async (clusterId: string) => {
  const response = await fetch(`/api/clusters/${clusterId}/workloads/stats`);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get cluster workloads stats: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const getWorkloadsStats = async () => {
  const response = await fetch(`/api/workloads/stats`);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workloads stats: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};
