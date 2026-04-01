// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import {
  TimeSeriesResponse,
  UtilizationResponse,
} from '@amdenterpriseai/types';

export const fetchGPUMemoryUtilization = async (
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const response = await fetch(
    `/api/metrics/gpu-memory-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get GPU Memory Utilization: ${errorMessage}`,
      response.status,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get GPU Device Utilization: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchUtilization = async (): Promise<UtilizationResponse> => {
  const response = await fetch(`/api/metrics/utilization`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get Metric Utilization: ${errorMessage}`,
      response.status,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get GPU Device Utilization for cluster ${clusterId}: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};
