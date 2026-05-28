// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  mergeGpuDeviceTimeseriesToChartData,
  normalizeNodeGpuUtilizationResponse,
} from '@/utils/node-gpu-utilization';
import type { NodeGpuUtilizationRawResponse } from '@/types/clusters';

describe('mergeGpuDeviceTimeseriesToChartData', () => {
  it('returns empty array for empty devices', () => {
    expect(mergeGpuDeviceTimeseriesToChartData([])).toEqual([]);
  });

  it('merges single device timeseries into chart points', () => {
    const devices = [
      {
        gpuId: '0',
        metric: {
          values: [
            { timestamp: '2024-01-01T00:00:00Z', value: 50 },
            { timestamp: '2024-01-01T00:05:00Z', value: 75 },
          ],
        },
      },
    ];

    const result = mergeGpuDeviceTimeseriesToChartData(devices);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ date: '2024-01-01T00:00:00Z', 'gpu-1': 50 });
    expect(result[1]).toEqual({ date: '2024-01-01T00:05:00Z', 'gpu-1': 75 });
  });

  it('merges multiple devices and fills null for missing timestamps', () => {
    const devices = [
      {
        gpuId: '1',
        metric: {
          values: [{ timestamp: '2024-01-01T00:00:00Z', value: 30 }],
        },
      },
      {
        gpuId: '0',
        metric: {
          values: [
            { timestamp: '2024-01-01T00:00:00Z', value: 50 },
            { timestamp: '2024-01-01T00:05:00Z', value: 60 },
          ],
        },
      },
    ];

    const result = mergeGpuDeviceTimeseriesToChartData(devices);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      date: '2024-01-01T00:00:00Z',
      'gpu-1': 50,
      'gpu-2': 30,
    });
    expect(result[1]).toEqual({
      date: '2024-01-01T00:05:00Z',
      'gpu-1': 60,
      'gpu-2': null,
    });
  });

  it('sorts devices by gpuId and timestamps chronologically', () => {
    const devices = [
      {
        gpuId: '2',
        metric: {
          values: [{ timestamp: '2024-01-01T00:10:00Z', value: 100 }],
        },
      },
      {
        gpuId: '0',
        metric: {
          values: [{ timestamp: '2024-01-01T00:05:00Z', value: 200 }],
        },
      },
    ];

    const result = mergeGpuDeviceTimeseriesToChartData(devices);

    expect(result).toHaveLength(2);
    expect(result[0].date).toBe('2024-01-01T00:05:00Z');
    expect(result[1].date).toBe('2024-01-01T00:10:00Z');
    expect(Object.keys(result[0]).filter((k) => k !== 'date')).toEqual([
      'gpu-1',
      'gpu-3',
    ]);
  });

  it('handles device with no metric', () => {
    const devices = [{ gpuId: '0' }];

    const result = mergeGpuDeviceTimeseriesToChartData(devices);

    expect(result).toEqual([]);
  });
});

describe('normalizeNodeGpuUtilizationResponse', () => {
  it('normalizes gpuDevices and preserves all fields', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpuDevices: [
        {
          gpuUuid: 'uuid-1',
          gpuId: '0',
          hostname: 'node-1',
          metric: {
            seriesLabel: 'gpuActivityPct',
            values: [{ timestamp: '2024-01-01T00:00:00Z', value: 50 }],
          },
        },
      ],
      range: { start: '2024-01-01T00:00:00Z', end: '2024-01-01T01:00:00Z' },
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpuDevices).toEqual([
      {
        gpuUuid: 'uuid-1',
        gpuId: '0',
        hostname: 'node-1',
        metric: {
          seriesLabel: 'gpuActivityPct',
          values: [{ timestamp: '2024-01-01T00:00:00Z', value: 50 }],
        },
      },
    ]);
    expect(result.range).toEqual({
      start: '2024-01-01T00:00:00Z',
      end: '2024-01-01T01:00:00Z',
    });
  });

  it('defaults range to empty strings when gpuDevices present but range missing', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpuDevices: [
        {
          gpuUuid: 'uuid-1',
          gpuId: '0',
          hostname: 'node-1',
          metric: {
            seriesLabel: 'gpuActivityPct',
            values: [],
          },
        },
      ],
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpuDevices).toHaveLength(1);
    expect(result.range).toEqual({ start: '', end: '' });
  });

  it('normalizes camelCase gpuDevices with custom metric label', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpuDevices: [
        {
          gpuUuid: 'uuid-2',
          gpuId: '1',
          hostname: 'node-2',
          metric: {
            seriesLabel: 'custom_metric',
            values: [{ timestamp: '2024-01-01T00:00:00Z', value: 75 }],
          },
        },
      ],
      range: { start: '2024-01-01T00:00:00Z', end: '2024-01-01T01:00:00Z' },
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpuDevices).toEqual([
      {
        gpuUuid: 'uuid-2',
        gpuId: '1',
        hostname: 'node-2',
        metric: {
          seriesLabel: 'custom_metric',
          values: [{ timestamp: '2024-01-01T00:00:00Z', value: 75 }],
        },
      },
    ]);
  });

  it('defaults seriesLabel to gpuActivityPct when metric exists without seriesLabel', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpuDevices: [
        {
          gpuUuid: 'uuid-3',
          gpuId: '2',
          hostname: 'node-3',
          metric: {
            values: [{ timestamp: '2024-01-01T00:00:00Z', value: 30 }],
          },
        },
      ],
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpuDevices[0].metric.seriesLabel).toBe('gpuActivityPct');
    expect(result.gpuDevices[0].metric.values).toHaveLength(1);
  });

  it('provides empty metric when device has no metric field', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpuDevices: [
        {
          gpuUuid: 'uuid-4',
          gpuId: '3',
          hostname: 'node-4',
        },
      ],
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpuDevices[0].metric).toEqual({
      seriesLabel: 'gpuActivityPct',
      values: [],
    });
  });

  it('handles empty gpuDevices array', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpuDevices: [],
      range: { start: '2024-01-01T00:00:00Z', end: '2024-01-01T01:00:00Z' },
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpuDevices).toEqual([]);
  });

  it('handles missing gpuDevices by defaulting to empty array', () => {
    const raw: NodeGpuUtilizationRawResponse = {};

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpuDevices).toEqual([]);
    expect(result.range).toEqual({ start: '', end: '' });
  });
});
