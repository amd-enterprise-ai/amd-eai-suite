// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  getChartColorBg,
  getColorForGpuUuid,
  filterGpuDevicesBySelection,
  getGpuChartCategories,
  getGpuChartColors,
} from '@/utils/cluster-nodes';
import {
  ALL_DEVICES_KEY,
  GPU_LINE_CHART_COLORS,
} from '@/constants/clusters/nodeDetail';
import type { NodeGpuUtilizationResponse } from '@/types/clusters';

type GpuDevice = NodeGpuUtilizationResponse['gpuDevices'][number];

function makeDevice(gpuId: string, gpuUuid: string): GpuDevice {
  return {
    gpuId,
    gpuUuid,
    hostname: 'node-1',
    metric: { seriesLabel: 'gpuActivityPct', values: [] },
  };
}

describe('getChartColorBg', () => {
  it('returns the bg class for a known color key', () => {
    expect(getChartColorBg('blue')).toBe('bg-blue-500');
  });

  it('returns bg-gray-500 as fallback for an unknown color key', () => {
    expect(getChartColorBg('unknown' as any)).toBe('bg-gray-500');
  });
});

describe('getColorForGpuUuid', () => {
  const palette = GPU_LINE_CHART_COLORS;

  it('returns the palette entry matching the gpu color map index', () => {
    const map = new Map([
      ['uuid-0', 0],
      ['uuid-1', 1],
    ]);
    expect(getColorForGpuUuid('uuid-0', map, palette)).toBe(palette[0]);
    expect(getColorForGpuUuid('uuid-1', map, palette)).toBe(palette[1]);
  });

  it('defaults to index 0 when the uuid is not in the map', () => {
    const map = new Map<string, number>();
    expect(getColorForGpuUuid('unknown-uuid', map, palette)).toBe(palette[0]);
  });

  it('wraps around when the index exceeds the palette length', () => {
    const map = new Map([['uuid-wrap', palette.length]]);
    expect(getColorForGpuUuid('uuid-wrap', map, palette)).toBe(palette[0]);
  });
});

describe('filterGpuDevicesBySelection', () => {
  const devices = [
    makeDevice('0', 'uuid-0'),
    makeDevice('1', 'uuid-1'),
    makeDevice('2', 'uuid-2'),
  ];

  it('returns all devices when selection contains ALL_DEVICES_KEY', () => {
    const selection = new Set([ALL_DEVICES_KEY]);
    expect(filterGpuDevicesBySelection(devices, selection)).toEqual(devices);
  });

  it('returns all devices when selection is empty', () => {
    const selection = new Set<string>();
    expect(filterGpuDevicesBySelection(devices, selection)).toEqual(devices);
  });

  it('filters to only devices matching the selected gpu keys', () => {
    const selection = new Set(['gpu-1', 'gpu-3']);
    const result = filterGpuDevicesBySelection(devices, selection);
    expect(result).toHaveLength(2);
    expect(result.map((d) => d.gpuId)).toEqual(['0', '2']);
  });

  it('returns empty array when no devices match the selection', () => {
    const selection = new Set(['gpu-99']);
    expect(filterGpuDevicesBySelection(devices, selection)).toEqual([]);
  });
});

describe('getGpuChartCategories', () => {
  it('returns gpu-N labels sorted by numeric gpu_id', () => {
    const devices = [
      makeDevice('2', 'uuid-2'),
      makeDevice('0', 'uuid-0'),
      makeDevice('1', 'uuid-1'),
    ];
    expect(getGpuChartCategories(devices)).toEqual(['gpu-1', 'gpu-2', 'gpu-3']);
  });

  it('returns an empty array for empty input', () => {
    expect(getGpuChartCategories([])).toEqual([]);
  });
});

describe('getGpuChartColors', () => {
  it('returns colors sorted by gpu_id, each resolved via the color map', () => {
    const devices = [makeDevice('1', 'uuid-1'), makeDevice('0', 'uuid-0')];
    const gpuColorMap = new Map([
      ['uuid-0', 0],
      ['uuid-1', 1],
    ]);
    const result = getGpuChartColors(devices, gpuColorMap);
    expect(result).toEqual([
      GPU_LINE_CHART_COLORS[0],
      GPU_LINE_CHART_COLORS[1],
    ]);
  });

  it('returns an empty array for empty input', () => {
    expect(getGpuChartColors([], new Map())).toEqual([]);
  });
});
