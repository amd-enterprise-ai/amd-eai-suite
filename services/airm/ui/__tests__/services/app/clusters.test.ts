// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  addCluster,
  deleteCluster,
  editCluster,
  fetchClusterStatistics,
  fetchClusters,
  getCluster,
  getClusterNodes,
} from '@/services/app/clusters';

import { APIRequestError } from '@/utils/app/errors';

vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('error message'),
}));

const mockJson = vi.fn();
const mockFetch = vi.fn();

global.fetch = mockFetch as any;

beforeEach(() => {
  vi.clearAllMocks();
  mockJson.mockReset();
});

describe('clusters service', () => {
  describe('fetchClusters', () => {
    it('returns clusters on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce([{ id: '1' }]);
      const result = await fetchClusters();
      expect(result).toEqual([{ id: '1' }]);
      expect(mockFetch).toHaveBeenCalledWith('/api/clusters');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(fetchClusters()).rejects.toThrow(APIRequestError);
    });
  });

  describe('addCluster', () => {
    it('returns new cluster on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce({ id: '2' });
      const result = await addCluster();
      expect(result).toEqual({ id: '2' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/clusters',
        expect.objectContaining({
          method: 'POST',
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(addCluster()).rejects.toThrow(APIRequestError);
    });
  });

  describe('getCluster', () => {
    it('returns cluster on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce({ id: '3' });
      const result = await getCluster('3');
      expect(result).toEqual({ id: '3' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/clusters/3',
        expect.any(Object),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(getCluster('3')).rejects.toThrow(APIRequestError);
    });
  });

  describe('deleteCluster', () => {
    it('returns response on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      const result = await deleteCluster('4');
      expect(result).toEqual({ ok: true });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/clusters/4',
        expect.any(Object),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 403 });
      await expect(deleteCluster('4')).rejects.toThrow(APIRequestError);
    });
  });

  describe('editCluster', () => {
    it('returns response on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      const data = { name: 'new' };
      const result = await editCluster('5', data as any);
      expect(result).toEqual({ ok: true });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/clusters/5',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(data),
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 422 });
      await expect(editCluster('5', {} as any)).rejects.toThrow(
        APIRequestError,
      );
    });
  });

  describe('getClusterNodes', () => {
    it('returns nodes on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce([{ node: 'n1' }]);
      const result = await getClusterNodes('6');
      expect(result).toEqual([{ node: 'n1' }]);
      expect(mockFetch).toHaveBeenCalledWith('/api/clusters/6/nodes');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(getClusterNodes('6')).rejects.toThrow(APIRequestError);
    });
  });

  describe('fetchClusterStatistics', () => {
    it('returns stats on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce({ stats: 'value' });
      const result = await fetchClusterStatistics();
      expect(result).toEqual({ stats: 'value' });
      expect(mockFetch).toHaveBeenCalledWith('/api/clusters/stats');
    });

    it('throws Error on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, message: 'error message' });
      await expect(fetchClusterStatistics()).rejects.toThrow(
        /^Failed to get Cluster Statistics/,
      );
    });
  });
});
