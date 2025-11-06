// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  getAims,
  getAimById,
  deployAim,
  undeployAim,
} from '@/services/app/aims';
import { APIRequestError } from '@/utils/app/errors';

vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('error message'),
  convertCamelToSnakeParams: vi.fn((params) =>
    new URLSearchParams(params).toString(),
  ),
  convertCamelToSnake: vi.fn((data) => data),
  convertSnakeToCamel: vi.fn((data) => data),
}));

vi.mock('@/utils/app/aims', () => ({
  aimsParser: vi.fn((aims) => aims),
  aimParser: vi.fn((aim) => ({ parsed: true })),
}));

const mockJson = vi.fn();
const mockFetch = vi.fn();

global.fetch = mockFetch as any;

beforeEach(() => {
  vi.clearAllMocks();
  mockJson.mockReset();
});

describe('aims service', () => {
  describe('getAims', () => {
    it('returns aims on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce([{ id: '1' }]),
      });
      const result = await getAims('proj1');
      expect(result).toEqual([{ id: '1' }]);
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(getAims('proj1')).rejects.toThrow(APIRequestError);
    });

    it('throws error when no project selected', async () => {
      await expect(getAims('')).rejects.toThrow(APIRequestError);
    });
  });

  describe('getAimById', () => {
    it('returns aim on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce({ id: 'aim1' }),
      });
      const result = await getAimById('aim1', 'proj1');
      expect(result).toHaveProperty('id', 'aim1');
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(getAimById('aim1', 'proj1')).rejects.toThrow(
        APIRequestError,
      );
    });
  });

  describe('deployAim', () => {
    it('deploys aim successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce({ success: true }),
      });
      const result = await deployAim('aim1', 'proj1', {
        cacheModel: true,
        replicas: 1,
      });
      expect(result).toEqual({ success: true });
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(
        deployAim('aim1', 'proj1', { cacheModel: true, replicas: 1 }),
      ).rejects.toThrow(APIRequestError);
    });
  });

  describe('undeployAim', () => {
    it('undeploys aim successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: mockJson.mockResolvedValueOnce({}),
      });
      const result = await undeployAim('aim1', 'proj1');
      expect(result).toEqual({});
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(undeployAim('aim1', 'proj1')).rejects.toThrow(
        APIRequestError,
      );
    });
  });
});
