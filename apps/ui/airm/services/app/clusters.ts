// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  getErrorMessage,
  buildQueryParams,
  APIRequestError,
} from '@amdenterpriseai/utils/app';

import {
  ClusterKubeConfig,
  ClusterStatsResponse,
  CollectionRequestParams,
  EditClusterRequest,
} from '@amdenterpriseai/types';

import type {
  NodeGpuDevicesResponse,
  NodeGpuUtilizationResponse,
  NodeGpuUtilizationRawResponse,
  NodeJunctionTemperatureResponse,
  NodeJunctionTemperatureRawResponse,
  NodeMemoryTemperatureResponse,
  NodeMemoryTemperatureRawResponse,
  NodePowerUsageResponse,
  NodePowerUsageRawResponse,
} from '@/types/clusters';
import {
  WorkloadWithMetricsServer,
  ClusterWorkloadsMetricsResponse,
  NodeWorkloadsMetricsResponse,
} from '@/types/workloads';
import { normalizeNodeGpuUtilizationResponse } from '@/utils/node-gpu-utilization';
import {
  MAX_POWER_USAGE_INTERVALS,
  MAX_TEMPERATURE_INTERVALS,
} from '@/constants/clusters/nodeDetail';

export type { NodeGpuUtilizationResponse } from '@/types/clusters';
export type { NodePowerUsageResponse } from '@/types/clusters';

export const fetchClusters = async () => {
  const response = await fetch('/api/clusters');
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get clusters: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const addCluster = async () => {
  const response = await fetch('/api/clusters', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: '{}',
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to create cluster: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const getCluster = async (id: string) => {
  const response = await fetch(`/api/clusters/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch cluster: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteCluster = async (id: string) => {
  const response = await fetch(`/api/clusters/${id}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete cluster: ${errorMessage}`,
      response.status,
    );
  }
  return response;
};

export const editCluster = async (id: string, data: EditClusterRequest) => {
  const response = await fetch(`/api/clusters/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to edit cluster: ${errorMessage}`,
      response.status,
    );
  }
  return response;
};

export const getClusterNodes = async (clusterId: string) => {
  const response = await fetch(`/api/clusters/${clusterId}/nodes`);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get cluster nodes: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchClusterStatistics =
  async (): Promise<ClusterStatsResponse> => {
    const response = await fetch(`/api/clusters/stats`);
    if (!response.ok) {
      const errorMessage = await getErrorMessage(response);
      throw new APIRequestError(
        `Failed to get Cluster Statistics: ${errorMessage}`,
        response.status,
      );
    }
    return response.json();
  };

export const fetchClusterKubeConfig = async (
  clusterId: string,
): Promise<ClusterKubeConfig> => {
  const response = await fetch(`/api/clusters/${clusterId}/kube-config`);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get cluster kube config: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchClusterWorkloadsMetrics = async (
  clusterId: string,
  collectionRequestParams: CollectionRequestParams<WorkloadWithMetricsServer>,
): Promise<ClusterWorkloadsMetricsResponse> => {
  const queryParams = buildQueryParams(
    collectionRequestParams.page,
    collectionRequestParams.pageSize,
    collectionRequestParams.filter,
    collectionRequestParams.sort,
  );

  const response = await fetch(
    `/api/clusters/${clusterId}/workloads/metrics?${queryParams}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get Cluster Workloads Metrics: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchClusterWorkloadsStatusStats = async (clusterId: string) => {
  const response = await fetch(`/api/clusters/${clusterId}/workloads/stats`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get Cluster Workloads Status Stats: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

const buildNodeMetricParams = (
  start: Date,
  end: Date,
  step?: number,
): URLSearchParams => {
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
  });
  if (step != null) params.set('step', String(step));
  return params;
};

export const fetchNodeGpuDevices = async (
  clusterId: string,
  nodeId: string,
): Promise<NodeGpuDevicesResponse> => {
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/gpu-devices`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node GPU devices: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchNodeGpuUtilization = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
  step?: number,
): Promise<NodeGpuUtilizationResponse> => {
  const params = buildNodeMetricParams(start, end, step);
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/gpu-utilization/core-utilization?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node GPU utilization: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodeGpuUtilizationRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};

export const fetchNodeGpuVramUtilization = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
  step?: number,
): Promise<NodeGpuUtilizationResponse> => {
  const params = buildNodeMetricParams(start, end, step);
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/gpu-utilization/memory-utilization?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node GPU VRAM utilization: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodeGpuUtilizationRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};

export const fetchNodeGpuClockSpeed = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
  step?: number,
): Promise<NodeGpuUtilizationResponse> => {
  const params = buildNodeMetricParams(start, end, step);
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/gpu-utilization/clock-speed?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node GPU clock speed: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodeGpuUtilizationRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};

export const fetchNodeGpuJunctionTemperature = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
): Promise<NodeJunctionTemperatureResponse> => {
  const stepSeconds = Math.floor(
    (end.getTime() - start.getTime()) / 1000 / MAX_TEMPERATURE_INTERVALS,
  );
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
    step: String(Math.max(1, stepSeconds)),
  });
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/temperature/junction?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node GPU junction temperature: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodeJunctionTemperatureRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};

export const fetchNodeGpuMemoryTemperature = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
): Promise<NodeMemoryTemperatureResponse> => {
  const stepSeconds = Math.floor(
    (end.getTime() - start.getTime()) / 1000 / MAX_TEMPERATURE_INTERVALS,
  );
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
    step: String(Math.max(1, stepSeconds)),
  });
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/temperature/memory?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node GPU memory temperature: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodeMemoryTemperatureRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};

export const fetchNodePowerUsage = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
): Promise<NodePowerUsageResponse> => {
  const stepSeconds = Math.floor(
    (end.getTime() - start.getTime()) / 1000 / MAX_POWER_USAGE_INTERVALS,
  );
  const params = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
    step: String(Math.max(1, stepSeconds)),
  });
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/power-usage?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node GPU power usage: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodePowerUsageRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};

export const fetchNodeWorkloadsMetrics = async (
  clusterId: string,
  nodeId: string,
): Promise<NodeWorkloadsMetricsResponse> => {
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/workloads/metrics`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node workloads metrics: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchNodePcieBandwidth = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
  step?: number,
): Promise<NodeGpuUtilizationResponse> => {
  const params = buildNodeMetricParams(start, end, step);
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/pcie/bandwidth?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node PCIe bandwidth: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodeGpuUtilizationRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};

export const fetchNodePcieEfficiency = async (
  clusterId: string,
  nodeId: string,
  start: Date,
  end: Date,
  step?: number,
): Promise<NodeGpuUtilizationResponse> => {
  const params = buildNodeMetricParams(start, end, step);
  const response = await fetch(
    `/api/clusters/${clusterId}/nodes/${nodeId}/metrics/pcie/efficiency?${params}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get node PCIe efficiency: ${errorMessage}`,
      response.status,
    );
  }
  const raw = (await response.json()) as NodeGpuUtilizationRawResponse;
  return normalizeNodeGpuUtilizationResponse(raw);
};
