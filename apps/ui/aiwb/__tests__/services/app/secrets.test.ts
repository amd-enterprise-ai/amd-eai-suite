// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { deleteProjectSecret, fetchProjectSecrets } from '@/lib/app/secrets';

import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

vi.mock('@amdenterpriseai/utils/app', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/utils/app')>();
  return {
    ...actual,
    getErrorMessage: vi.fn().mockResolvedValue('error message'),
  };
});

const mockJson = vi.fn();
const mockFetch = vi.fn();

global.fetch = mockFetch as any;

beforeEach(() => {
  vi.clearAllMocks();
  mockJson.mockReset();
});

describe('secrets service', () => {
  describe('fetchProjectSecrets', () => {
    it('returns project secrets on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce([{ id: '2' }]),
      });
      const result = await fetchProjectSecrets('proj1');
      expect(result).toEqual([{ id: '2' }]);
      expect(mockFetch).toHaveBeenCalledWith('/api/namespaces/proj1/secrets');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(fetchProjectSecrets('proj1')).rejects.toThrow(
        APIRequestError,
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });

    it('appends use_case query param when useCase is provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce({ data: [] }),
      });
      await fetchProjectSecrets('proj1', 'ImagePullSecret');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/namespaces/proj1/secrets?use_case=ImagePullSecret',
      );
    });

    it('does not append use_case query param when useCase is omitted', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce({ data: [] }),
      });
      await fetchProjectSecrets('proj1');
      expect(mockFetch).toHaveBeenCalledWith('/api/namespaces/proj1/secrets');
    });
  });

  describe('deleteProjectSecret', () => {
    it('calls fetch with DELETE and succeeds', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await expect(
        deleteProjectSecret('proj1', 'sec1'),
      ).resolves.toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/namespaces/proj1/secrets/sec1',
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
});
