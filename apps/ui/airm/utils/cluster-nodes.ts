// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type {
  AvailableChartColorsKeys,
  TimeRange,
} from '@amdenterpriseai/types';
import { chartColors } from '@amdenterpriseai/types';

import type { NodeGpuUtilizationResponse } from '@/types/clusters';
import {
  ALL_DEVICES_KEY,
  GPU_LINE_CHART_COLORS,
} from '@/constants/clusters/nodeDetail';

export function getClusterNodeQueryKeyPrefix(
  clusterId: string,
  nodeId: string,
) {
  return ['cluster', clusterId, 'node', nodeId] as const;
}

export function getClusterNodeTimeRangeQueryKeyPrefix(
  clusterId: string,
  nodeId: string,
  timeRange: TimeRange,
) {
  return [
    ...getClusterNodeQueryKeyPrefix(clusterId, nodeId),
    timeRange.start.toISOString(),
    timeRange.end.toISOString(),
  ] as const;
}

export function getChartColorBg(color: AvailableChartColorsKeys): string {
  return chartColors[color]?.bg ?? 'bg-gray-500';
}

export function getColorForGpuUuid(
  gpuUuid: string,
  gpuColorMap: Map<string, number>,
  palette: AvailableChartColorsKeys[],
): AvailableChartColorsKeys {
  const index = gpuColorMap.get(gpuUuid) ?? 0;
  return palette[index % palette.length] ?? 'gray';
}

export function filterGpuDevicesBySelection(
  devices: NodeGpuUtilizationResponse['gpuDevices'],
  selectedGpuDevices: Set<string>,
): NodeGpuUtilizationResponse['gpuDevices'] {
  const showAll =
    selectedGpuDevices.size === 0 || selectedGpuDevices.has(ALL_DEVICES_KEY);
  if (showAll) return devices;
  return devices.filter((d) => {
    const key = `gpu-${parseInt(d.gpuId, 10) + 1}`;
    return selectedGpuDevices.has(key);
  });
}

export function getGpuChartCategories(
  devices: NodeGpuUtilizationResponse['gpuDevices'],
): string[] {
  return devices
    .slice()
    .sort((a, b) => parseInt(a.gpuId, 10) - parseInt(b.gpuId, 10))
    .map((d) => `gpu-${parseInt(d.gpuId, 10) + 1}`);
}

export function getGpuChartColors(
  devices: NodeGpuUtilizationResponse['gpuDevices'],
  gpuColorMap: Map<string, number>,
): AvailableChartColorsKeys[] {
  return devices
    .slice()
    .sort((a, b) => parseInt(a.gpuId, 10) - parseInt(b.gpuId, 10))
    .map((d) =>
      getColorForGpuUuid(d.gpuUuid, gpuColorMap, GPU_LINE_CHART_COLORS),
    );
}
