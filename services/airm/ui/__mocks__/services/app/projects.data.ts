// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterStatus } from '@/types/enums/cluster-status';
import { ProjectStatus } from '@/types/enums/projects';
import { QuotaResource, QuotaStatus } from '@/types/enums/quotas';
import {
  Project,
  ProjectBasicInfo,
  ProjectWithResourceAllocation,
  ProjectsResponse,
} from '@/types/projects';

/**
 * Basic project info matching the API structure when embedded in workloads.
 * These contain only the basic fields without nested cluster/quota objects (lazy joined).
 */
export const mockProject1: ProjectBasicInfo = {
  id: 'project-1',
  name: 'Test Project',
  description: 'Test project description',
  clusterId: 'cluster-1',
  status: ProjectStatus.READY,
  statusReason: null,
};

export const mockProject2: ProjectBasicInfo = {
  id: 'project-2',
  name: 'Dev Project',
  description: 'Development project description',
  clusterId: 'cluster-2',
  status: ProjectStatus.READY,
  statusReason: null,
};

/**
 * Full project objects with nested cluster and quota information.
 * Use these for project management pages and full project details.
 */
export const mockFullProject1: Project = {
  id: 'project-1',
  name: 'Test Project',
  description: 'Test project description',
  status: ProjectStatus.READY,
  statusReason: null,
  clusterId: 'cluster-1',
  quota: {
    [QuotaResource.GPU]: 8,
    [QuotaResource.CPU]: 32000,
    [QuotaResource.RAM]: 1000000000,
    [QuotaResource.DISK]: 5000000000,
    status: QuotaStatus.READY,
  },
  cluster: {
    id: 'cluster-1',
    name: 'Test Cluster',
    workloadsBaseUrl: 'https://test-cluster.example.com',
    lastHeartbeatAt: '2024-01-01T00:00:00Z',
    status: ClusterStatus.HEALTHY,
  },
};

export const mockFullProject2: Project = {
  id: 'project-2',
  name: 'Dev Project',
  description: 'Development project description',
  status: ProjectStatus.READY,
  statusReason: null,
  clusterId: 'cluster-2',
  quota: {
    [QuotaResource.GPU]: 4,
    [QuotaResource.CPU]: 16000,
    [QuotaResource.RAM]: 500000000,
    [QuotaResource.DISK]: 2500000000,
    status: QuotaStatus.READY,
  },
  cluster: {
    id: 'cluster-2',
    name: 'Dev Cluster',
    workloadsBaseUrl: 'https://dev-cluster.example.com',
    lastHeartbeatAt: '2024-01-01T00:00:00Z',
    status: ClusterStatus.HEALTHY,
  },
};

/**
 * Projects with resource allocation for project list/selection components.
 */
export const mockProjectWithAllocation1: ProjectWithResourceAllocation = {
  ...mockFullProject1,
  gpuAllocationPercentage: 50,
  cpuAllocationPercentage: 60,
  memoryAllocationPercentage: 55,
  gpuAllocationExceeded: false,
  cpuAllocationExceeded: false,
  memoryAllocationExceeded: false,
};

export const mockProjectWithAllocation2: ProjectWithResourceAllocation = {
  ...mockFullProject2,
  gpuAllocationPercentage: 75,
  cpuAllocationPercentage: 80,
  memoryAllocationPercentage: 70,
  gpuAllocationExceeded: false,
  cpuAllocationExceeded: false,
  memoryAllocationExceeded: false,
};

/**
 * Mock response for fetchProjects API call.
 */
export const mockProjectsResponse: ProjectsResponse = {
  projects: [mockProjectWithAllocation1, mockProjectWithAllocation2],
};
