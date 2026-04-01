// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export type NodeGpuUtilizationResponse = {
  gpu_devices: {
    gpu_uuid: string;
    gpu_id: string;
    hostname: string;
    metric: {
      series_label: string;
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

/** Raw API response: backend may return camelCase or snake_case. */
export type NodeGpuUtilizationRawResponse = {
  gpu_devices?: NodeGpuUtilizationResponse['gpu_devices'];
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
