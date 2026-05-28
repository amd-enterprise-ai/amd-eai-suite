// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterStatus } from './enums/cluster-status';
import { GPUInfo } from './gpu-info';
import { QuotaResourceType } from './quotas';

export type ClusterBasicInfo = {
  name: string;
  id: string;
  lastHeartbeatAt: string;
  status: ClusterStatus;
  workbenchBaseUrl?: string;
  kubeApiUrl?: string;
};

export type Cluster = ClusterBasicInfo & {
  availableResources: QuotaResourceType;
  allocatedResources: QuotaResourceType;
  totalNodeCount: number;
  availableNodeCount: number;
  assignedQuotaCount: number;
  gpuInfo?: GPUInfo;
  createdAt: string;
  gpuAllocationPercentage: number;
  cpuAllocationPercentage: number;
  memoryAllocationPercentage: number;
};

export type ClustersResponse = {
  data: Cluster[];
};

export type CreateClusterResponse = {
  name: string;
  id: string;
  userSecret: string;
};

export type ClusterNode = {
  id: string;
  name: string;
  cpuMilliCores: number;
  memoryBytes: number;
  ephemeralStorageBytes: number;
  gpuCount: number;
  gpuInfo?: GPUInfo;
  updatedAt: string;
  status: string;
};

export type ClusterNodesResponse = {
  data: ClusterNode[];
};

export type ClusterIdentifierFormData = {
  name: string;
};

export type ClusterStatsResponse = {
  totalClusterCount: number;
  totalNodeCount: number;
  availableNodeCount: number;
  totalGpuNodeCount: number;
  totalGpuCount: number;
  availableGpuCount: number;
  allocatedGpuCount: number;
};

export type EditClusterFormData = {
  workbenchBaseUrl: string;
  kubeApiUrl: string;
};

export type EditClusterRequest = {
  workbenchBaseUrl: string;
  kubeApiUrl: string;
};

export type ClusterKubeConfig = {
  kubeConfig: string;
};

export type NodeGpuUtilizationResponse = {
  gpuDevices: {
    gpuUuid: string;
    gpuId: string;
    hostname: string;
    metric: {
      seriesLabel: string;
      values: { timestamp: string; value: number }[];
    };
  }[];
  range: { start: string; end: string };
};

export type NodeGpuDevice = {
  gpuUuid: string;
  gpuId: string;
  productName: string | null;
  temperature: number | null;
  powerConsumption: number | null;
  vramUtilization: number | null;
  lastUpdated: string | null;
};

export type NodeGpuDevicesResponse = {
  gpuDevices: NodeGpuDevice[];
};

export type NodeGpuUtilizationRawResponse = {
  gpuDevices?: {
    gpuUuid: string;
    gpuId: string;
    hostname: string;
    metric?: {
      seriesLabel?: string;
      values: { timestamp: string; value: number }[];
    };
  }[];
  range?: { start: string; end: string };
};

export type NodePowerUsageResponse = NodeGpuUtilizationResponse;
export type NodePowerUsageRawResponse = NodeGpuUtilizationRawResponse;
export type NodeJunctionTemperatureResponse = NodeGpuUtilizationResponse;
export type NodeJunctionTemperatureRawResponse = NodeGpuUtilizationRawResponse;
export type NodeMemoryTemperatureResponse = NodeGpuUtilizationResponse;
export type NodeMemoryTemperatureRawResponse = NodeGpuUtilizationRawResponse;
