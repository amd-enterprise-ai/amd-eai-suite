// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  getCluster,
  getClusterNodes,
  getClusterProjects,
  getClusterStats,
  getClusters,
} from '@/services/server/clusters';

const mockAccessToken = 'test-token';
const mockClusterId = 'cluster-1';

vi.mock('@/utils/app/api-helpers', () => ({
  convertSnakeToCamel: vi.fn((data) => ({ ...data, converted: true })),
  getErrorMessage: vi.fn(async (response) => 'error-message'),
}));

const mockJson = vi.fn();
const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
  mockJson.mockClear();
  mockFetch.mockClear();
  process.env.AIRM_API_SERVICE_URL = 'http://test-api';
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('clusters service', () => {
  it('getClusters returns converted data on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue({ foo: 'bar' }),
    });
    const result = await getClusters(mockAccessToken);
    expect(result).toEqual(expect.objectContaining({ converted: true }));
    expect(mockFetch).toHaveBeenCalledWith(
      'http://test-api/v1/clusters',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: `Bearer ${mockAccessToken}`,
        }),
      }),
    );
  });

  it('getClusters throws error on failure', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(getClusters(mockAccessToken)).rejects.toThrow(
      /Failed to get clusters: error-message/,
    );
  });

  it('getCluster returns converted data on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue({ id: mockClusterId }),
    });
    const result = await getCluster(mockClusterId, mockAccessToken);
    expect(result).toEqual(expect.objectContaining({ converted: true }));
    expect(mockFetch).toHaveBeenCalledWith(
      `http://test-api/v1/clusters/${mockClusterId}`,
      expect.anything(),
    );
  });

  it('getCluster throws error on failure', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(getCluster(mockClusterId, mockAccessToken)).rejects.toThrow(
      /Failed to get cluster: error-message/,
    );
  });

  it('getClusterNodes returns converted data on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue({ nodes: [] }),
    });
    const result = await getClusterNodes(mockClusterId, mockAccessToken);
    expect(result).toEqual(expect.objectContaining({ converted: true }));
    expect(mockFetch).toHaveBeenCalledWith(
      `http://test-api/v1/clusters/${mockClusterId}/nodes`,
      expect.anything(),
    );
  });

  it('getClusterNodes throws error on failure', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(
      getClusterNodes(mockClusterId, mockAccessToken),
    ).rejects.toThrow(/Failed to get cluster nodes: error-message/);
  });

  it('getClusterProjects returns converted data on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue({ projects: [] }),
    });
    const result = await getClusterProjects(mockClusterId, mockAccessToken);
    expect(result).toEqual(expect.objectContaining({ converted: true }));
    expect(mockFetch).toHaveBeenCalledWith(
      `http://test-api/v1/clusters/${mockClusterId}/projects`,
      expect.anything(),
    );
  });

  it('getClusterProjects throws error on failure', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(
      getClusterProjects(mockClusterId, mockAccessToken),
    ).rejects.toThrow(/Failed to get cluster quota: error-message/);
  });

  it('getClusterStats returns converted data on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: mockJson.mockResolvedValue({ stats: {} }),
    });
    const result = await getClusterStats(mockAccessToken);
    expect(result).toEqual(expect.objectContaining({ converted: true }));
    expect(mockFetch).toHaveBeenCalledWith(
      'http://test-api/v1/clusters/stats',
      expect.anything(),
    );
  });

  it('getClusterStats throws error on failure', async () => {
    mockFetch.mockResolvedValue({ ok: false });
    await expect(getClusterStats(mockAccessToken)).rejects.toThrow(
      /Failed to get cluster: error-message/,
    );
  });
});
