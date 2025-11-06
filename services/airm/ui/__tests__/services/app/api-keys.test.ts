// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  createApiKey,
  deleteApiKey,
  fetchProjectApiKeys,
} from '@/services/app/api-keys';

import { APIRequestError } from '@/utils/app/errors';

import {
  generateMockApiKeyResponse,
  generateMockCreateApiKeyData,
  generateMockFullApiKey,
} from '@/__mocks__/utils/api-keys-mock';

vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('error message'),
  convertCamelToSnake: vi.fn((obj) => obj), // Pass through for testing
}));

const mockJson = vi.fn();
const mockFetch = vi.fn();

globalThis.fetch = mockFetch as any;

beforeEach(() => {
  vi.clearAllMocks();
  mockJson.mockClear();
});

describe('api-keys service', () => {
  describe('fetchProjectApiKeys', () => {
    it('should fetch API keys successfully', async () => {
      const mockResponse = generateMockApiKeyResponse();

      mockJson.mockResolvedValue(mockResponse);
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      const result = await fetchProjectApiKeys('project-1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys',
      );
      expect(mockJson).toHaveBeenCalled();
      expect(result).toEqual(mockResponse);
    });

    it('should handle fetch error', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 500 });

      await expect(fetchProjectApiKeys('project-1')).rejects.toThrow(
        APIRequestError,
      );

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys',
      );
    });

    it('should handle empty API keys list', async () => {
      mockJson.mockResolvedValue({
        apiKeys: [],
      });
      mockFetch.mockResolvedValue({ ok: true, json: mockJson });

      await fetchProjectApiKeys('project-1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/projects/project-1/api-keys',
      );
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
