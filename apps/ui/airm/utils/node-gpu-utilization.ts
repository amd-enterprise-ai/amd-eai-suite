// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type {
  NodeGpuUtilizationRawResponse,
  NodeGpuUtilizationResponse,
} from '@/types/clusters';

export function mergeGpuDeviceTimeseriesToChartData(
  gpuDevices: {
    gpu_id: string;
    metric?: { values: { timestamp: string; value: number }[] };
  }[],
): Record<string, string | number | null>[] {
  const sortedDevices = [...gpuDevices].sort(
    (a, b) => parseInt(a.gpu_id, 10) - parseInt(b.gpu_id, 10),
  );
  const categoryKeys = sortedDevices.map(
    (d) => `gpu-${parseInt(d.gpu_id, 10) + 1}`,
  );
  const timestampToValueByCategory = categoryKeys.map((_, i) => {
    const values = sortedDevices[i]?.metric?.values ?? [];
    return new Map(values.map((v) => [v.timestamp, v.value]));
  });
  const allTimestamps = new Set<string>();
  for (const map of timestampToValueByCategory) {
    map.forEach((_, ts) => {
      allTimestamps.add(ts);
    });
  }
  const sortedTimestamps = Array.from(allTimestamps).sort(
    (a, b) => new Date(a).getTime() - new Date(b).getTime(),
  );
  return sortedTimestamps.map((ts) => {
    const point: Record<string, string | number | null> = { date: ts };
    for (let i = 0; i < categoryKeys.length; i++) {
      point[categoryKeys[i]] = timestampToValueByCategory[i].get(ts) ?? null;
    }
    return point;
  });
}

export function normalizeNodeGpuUtilizationResponse(
  raw: NodeGpuUtilizationRawResponse,
): NodeGpuUtilizationResponse {
  if (raw.gpu_devices) {
    return {
      gpu_devices: raw.gpu_devices,
      range: raw.range ?? { start: '', end: '' },
    };
  }
  const gpu_devices = (raw.gpuDevices ?? []).map((d) => ({
    gpu_uuid: d.gpuUuid,
    gpu_id: d.gpuId,
    hostname: d.hostname,
    metric: d.metric
      ? {
          series_label: d.metric.seriesLabel ?? 'gpu_activity_pct',
          values: d.metric.values ?? [],
        }
      : { series_label: 'gpu_activity_pct', values: [] },
  }));
  const range = raw.range ?? { start: '', end: '' };
  return { gpu_devices, range };
}
