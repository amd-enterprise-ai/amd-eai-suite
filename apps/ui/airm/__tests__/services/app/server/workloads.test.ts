// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getClusterWorkloadsStats } from '@/services/server';

import {
  convertSnakeToCamel,
  getErrorMessage,
} from '@amdenterpriseai/utils/app';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@amdenterpriseai/utils/app', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/utils/app')>();
  return {
    ...actual,
    convertSnakeToCamel: vi.fn((x) => x),
    getErrorMessage: vi.fn(async () => 'error message'),
  };
});

const OLD_ENV = process.env;

describe('workloads server service', () => {
  beforeEach(() => {
    vi.resetModules();
    global.fetch = vi.fn();
    process.env = { ...OLD_ENV, AIRM_API_SERVICE_URL: 'http://test-api' };
  });

  afterEach(() => {
    vi.clearAllMocks();
    process.env = OLD_ENV;
  });

  describe('getClusterWorkloadsStats', () => {
    it('returns workload stats on success', async () => {
      const mockJson = {
        name: 'Test Cluster',
        totalWorkloads: 15,
        statusCounts: [
          { status: 'Running', count: 5 },
          { status: 'Pending', count: 3 },
          { status: 'Complete', count: 7 },
        ],
      };
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockJson),
      });
      const result = await getClusterWorkloadsStats('cluster-123', 'token');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api/v1/clusters/cluster-123/workloads/stats',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer token',
          }),
        }),
      );
      expect(result).toEqual(mockJson);
      expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
    });

    it('throws error on failure', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        json: vi.fn(),
      });
      await expect(
        getClusterWorkloadsStats('cluster-123', 'token'),
      ).rejects.toThrow('Failed to get cluster workload stats: error message');
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });
});
