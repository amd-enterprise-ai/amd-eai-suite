// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { afterEach, beforeEach, describe, expect, it, Mock, vi } from 'vitest';

import {
  listAllProjectFineTunedModels,
  listProjectFineTunedModels,
} from '@/lib/app/models';

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  mockFetch.mockReset();
});

const lastCall = () =>
  (mockFetch as Mock).mock.calls.at(-1) as [string, RequestInit];

const okJson = (body: unknown) => ({
  ok: true,
  status: 200,
  json: () => Promise.resolve(body),
});
const errJson = (status: number) => ({
  ok: false,
  status,
  json: () => Promise.resolve({ detail: 'boom' }),
  text: () => Promise.resolve('boom'),
});

describe('listProjectFineTunedModels', () => {
  it('GETs the project fine-tuning list endpoint with default page=1/pageSize=10', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 10, total: 0 },
      }),
    );

    await listProjectFineTunedModels('proj-1');

    expect(lastCall()[0]).toBe(
      '/api/projects/proj-1/fine-tuning/models?pageSize=10&page=1',
    );
    expect(lastCall()[1].method).toBe('GET');
  });

  it('forwards explicit page and pageSize to the query string', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 3, pageSize: 25, total: 80 },
      }),
    );

    await listProjectFineTunedModels('proj-1', { page: 3, pageSize: 25 });

    expect(lastCall()[0]).toBe(
      '/api/projects/proj-1/fine-tuning/models?pageSize=25&page=3',
    );
  });

  it('returns the paginated envelope verbatim', async () => {
    const envelope = {
      data: [{ metadata: { name: 'ft-1' } }, { metadata: { name: 'ft-2' } }],
      pagination: { page: 1, pageSize: 10, total: 2 },
    };
    mockFetch.mockResolvedValueOnce(okJson(envelope));

    const result = await listProjectFineTunedModels('proj-1');

    expect(result).toEqual(envelope);
  });

  it('throws APIRequestError on non-OK response', async () => {
    mockFetch.mockResolvedValueOnce(errJson(500));

    await expect(listProjectFineTunedModels('proj-1')).rejects.toThrow(
      /Failed to get fine-tuned models/,
    );
  });
});

describe('listAllProjectFineTunedModels', () => {
  it('GETs the project fine-tuning list endpoint with pageSize=100 on the first page', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      }),
    );

    await listAllProjectFineTunedModels('proj-1');

    expect(lastCall()[0]).toBe(
      '/api/projects/proj-1/fine-tuning/models?pageSize=100&page=1',
    );
  });

  it('unwraps the paginated envelope to AIMModel[] for a single page', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [{ metadata: { name: 'ft-1' } }, { metadata: { name: 'ft-2' } }],
        pagination: { page: 1, pageSize: 100, total: 2 },
      }),
    );

    const result = await listAllProjectFineTunedModels('proj-1');

    expect(result).toEqual([
      { metadata: { name: 'ft-1' } },
      { metadata: { name: 'ft-2' } },
    ]);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('walks subsequent pages and concatenates when total exceeds one page', async () => {
    mockFetch
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'ft-1' } }],
          pagination: { page: 1, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'ft-2' } }],
          pagination: { page: 2, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'ft-3' } }],
          pagination: { page: 3, pageSize: 100, total: 250 },
        }),
      );

    const result = await listAllProjectFineTunedModels('proj-1');

    expect(result).toEqual([
      { metadata: { name: 'ft-1' } },
      { metadata: { name: 'ft-2' } },
      { metadata: { name: 'ft-3' } },
    ]);
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect((mockFetch as Mock).mock.calls[1][0]).toContain('page=2');
    expect((mockFetch as Mock).mock.calls[2][0]).toContain('page=3');
  });

  it('returns [] and does not throw on non-OK response (graceful degrade)', async () => {
    mockFetch.mockResolvedValueOnce(errJson(500));

    const result = await listAllProjectFineTunedModels('proj-1');

    expect(result).toEqual([]);
  });

  it('returns [] when a subsequent page fails (graceful degrade)', async () => {
    // total=150, pageSize=100 -> totalPages=2, so only one remaining page is fetched.
    mockFetch
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'ft-1' } }],
          pagination: { page: 1, pageSize: 100, total: 150 },
        }),
      )
      .mockResolvedValueOnce(errJson(500));

    const result = await listAllProjectFineTunedModels('proj-1');

    expect(result).toEqual([]);
  });
});
