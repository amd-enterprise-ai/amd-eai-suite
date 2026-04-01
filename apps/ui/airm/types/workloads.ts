// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Workload,
  WorkloadStatus,
  WorkloadType,
  SnakeCaseKeys,
  ServerCollectionMetadata,
} from '@amdenterpriseai/types';

export type WorkloadWithMetrics = {
  id: string;
  projectId: string;
  clusterId: string;
  status: WorkloadStatus;
  displayName: string | null;
  type: WorkloadType | null;
  gpuCount: number;
  vram: number;
  runTime?: number;
  createdAt: string;
  createdBy: string;
};

export type WorkloadWithMetricsServer = SnakeCaseKeys<WorkloadWithMetrics>;

export type ProjectWorkloadsMetricsResponse = {
  data: WorkloadWithMetrics[];
} & ServerCollectionMetadata;

export type ClusterWorkloadsMetricsResponse = {
  data: WorkloadWithMetrics[];
} & ServerCollectionMetadata;

export type GpuDeviceInfo = {
  gpuId: string;
  hostname: string;
};

export type NodeWorkloadWithMetrics = {
  id: string;
  projectId: string;
  clusterId: string;
  status: WorkloadStatus;
  displayName: string | null;
  type: WorkloadType | null;
  gpuCount: number;
  vram: number;
  gpuDevices: GpuDeviceInfo[];
  createdAt: string;
  createdBy: string;
};

export type NodeWorkloadsMetricsResponse = {
  data: NodeWorkloadWithMetrics[];
};

export type WorkloadResponse = Workload & {
  projectId?: string;
  clusterId?: string;
};

export type WorkloadMetricsDetails = {
  name: string | null;
  id: string;
  createdBy: string | null;
  clusterName: string | null;
  clusterId: string;
  nodesInUse: number;
  gpuDevicesInUse: number;
  createdAt: string;
  updatedAt: string;
  queueTime: number;
  runningTime: number;
};

export type GpuDeviceMetricValue = {
  value: number;
  timestamp: string;
};

export type GpuDeviceMetricResponse = {
  gpuUuid: string;
  gpuId: string;
  hostname: string;
  metric: {
    seriesLabel: string;
    values: GpuDeviceMetricValue[];
  };
};

export type WorkloadGpuDevicesMetricsResponse = {
  gpuDevices: GpuDeviceMetricResponse[];
  range: { start: string; end: string };
};

/** Merged per-device snapshot used by the workload detail page for charting. */
export type WorkloadGpuDeviceSnapshot = {
  gpuUuid: string;
  gpuId: string;
  hostname: string;
  displayLabel?: string;
  vramUtilizationPct: number | null;
  junctionTemperatureC: number | null;
  powerUsageW: number | null;
  vramUtilizationSeries?: { time: string; value: number }[];
  junctionTemperatureSeries?: { time: string; value: number }[];
  powerUsageSeries?: { time: string; value: number }[];
};
