// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum GpuUtilizationTabId {
  Memory = 'memory',
  Clock = 'clock',
  GpuUsage = 'gpu-usage',
}

export enum GpuTemperatureTabId {
  Junction = 'junction',
  Memory = 'memory',
}

export enum PcieTrafficTabId {
  Bandwidth = 'bandwidth',
  Performance = 'performance',
}

export enum NodeGpuDevicesTableField {
  GPU_ID = 'gpuId',
  PRODUCT_NAME = 'productName',
  TEMPERATURE = 'temperature',
  POWER_CONSUMPTION = 'powerConsumption',
  VRAM_UTILIZATION = 'vramUtilization',
  LAST_UPDATED = 'lastUpdated',
}
