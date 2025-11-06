// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  createSecret,
  deleteProjectSecret,
  deleteSecret,
  fetchProjectSecrets,
  fetchSecrets,
  updateSecretAssignment,
} from '@/services/app/secrets';

import { getErrorMessage } from '@/utils/app/api-helpers';
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

describe('secrets service', () => {
  describe('fetchSecrets', () => {
    it('returns secrets on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce([{ id: '1' }]),
      });
      const result = await fetchSecrets();
      expect(result).toEqual([{ id: '1' }]);
      expect(mockFetch).toHaveBeenCalledWith('/api/secrets');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(fetchSecrets()).rejects.toThrow(APIRequestError);
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('fetchProjectSecrets', () => {
    it('returns project secrets on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce([{ id: '2' }]),
      });
      const result = await fetchProjectSecrets('proj1');
      expect(result).toEqual([{ id: '2' }]);
      expect(mockFetch).toHaveBeenCalledWith('/api/projects/proj1/secrets');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(fetchProjectSecrets('proj1')).rejects.toThrow(
        APIRequestError,
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('deleteProjectSecret', () => {
    it('calls fetch with DELETE and succeeds', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await expect(
        deleteProjectSecret('proj1', 'sec1'),
      ).resolves.toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets/sec1',
        { method: 'DELETE' },
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(deleteProjectSecret('proj1', 'sec1')).rejects.toThrow(
        APIRequestError,
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('createSecret', () => {
    it('creates secret and returns result', async () => {
      const req = { name: 'test', value: 'val' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce({ id: 'new' }),
      });
      const result = await createSecret(req as any);
      expect(result).toEqual({ id: 'new' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/secrets',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(req),
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 403 });
      await expect(createSecret({} as any)).rejects.toThrow(APIRequestError);
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('updateSecretAssignment', () => {
    it('updates assignment and returns result', async () => {
      const req = { projectId: 'p', secretId: 's' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce({ assigned: true }),
      });
      const result = await updateSecretAssignment('id1', req as any);
      expect(result).toEqual({ assigned: true });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/secrets/id1/assign',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(req),
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(updateSecretAssignment('id1', {} as any)).rejects.toThrow(
        APIRequestError,
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('deleteSecret', () => {
    it('calls fetch with DELETE and succeeds', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await expect(deleteSecret('sec1')).resolves.toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith('/api/secrets/sec1', {
        method: 'DELETE',
      });
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(deleteSecret('sec1')).rejects.toThrow(APIRequestError);
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });
});
