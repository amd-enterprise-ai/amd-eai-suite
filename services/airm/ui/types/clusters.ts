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
  baseUrl?: string;
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
  clusters: Cluster[];
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
  clusterNodes: ClusterNode[];
};

export type ClusterIdentifierFormData = {
  name: string;
};

export type CheckClusterStatusResult = {
  isSuccess: boolean;
  data?: {
    status: ClusterStatus;
  };
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
  baseUrl: string;
};

export type EditClusterRequest = {
  base_url: string;
};
