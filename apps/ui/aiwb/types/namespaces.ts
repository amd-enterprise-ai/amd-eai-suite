// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  WorkloadStatus,
  WorkloadType,
  ResourceType,
} from '@amdenterpriseai/types';

export interface ResourceMetrics {
  id: string;
  name: string;
  displayName: string | null;
  type: WorkloadType;
  status: WorkloadStatus;
  gpuCount: number | null;
  vram: number | null;
  createdAt: string | null;
  createdBy: string | null;
  resourceType: ResourceType;
}

export interface NamespaceMetricsResponse {
  data: ResourceMetrics[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface NamespaceStatsResponse {
  namespace: string;
  total: number;
  statusCounts: Array<{
    status: WorkloadStatus;
    count: number;
  }>;
}

export interface ChattableResource {
  id: string;
  name: string;
  displayName: string | null;
  type: WorkloadType;
  status: WorkloadStatus;
}

export interface ChattableResponse {
  aimServices: ChattableResource[];
  workloads: ChattableResource[];
}

export interface NamespacesResponse {
  data: { id: string; name: string }[];
}
