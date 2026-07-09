// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus, ResourceType } from '@/types/enums/workloads';
import { PaginatedList } from '@/types/pagination';

export interface ResourceMetrics {
  id: string;
  name: string;
  displayName: string | null;
  type: WorkloadType;
  status: WorkloadStatus;
  gpuCount: number | null;
  templateGpuCount: number | null;
  gpu: string | null;
  acceleratorType: string | null;
  metric: string | null;
  precision: string | null;
  vram: number | null;
  createdAt: string | null;
  createdBy: string | null;
  resourceType: ResourceType;
}

export type WorkloadMetricsResponse = PaginatedList<ResourceMetrics>;

export interface WorkloadStatsResponse {
  project: string;
  total: number;
  statusCounts: Array<{
    status: WorkloadStatus;
    count: number;
  }>;
}

export interface ProjectsResponse {
  data: { id: string; name: string }[];
}
