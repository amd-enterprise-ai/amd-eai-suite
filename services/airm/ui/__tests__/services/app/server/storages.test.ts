// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getStorages } from '@/services/server/storages';

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';

vi.mock('@/utils/app/api-helpers', () => ({
  convertSnakeToCamel: vi.fn(),
  getErrorMessage: vi.fn(),
}));

const OLD_ENV = process.env;

describe('getStorages', () => {
  const accessToken = 'test-token';
  const apiUrl = 'https://api.example.com';
  const mockResponseData = { storages: [{ id: 1, name: 'test_storage' }] };
  const camelData = { storages: [{ id: 1, name: 'testStorage' }] };

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...OLD_ENV, AIRM_API_SERVICE_URL: apiUrl };
    vi.clearAllMocks();
  });

  it('should fetch storages and return camel-cased data on success', async () => {
    (convertSnakeToCamel as any).mockReturnValue(camelData);

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockResponseData),
    });

    const result = await getStorages(accessToken);

    expect(global.fetch).toHaveBeenCalledWith(
      `${apiUrl}/v1/storages`,
      expect.objectContaining({
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
      }),
    );
    expect(convertSnakeToCamel).toHaveBeenCalledWith(mockResponseData);
    expect(result).toEqual(camelData);
  });

  it('should throw an error with message from getErrorMessage on failure', async () => {
    const errorMsg = 'Unauthorized';
    (getErrorMessage as any).mockResolvedValue(errorMsg);

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
    });

    await expect(getStorages(accessToken)).rejects.toThrow(
      `Failed to get storages: ${errorMsg}`,
    );
    expect(getErrorMessage).toHaveBeenCalled();
  });
});
