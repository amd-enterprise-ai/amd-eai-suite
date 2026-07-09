// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { deleteProjectSecret, fetchProjectSecrets } from '@/lib/app/secrets';

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

globalThis.fetch = mockFetch as any;

beforeEach(() => {
  vi.clearAllMocks();
  mockJson.mockClear();
});

describe('secrets service', () => {
  describe('fetchProjectSecrets', () => {
    it('should fetch a single page when total fits in one page', async () => {
      const mockData = [{ metadata: { name: 'secret-1' } }];

      mockJson.mockResolvedValue({
        data: mockData,
        pagination: { page: 1, pageSize: 100, total: mockData.length },
      });
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      const result = await fetchProjectSecrets('proj1');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets?pageSize=100&page=1',
      );
      expect(result).toEqual({ data: mockData });
    });

    it('should walk every page when total exceeds one page', async () => {
      const pageOne = Array.from({ length: 100 }, (_, i) => ({
        metadata: { name: `secret-${i}` },
      }));
      const pageTwo = Array.from({ length: 100 }, (_, i) => ({
        metadata: { name: `secret-${100 + i}` },
      }));
      const pageThree = Array.from({ length: 50 }, (_, i) => ({
        metadata: { name: `secret-${200 + i}` },
      }));

      mockFetch.mockImplementation(async (url: string) => {
        const page = new URL(url, 'http://t').searchParams.get('page');
        const data =
          page === '1' ? pageOne : page === '2' ? pageTwo : pageThree;
        return {
          ok: true,
          json: async () => ({
            data,
            pagination: { page: Number(page), pageSize: 100, total: 250 },
          }),
        };
      });

      const result = await fetchProjectSecrets('proj1');

      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets?pageSize=100&page=1',
      );
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets?pageSize=100&page=2',
      );
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets?pageSize=100&page=3',
      );
      expect(result.data).toHaveLength(250);
    });

    it('should handle empty secrets list', async () => {
      mockJson.mockResolvedValue({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      });
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      const result = await fetchProjectSecrets('proj1');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(result).toEqual({ data: [] });
    });

    it('should throw APIRequestError on failure', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 500 });

      await expect(fetchProjectSecrets('proj1')).rejects.toThrow(
        APIRequestError,
      );

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should append useCase query param when useCase is provided', async () => {
      mockJson.mockResolvedValue({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      });
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      await fetchProjectSecrets('proj1', 'ImagePullSecret');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets?pageSize=100&page=1&useCase=ImagePullSecret',
      );
    });

    it('should not append useCase query param when useCase is omitted', async () => {
      mockJson.mockResolvedValue({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      });
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      await fetchProjectSecrets('proj1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets?pageSize=100&page=1',
      );
    });

    it('should throw APIRequestError when projectId is empty', async () => {
      await expect(fetchProjectSecrets('')).rejects.toThrow(APIRequestError);
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('deleteProjectSecret', () => {
    it('calls fetch with DELETE and succeeds', async () => {
      mockFetch.mockResolvedValue({ ok: true });
      await expect(
        deleteProjectSecret('proj1', 'sec1'),
      ).resolves.toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/proj1/secrets/sec1',
        { method: 'DELETE' },
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 400 });
      await expect(deleteProjectSecret('proj1', 'sec1')).rejects.toThrow(
        APIRequestError,
      );
    });
  });
});
