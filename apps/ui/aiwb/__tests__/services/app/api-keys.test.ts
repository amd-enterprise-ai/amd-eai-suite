// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  createApiKey,
  deleteApiKey,
  fetchProjectApiKeys,
} from '@/lib/app/api-keys';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import {
  generateMockApiKeyResponse,
  generateMockCreateApiKeyData,
  generateMockFullApiKey,
} from '@/__mocks__/utils/api-keys-mock';

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

describe('api-keys service', () => {
  describe('fetchProjectApiKeys', () => {
    it('should fetch a single page when total fits in one page', async () => {
      const mockResponse = generateMockApiKeyResponse();

      mockJson.mockResolvedValue({
        ...mockResponse,
        pagination: { page: 1, pageSize: 100, total: mockResponse.data.length },
      });
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      const result = await fetchProjectApiKeys('project-1');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys?pageSize=100&page=1',
      );
      expect(result).toEqual({ data: mockResponse.data });
    });

    it('should walk every page when total exceeds one page', async () => {
      // Backend caps pageSize at 100; with total=250 the loader must issue
      // requests for page 1, 2, and 3 and concatenate the results.
      const pageOne = Array.from({ length: 100 }, (_, i) => ({ id: `k-${i}` }));
      const pageTwo = Array.from({ length: 100 }, (_, i) => ({
        id: `k-${100 + i}`,
      }));
      const pageThree = Array.from({ length: 50 }, (_, i) => ({
        id: `k-${200 + i}`,
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

      const result = await fetchProjectApiKeys('project-1');

      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys?pageSize=100&page=1',
      );
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys?pageSize=100&page=2',
      );
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys?pageSize=100&page=3',
      );
      expect(result.data).toHaveLength(250);
      expect(result.data[0]).toEqual({ id: 'k-0' });
      expect(result.data[249]).toEqual({ id: 'k-249' });
    });

    it('should handle fetch error', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 500 });

      await expect(fetchProjectApiKeys('project-1')).rejects.toThrow(
        APIRequestError,
      );

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys?pageSize=100&page=1',
      );
    });

    it('should handle empty API keys list', async () => {
      mockJson.mockResolvedValue({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      });
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      const result = await fetchProjectApiKeys('project-1');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys?pageSize=100&page=1',
      );
      expect(result).toEqual({ data: [] });
    });
  });

  describe('deleteApiKey', () => {
    it('should delete API key successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true });

      await deleteApiKey('project-1', 'api-key-1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys/api-key-1',
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    });

    it('should handle delete error', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 404 });

      await expect(deleteApiKey('project-1', 'api-key-1')).rejects.toThrow(
        APIRequestError,
      );

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys/api-key-1',
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    });
  });

  describe('createApiKey', () => {
    it('should create API key successfully', async () => {
      const mockResponse = generateMockFullApiKey();

      mockJson.mockResolvedValue(mockResponse);
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      const createData = generateMockCreateApiKeyData();
      const result = await createApiKey('project-1', createData);

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(createData),
        },
      );
      expect(mockJson).toHaveBeenCalled();
      expect(result).toEqual(mockResponse);
    });

    it('should handle create error', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 400 });

      const createData = generateMockCreateApiKeyData();
      await expect(createApiKey('project-1', createData)).rejects.toThrow(
        APIRequestError,
      );

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(createData),
        },
      );
    });

    it('should include the request body', async () => {
      mockJson.mockResolvedValue({});
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      const createData = generateMockCreateApiKeyData();
      await createApiKey('project-1', createData);

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys',
        expect.objectContaining({
          body: JSON.stringify(createData),
        }),
      );
    });
  });
});
