// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type {
  NodeGpuUtilizationRawResponse,
  NodeGpuUtilizationResponse,
} from '@/types/clusters';

export function mergeGpuDeviceTimeseriesToChartData(
  gpuDevices: {
    gpuId: string;
    metric?: { values: { timestamp: string; value: number }[] };
  }[],
): Record<string, string | number | null>[] {
  const sortedDevices = [...gpuDevices].sort(
    (a, b) => parseInt(a.gpuId, 10) - parseInt(b.gpuId, 10),
  );
  const categoryKeys = sortedDevices.map(
    (d) => `gpu-${parseInt(d.gpuId, 10) + 1}`,
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
  const gpuDevices = (raw.gpuDevices ?? []).map((d) => ({
    gpuUuid: d.gpuUuid,
    gpuId: d.gpuId,
    hostname: d.hostname,
    metric: d.metric
      ? {
          seriesLabel: d.metric.seriesLabel ?? 'gpuActivityPct',
          values: d.metric.values ?? [],
        }
      : { seriesLabel: 'gpuActivityPct', values: [] },
  }));
  const range = raw.range ?? { start: '', end: '' };
  return { gpuDevices, range };
}
