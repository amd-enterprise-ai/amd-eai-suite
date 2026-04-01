// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ClusterNode,
  ClusterStatus,
  ProjectBasicInfo,
  ProjectStatus,
  WorkloadStatus,
  WorkloadType,
} from '@amdenterpriseai/types';
import { QuotaResource } from '@amdenterpriseai/types';

import type { NodeGpuUtilizationResponse } from '@/types/clusters';
import type { NodePowerUsageResponse } from '@/types/clusters';
import { NodeWorkloadWithMetrics, GpuDeviceInfo } from '@/types/workloads';

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

export const generateClusterNodesMock = (n: number): ClusterNode[] => {
  return Array.from({ length: n }, (_, i) => {
    const withGpu = i === 0;
    return {
      id: `node-${i + 1}`,
      name: withGpu ? 'gpu-m350-0001' : 'cpu-only-node',
      cpuMilliCores: withGpu ? 4000 : 16000,
      memoryBytes: withGpu ? 26843545600 : 68719476736,
      ephemeralStorageBytes: 107374182400,
      gpuCount: withGpu ? 8 : 0,
      gpuInfo: withGpu
        ? {
            vendor: 'AMD',
            type: '740c',
            memoryBytesPerDevice: 274877906944,
            name: 'Instinct M1350',
          }
        : undefined,
      updatedAt: '2025-02-19T10:23:54Z',
      status: withGpu ? 'Unhealthy' : 'Ready',
    };
  });
};

interface GpuDeviceMetricMockOptions {
  deviceCount?: number;
  valuesPerDevice?: number;
  seriesLabel?: string;
  baseValue?: number;
  fluctuation?: number;
}

function generateGpuDeviceMetricResponse(
  options: GpuDeviceMetricMockOptions = {},
): NodeGpuUtilizationResponse {
  const {
    deviceCount = 0,
    valuesPerDevice = 2,
    seriesLabel = 'gpu_activity_pct',
    baseValue = 50,
    fluctuation = 10,
  } = options;

  const now = new Date();
  const gpu_devices = Array.from({ length: deviceCount }, (_, i) => ({
    gpu_uuid: `uuid-${i}`,
    gpu_id: String(i),
    hostname: `node-${Math.floor(i / 8) + 1}`,
    metric: {
      series_label: seriesLabel,
      values: Array.from({ length: valuesPerDevice }, (_, vi) => ({
        timestamp: new Date(
          now.getTime() - (valuesPerDevice - 1 - vi) * 60_000,
        ).toISOString(),
        value:
          Math.round((baseValue + (Math.random() - 0.5) * fluctuation) * 10) /
          10,
      })),
    },
  }));

  return {
    gpu_devices,
    range: {
      start: new Date(now.getTime() - 3_600_000).toISOString(),
      end: now.toISOString(),
    },
  };
}

export function generateNodeGpuUtilizationMock(
  deviceCount = 0,
  valuesPerDevice = 2,
): NodeGpuUtilizationResponse {
  return generateGpuDeviceMetricResponse({
    deviceCount,
    valuesPerDevice,
    seriesLabel: 'gpu_activity_pct',
    baseValue: 50,
    fluctuation: 20,
  });
}

export function generateNodePowerUsageMock(
  deviceCount = 0,
  valuesPerDevice = 2,
): NodePowerUsageResponse {
  return generateGpuDeviceMetricResponse({
    deviceCount,
    valuesPerDevice,
    seriesLabel: 'power_watts',
    baseValue: 19,
    fluctuation: 5,
  });
}

export function generateNodePcieBandwidthMock(
  deviceCount = 0,
  valuesPerDevice = 2,
): NodeGpuUtilizationResponse {
  return generateGpuDeviceMetricResponse({
    deviceCount,
    valuesPerDevice,
    seriesLabel: 'pcie_bandwidth',
    baseValue: 50_000_000,
    fluctuation: 30_000_000,
  });
}

export const generateGpuDeviceMock = (
  gpuId: string,
  hostname: string,
): GpuDeviceInfo => ({
  gpuId,
  hostname,
});

const workloadTypes = [
  WorkloadType.INFERENCE,
  WorkloadType.FINE_TUNING,
  WorkloadType.WORKSPACE,
  WorkloadType.MODEL_DOWNLOAD,
];

const workloadStatuses = [
  WorkloadStatus.RUNNING,
  WorkloadStatus.PENDING,
  WorkloadStatus.FAILED,
];

export const generateNodeWorkloadsMock = (
  n: number,
  hostname: string,
): NodeWorkloadWithMetrics[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `workload-${i + 1}`,
    projectId: `project-${(i % 3) + 1}`,
    clusterId: 'cluster-1',
    status: workloadStatuses[i % workloadStatuses.length],
    displayName: `Workload ${i + 1}`,
    type: workloadTypes[i % workloadTypes.length],
    gpuCount: i + 1,
    vram: (i + 1) * 8192,
    gpuDevices: Array.from({ length: i + 1 }, (_, g) =>
      generateGpuDeviceMock(
        g.toString(),
        g === 0 ? hostname : `worker-${g + 1}`,
      ),
    ),
    createdAt: new Date(Date.UTC(2024, 0, i + 1)).toISOString(),
    createdBy: `user${i + 1}@amd.com`,
  }));
};

export const generateClusterProjectsMock = (n: number): ProjectBasicInfo[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `project-${i + 1}`,
    name: `Project ${i + 1}`,
    description: `Test project ${i + 1}`,
    status: ProjectStatus.READY,
    statusReason: null,
    clusterId: 'cluster-1',
  }));
};
