// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterStatus } from '@/types/enums/cluster-status';
import { ProjectStatus } from '@/types/enums/projects';
import { QuotaStatus } from '@/types/enums/quotas';
import {
  ProjectWithMembers,
  ProjectWithResourceAllocation,
} from '@/types/projects';

export const generateMockProjects = (
  count: number,
): ProjectWithResourceAllocation[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: (i + 1).toString(),
    name: 'project-' + (i + 1),
    description: 'Project description',
    status: ProjectStatus.READY,
    statusReason: null,
    clusterId: 'cluster-1',
    quota: {
      status: QuotaStatus.PENDING,
      cpuMilliCores: 2000,
      gpuCount: 8,
      memoryBytes: 26843545600,
      ephemeralStorageBytes: 107374182400,
    },
    cluster: {
      id: '1',
      name: 'cluster-1',
      lastHeartbeatAt: '2025-03-11T23:24:03.733668Z',
      status: ClusterStatus.HEALTHY,
    },
    gpuAllocationPercentage: 100.0,
    cpuAllocationPercentage: 25.0,
    memoryAllocationPercentage: 50.0,
    gpuAllocationExceeded: false,
    cpuAllocationExceeded: false,
    memoryAllocationExceeded: false,
  }));
};

export const generateMockProjectWithMembers = (
  userCount: number,
  invitedUserCount: number,
): ProjectWithMembers => {
  return {
    ...generateMockProjects(1)[0],
    users: Array.from({ length: userCount }, (_, i) => ({
      id: (i + 1).toString(),
      firstName: `${(i + 1).toString()} First`,
      lastName: `${(i + 1).toString()} Last`,
      role: 'Team Member',
      email: `${(i + 1).toString()}@example.com`,
    })),
    invitedUsers: Array.from({ length: invitedUserCount }, (_, i) => ({
      id: `i${i + 1}`,
      email: `${(i + 1).toString()}@example.com`,
      role: 'Team Member',
    })),
  };
};
