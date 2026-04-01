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
        gpu_id: '0',
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
        gpu_id: '1',
        metric: {
          values: [{ timestamp: '2024-01-01T00:00:00Z', value: 30 }],
        },
      },
      {
        gpu_id: '0',
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

  it('sorts devices by gpu_id and timestamps chronologically', () => {
    const devices = [
      {
        gpu_id: '2',
        metric: {
          values: [{ timestamp: '2024-01-01T00:10:00Z', value: 100 }],
        },
      },
      {
        gpu_id: '0',
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
    const devices = [{ gpu_id: '0' }];

    const result = mergeGpuDeviceTimeseriesToChartData(devices);

    expect(result).toEqual([]);
  });
});

describe('normalizeNodeGpuUtilizationResponse', () => {
  it('passes through snake_case gpu_devices directly', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpu_devices: [
        {
          gpu_uuid: 'uuid-1',
          gpu_id: '0',
          hostname: 'node-1',
          metric: {
            series_label: 'gpu_activity_pct',
            values: [{ timestamp: '2024-01-01T00:00:00Z', value: 50 }],
          },
        },
      ],
      range: { start: '2024-01-01T00:00:00Z', end: '2024-01-01T01:00:00Z' },
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpu_devices).toBe(raw.gpu_devices);
    expect(result.range).toEqual({
      start: '2024-01-01T00:00:00Z',
      end: '2024-01-01T01:00:00Z',
    });
  });

  it('defaults range to empty strings when gpu_devices present but range missing', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpu_devices: [
        {
          gpu_uuid: 'uuid-1',
          gpu_id: '0',
          hostname: 'node-1',
          metric: {
            series_label: 'gpu_activity_pct',
            values: [],
          },
        },
      ],
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.range).toEqual({ start: '', end: '' });
  });

  it('normalizes camelCase gpuDevices to snake_case', () => {
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

    expect(result.gpu_devices).toEqual([
      {
        gpu_uuid: 'uuid-2',
        gpu_id: '1',
        hostname: 'node-2',
        metric: {
          series_label: 'custom_metric',
          values: [{ timestamp: '2024-01-01T00:00:00Z', value: 75 }],
        },
      },
    ]);
  });

  it('defaults seriesLabel to gpu_activity_pct when metric exists without seriesLabel', () => {
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

    expect(result.gpu_devices[0].metric.series_label).toBe('gpu_activity_pct');
    expect(result.gpu_devices[0].metric.values).toHaveLength(1);
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

    expect(result.gpu_devices[0].metric).toEqual({
      series_label: 'gpu_activity_pct',
      values: [],
    });
  });

  it('handles empty gpuDevices array', () => {
    const raw: NodeGpuUtilizationRawResponse = {
      gpuDevices: [],
      range: { start: '2024-01-01T00:00:00Z', end: '2024-01-01T01:00:00Z' },
    };

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpu_devices).toEqual([]);
  });

  it('handles missing gpuDevices by defaulting to empty array', () => {
    const raw: NodeGpuUtilizationRawResponse = {};

    const result = normalizeNodeGpuUtilizationResponse(raw);

    expect(result.gpu_devices).toEqual([]);
    expect(result.range).toEqual({ start: '', end: '' });
  });
});
