// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterStatus } from '@/types/enums/cluster-status';
import { QuotaResource } from '@/types/enums/quotas';

export const generateClustersMock = (n: number) => {
  return Array.from({ length: n }, (_, i) => ({
    name: `cluster${i + 1}`,
    id: `cluster-${i + 1}`,
    status: ClusterStatus.HEALTHY,
    lastHeartbeatAt: '2025-03-11T23:24:03.733668Z',
    availableResources: {
      [QuotaResource.GPU]: i === 0 ? 8 : 0,
      [QuotaResource.CPU]: 8000,
      [QuotaResource.RAM]: 53687091200,
      [QuotaResource.DISK]: 107374182400,
    },
    allocatedResources: {
      [QuotaResource.GPU]: i === 0 ? 4 : 0,
      [QuotaResource.CPU]: 2000,
      [QuotaResource.RAM]: 26843545600,
      [QuotaResource.DISK]: 0,
    },
    totalNodeCount: i === 0 ? 4 : 9,
    availableNodeCount: i === 0 ? 3 : 4,
    assignedQuotaCount: 0,
    gpuInfo: {
      vendor: '',
      type: '',
      name: '',
      memoryBytesPerDevice: 0,
    },
    createdAt: '2025-03-11T23:14:03.733668Z',
    gpuAllocationPercentage: i === 0 ? 50.0 : 0.0,
    cpuAllocationPercentage: 25.0,
    memoryAllocationPercentage: 50.0,
  }));
};
