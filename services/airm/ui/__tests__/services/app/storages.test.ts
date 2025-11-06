// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  createStorage,
  deleteProjectStorage,
  deleteStorage,
  fetchProjectStorages,
  fetchStorages,
  updateStorageAssignment,
} from '@/services/app/storages';
import { getProjectStorages } from '@/services/server/storages';

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('error message'),
  convertSnakeToCamel: vi.fn((data) => data),
}));

const mockJson = vi.fn();
const mockFetch = vi.fn();

global.fetch = mockFetch as any;

describe('storages service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockJson.mockReset();
  });

  describe('fetchStorages', () => {
    it('returns storages on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce([{ id: '1' }]);
      const result = await fetchStorages();
      expect(result).toEqual([{ id: '1' }]);
      expect(mockFetch).toHaveBeenCalledWith('/api/storages');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(fetchStorages()).rejects.toThrow(APIRequestError);
    });
  });

  describe('fetchProjectStorages', () => {
    it('returns project storages on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce([{ id: '2' }]);
      const result = await fetchProjectStorages('proj1');
      expect(result).toEqual([{ id: '2' }]);
      expect(mockFetch).toHaveBeenCalledWith('/api/projects/proj1/storages');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(fetchProjectStorages('proj1')).rejects.toThrow(
        APIRequestError,
      );
    });
  });

  describe('deleteProjectStorage', () => {
    it('calls fetch with DELETE method', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await deleteProjectStorage('proj1', 'stor1');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/storages/stor1',
        { method: 'DELETE' },
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(deleteProjectStorage('proj1', 'stor1')).rejects.toThrow(
        APIRequestError,
      );
    });
  });

  describe('createStorage', () => {
    it('creates storage and returns result', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce({ id: 'new' });
      const req = { name: 'test' } as any;
      const result = await createStorage(req);
      expect(result).toEqual({ id: 'new' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/storages',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req),
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 422 });
      await expect(createStorage({} as any)).rejects.toThrow(APIRequestError);
    });
  });

  describe('updateStorageAssignment', () => {
    it('updates assignment and returns result', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce({ success: true });
      const req = { assigned: true } as any;
      const result = await updateStorageAssignment('req1', req);
      expect(result).toEqual({ success: true });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/storages/req1/assign',
        expect.objectContaining({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req),
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 403 });
      await expect(updateStorageAssignment('req1', {} as any)).rejects.toThrow(
        APIRequestError,
      );
    });
  });

  describe('deleteStorage', () => {
    it('calls fetch with DELETE method', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await deleteStorage('stor2');
      expect(mockFetch).toHaveBeenCalledWith('/api/storages/stor2', {
        method: 'DELETE',
      });
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(deleteStorage('stor2')).rejects.toThrow(APIRequestError);
    });
  });

  describe('getProjectStorages', () => {
    const mockFetch = vi.fn();
    const mockJson = vi.fn();

    beforeAll(() => {
      global.fetch = mockFetch as any;
    });

    beforeEach(() => {
      vi.clearAllMocks();
      mockFetch.mockReset();
      mockJson.mockReset();
      (convertSnakeToCamel as any).mockClear();
      (getErrorMessage as any).mockClear();
    });

    it('returns converted project storages on success', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: mockJson });
      mockJson.mockResolvedValueOnce([{ id: 'projStor1' }]);
      const result = await getProjectStorages('token123', 'proj1');
      expect(result).toEqual([{ id: 'projStor1' }]);
      expect(mockFetch).toHaveBeenCalledWith(
        `${process.env.AIRM_API_SERVICE_URL}/v1/projects/proj1/storages`,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer token123',
          },
        },
      );
      expect(convertSnakeToCamel).toHaveBeenCalledWith([{ id: 'projStor1' }]);
    });

    it('throws error with message on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(getProjectStorages('token123', 'proj1')).rejects.toThrow(
        /^Failed to get project storages/,
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });
});
