// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  fetchGPUDeviceUtilization,
  fetchGPUDeviceUtilizationByClusterId,
  fetchGPUMemoryUtilization,
  fetchUtilization,
} from '@/services/app/metrics';

vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('error message'),
}));

const mockJson = vi.fn();
const mockFetch = vi.fn();

globalThis.fetch = mockFetch as any;

beforeEach(() => {
  mockFetch.mockReset();
  mockJson.mockReset();
});

describe('fetchGPUMemoryUtilization', () => {
  it('returns data when response is ok', async () => {
    const data = { result: 'ok' };
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue(data),
    });
    const start = new Date('2024-01-01T00:00:00Z');
    const end = new Date('2024-01-02T00:00:00Z');
    const res = await fetchGPUMemoryUtilization(start, end);
    expect(res).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/metrics/gpu-memory-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
    );
  });

  it('throws error when response is not ok', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    const start = new Date();
    const end = new Date();
    await expect(fetchGPUMemoryUtilization(start, end)).rejects.toThrow(
      /Failed to get GPU Memory Utilization/,
    );
  });
});

describe('fetchGPUDeviceUtilization', () => {
  it('returns data when response is ok', async () => {
    const data = { result: 'ok' };
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue(data),
    });
    const start = new Date('2024-01-01T00:00:00Z');
    const end = new Date('2024-01-02T00:00:00Z');
    const res = await fetchGPUDeviceUtilization(start, end);
    expect(res).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/metrics/gpu-device-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
    );
  });

  it('throws error when response is not ok', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    const start = new Date();
    const end = new Date();
    await expect(fetchGPUDeviceUtilization(start, end)).rejects.toThrow(
      /^Failed to get GPU Device Utilization/,
    );
  });
});

describe('fetchUtilization', () => {
  it('returns data when response is ok', async () => {
    const data = { utilization: 42 };
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue(data),
    });
    const res = await fetchUtilization();
    expect(res).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith(`/api/metrics/utilization`);
  });

  it('throws error when response is not ok', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(fetchUtilization()).rejects.toThrow(
      /^Failed to get Metric Utilization/,
    );
  });
});

describe('fetchGPUDeviceUtilizationByClusterId', () => {
  it('returns data when response is ok', async () => {
    const data = { result: 'ok' };
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue(data),
    });
    const clusterId = 'cluster-123';
    const start = new Date('2024-01-01T00:00:00Z');
    const end = new Date('2024-01-02T00:00:00Z');
    const res = await fetchGPUDeviceUtilizationByClusterId(
      clusterId,
      start,
      end,
    );
    expect(res).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/clusters/${clusterId}/metrics/gpu-device-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
    );
  });

  it('throws error when response is not ok', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    const clusterId = 'cluster-123';
    const start = new Date();
    const end = new Date();
    await expect(
      fetchGPUDeviceUtilizationByClusterId(clusterId, start, end),
    ).rejects.toThrow(
      new RegExp(`Failed to get GPU Device Utilization for cluster`),
    );
  });
});
