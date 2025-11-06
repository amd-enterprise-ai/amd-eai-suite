// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getProjectSecrets, getSecrets } from '@/services/server/secrets';

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';

vi.mock('@/utils/app/api-helpers', () => ({
  convertSnakeToCamel: vi.fn((data) => ({ ...data, camelCased: true })),
  getErrorMessage: vi.fn(async (response) => 'error message'),
}));

const OLD_ENV = process.env;

describe('secrets service', () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...OLD_ENV, AIRM_API_SERVICE_URL: 'http://test-url' };
  });

  afterEach(() => {
    process.env = OLD_ENV;
    vi.restoreAllMocks();
  });

  describe('getSecrets', () => {
    it('should fetch secrets and convert response', async () => {
      const mockJson = { secret_key: 'value' };
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockJson),
      } as any);

      const result = await getSecrets('token123');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-url/v1/secrets',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer token123',
            'Content-Type': 'application/json',
          }),
        }),
      );
      expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
      expect(result).toEqual({ ...mockJson, camelCased: true });
    });

    it('should throw error if response not ok', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
      } as any);

      await expect(getSecrets('token123')).rejects.toThrow(
        'Failed to get secrets: error message',
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('getProjectSecrets', () => {
    it('should fetch project secrets and convert response', async () => {
      const mockJson = { project_secret: 'value' };
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockJson),
      } as any);

      const result = await getProjectSecrets('token456', 'project789');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-url/v1/projects/project789/secrets',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer token456',
            'Content-Type': 'application/json',
          }),
        }),
      );
      expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
      expect(result).toEqual({ ...mockJson, camelCased: true });
    });

    it('should throw error if response not ok', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
      } as any);

      await expect(getProjectSecrets('token456', 'project789')).rejects.toThrow(
        'Failed to get project secrets: error message',
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });
});
