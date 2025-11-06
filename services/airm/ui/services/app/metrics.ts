// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';

import { TimeSeriesResponse, UtilizationResponse } from '@/types/metrics';

export const fetchGPUMemoryUtilization = async (
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const response = await fetch(
    `/api/metrics/gpu-memory-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get GPU Memory Utilization: ${await getErrorMessage(response)}`,
    );
  }
  return response.json();
};

export const fetchGPUDeviceUtilization = async (
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const response = await fetch(
    `/api/metrics/gpu-device-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get GPU Device Utilization: ${await getErrorMessage(response)}`,
    );
  }
  return response.json();
};

export const fetchUtilization = async (): Promise<UtilizationResponse> => {
  const response = await fetch(`/api/metrics/utilization`);

  if (!response.ok) {
    throw new Error(
      `Failed to get Metric Utilization: ${await getErrorMessage(response)}`,
    );
  }

  return response.json();
};

export const fetchGPUDeviceUtilizationByClusterId = async (
  clusterId: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const response = await fetch(
    `/api/clusters/${clusterId}/metrics/gpu-device-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );

  if (!response.ok) {
    throw new Error(
      `Failed to get GPU Device Utilization for cluster ${clusterId}: ${await getErrorMessage(response)}`,
    );
  }

  return response.json();
};
