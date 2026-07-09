// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { afterEach, beforeEach, describe, expect, it, Mock, vi } from 'vitest';

import {
  deleteInferenceDeployment,
  deployInference,
  getInferenceDeployment,
  getInferenceModel,
  listAllInferenceDeployments,
  listAllInferenceModels,
  listInferenceDeployments,
  listInferenceModels,
  updateInferenceScaling,
} from '@/lib/app/inference';
import { AIMDeployPayload, AIMServiceStatus, AIMStatus } from '@/types/aims';

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

describe('getInferenceModel', () => {
  it('GETs the single model URL with URL-encoded name', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({ metadata: { name: 'aim-llama/3' } }),
    );

    await getInferenceModel('aim-llama/3');

    expect(lastCall()[0]).toBe('/api/inference/models/aim-llama%2F3');
  });

  it('rejects when name is empty', async () => {
    await expect(getInferenceModel('')).rejects.toThrow(
      /No inference model name/,
    );
  });
});

describe('listInferenceModels', () => {
  it('GETs /api/inference/models with page and pageSize params', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [{ metadata: { name: 'm1' } }],
        pagination: { page: 1, pageSize: 10, total: 1 },
      }),
    );

    await listInferenceModels();

    expect(lastCall()[0]).toBe('/api/inference/models?page=1&pageSize=10');
    expect(lastCall()[1].method).toBe('GET');
  });

  it('forwards explicit page and pageSize to the query string', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 2, pageSize: 25, total: 50 },
      }),
    );

    await listInferenceModels({ page: 2, pageSize: 25 });

    expect(lastCall()[0]).toBe('/api/inference/models?page=2&pageSize=25');
  });

  it('forwards statusFilter as repeated query params', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({ data: [], pagination: { page: 1, pageSize: 10, total: 0 } }),
    );

    await listInferenceModels({
      statusFilter: [AIMStatus.READY, AIMStatus.FAILED],
    });

    const url = lastCall()[0];
    expect(url).toContain('statusFilter=Ready');
    expect(url).toContain('statusFilter=Failed');
  });

  it('returns the paginated envelope verbatim', async () => {
    const envelope = {
      data: [{ metadata: { name: 'm1' } }],
      pagination: { page: 1, pageSize: 10, total: 1 },
    };
    mockFetch.mockResolvedValueOnce(okJson(envelope));

    const result = await listInferenceModels();

    expect(result).toEqual(envelope);
  });

  it('throws APIRequestError on non-OK response', async () => {
    mockFetch.mockResolvedValueOnce(errJson(500));

    await expect(listInferenceModels()).rejects.toThrow(
      /Failed to fetch inference models/,
    );
  });
});

describe('listAllInferenceModels', () => {
  it('GETs /api/inference/models with pageSize=100 on the first page', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      }),
    );

    await listAllInferenceModels();

    expect(lastCall()[0]).toBe('/api/inference/models?page=1&pageSize=100');
  });

  it('forwards statusFilter as repeated query params', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      }),
    );

    await listAllInferenceModels([AIMStatus.READY, AIMStatus.FAILED]);

    const url = lastCall()[0];
    expect(url).toContain('pageSize=100');
    expect(url).toContain('statusFilter=Ready');
    expect(url).toContain('statusFilter=Failed');
  });

  it('unwraps the paginated envelope to AIMClusterModel[] for a single page', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [{ metadata: { name: 'm1' } }, { metadata: { name: 'm2' } }],
        pagination: { page: 1, pageSize: 100, total: 2 },
      }),
    );

    const result = await listAllInferenceModels();

    expect(result).toEqual([
      { metadata: { name: 'm1' } },
      { metadata: { name: 'm2' } },
    ]);
  });

  it('walks subsequent pages and concatenates when total exceeds one page', async () => {
    mockFetch
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'm1' } }],
          pagination: { page: 1, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'm2' } }],
          pagination: { page: 2, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'm3' } }],
          pagination: { page: 3, pageSize: 100, total: 250 },
        }),
      );

    const result = await listAllInferenceModels();

    expect(result).toEqual([
      { metadata: { name: 'm1' } },
      { metadata: { name: 'm2' } },
      { metadata: { name: 'm3' } },
    ]);
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect((mockFetch as Mock).mock.calls[1][0]).toContain('page=2');
    expect((mockFetch as Mock).mock.calls[2][0]).toContain('page=3');
  });

  it('returns [] and does not throw on non-OK response (graceful degrade)', async () => {
    mockFetch.mockResolvedValueOnce(errJson(500));

    const result = await listAllInferenceModels();

    expect(result).toEqual([]);
  });

  it('returns [] when a subsequent page fails (graceful degrade)', async () => {
    mockFetch
      .mockResolvedValueOnce(
        okJson({
          data: [{ metadata: { name: 'm1' } }],
          pagination: { page: 1, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(errJson(500));

    const result = await listAllInferenceModels();

    expect(result).toEqual([]);
  });
});

describe('deployInference', () => {
  it('POSTs camelCase body to /api/projects/{project}/inference verbatim', async () => {
    mockFetch.mockResolvedValueOnce(okJson({ id: 'svc-1' }));

    const payload: AIMDeployPayload = {
      model: 'llama3-8b',
      hfToken: 'my-hf-secret',
      imagePullSecrets: ['s1'],
      minReplicas: 2,
      maxReplicas: 10,
      autoScaling: {
        metrics: [
          {
            type: 'PodMetric',
            podmetric: {
              metric: {
                backend: 'opentelemetry',
                metricNames: ['vllm:num_requests_waiting'],
                query: 'vllm:num_requests_waiting',
                operationOverTime: 'avg',
              },
              target: { type: 'Value', value: '5' },
            },
          },
        ],
      },
    };

    await deployInference('proj-1', payload);

    const [url, init] = lastCall();
    expect(url).toBe('/api/projects/proj-1/inference');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual(payload);
  });

  it('rejects when project is empty', async () => {
    await expect(
      deployInference('', { model: 'm' } as AIMDeployPayload),
    ).rejects.toThrow(/No project selected/);
  });
});

describe('listInferenceDeployments', () => {
  it('GETs the project list endpoint with default pageSize=10 on the first page', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 10, total: 0 },
      }),
    );

    await listInferenceDeployments('proj-1');

    expect(lastCall()[0]).toBe(
      '/api/projects/proj-1/inference?pageSize=10&page=1',
    );
  });

  it('forwards explicit page and pageSize to the query string', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 3, pageSize: 25, total: 80 },
      }),
    );

    await listInferenceDeployments('proj-1', { page: 3, pageSize: 25 });

    expect(lastCall()[0]).toBe(
      '/api/projects/proj-1/inference?pageSize=25&page=3',
    );
  });

  it('appends repeated statusFilter and capability=chat to the query', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 10, total: 0 },
      }),
    );

    await listInferenceDeployments('proj-1', {
      capability: 'chat',
      statusFilter: [AIMServiceStatus.RUNNING, AIMServiceStatus.PENDING],
    });

    const url = lastCall()[0];
    expect(url).toContain('pageSize=10');
    expect(url).toContain('page=1');
    expect(url).toContain('capability=chat');
    expect(url).toContain('statusFilter=Running');
    expect(url).toContain('statusFilter=Pending');
  });

  it('returns the paginated envelope verbatim', async () => {
    const envelope = {
      data: [{ id: 'svc-1' }, { id: 'svc-2' }],
      pagination: { page: 1, pageSize: 10, total: 2 },
    };
    mockFetch.mockResolvedValueOnce(okJson(envelope));

    const result = await listInferenceDeployments('proj-1');

    expect(result).toEqual(envelope);
  });

  it('throws APIRequestError on non-OK response', async () => {
    mockFetch.mockResolvedValueOnce(errJson(500));

    await expect(listInferenceDeployments('proj-1')).rejects.toThrow(
      /Failed to fetch inference deployments/,
    );
  });
});

describe('listAllInferenceDeployments', () => {
  it('GETs the project list endpoint with pageSize=100 on the first page', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      }),
    );

    await listAllInferenceDeployments('proj-1');

    expect(lastCall()[0]).toBe(
      '/api/projects/proj-1/inference?pageSize=100&page=1',
    );
  });

  it('appends repeated statusFilter and capability=chat to the query', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [],
        pagination: { page: 1, pageSize: 100, total: 0 },
      }),
    );

    await listAllInferenceDeployments('proj-1', {
      capability: 'chat',
      statusFilter: [AIMServiceStatus.RUNNING, AIMServiceStatus.PENDING],
    });

    const url = lastCall()[0];
    expect(url).toContain('pageSize=100');
    expect(url).toContain('page=1');
    expect(url).toContain('capability=chat');
    expect(url).toContain('statusFilter=Running');
    expect(url).toContain('statusFilter=Pending');
  });

  it('unwraps the paginated envelope to AIMService[] for a single page', async () => {
    mockFetch.mockResolvedValueOnce(
      okJson({
        data: [{ id: 'svc-1' }, { id: 'svc-2' }],
        pagination: { page: 1, pageSize: 100, total: 2 },
      }),
    );

    const result = await listAllInferenceDeployments('proj-1');

    expect(result).toEqual([{ id: 'svc-1' }, { id: 'svc-2' }]);
  });

  it('walks subsequent pages and concatenates when total exceeds one page', async () => {
    mockFetch
      .mockResolvedValueOnce(
        okJson({
          data: [{ id: 'svc-1' }],
          pagination: { page: 1, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(
        okJson({
          data: [{ id: 'svc-2' }],
          pagination: { page: 2, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(
        okJson({
          data: [{ id: 'svc-3' }],
          pagination: { page: 3, pageSize: 100, total: 250 },
        }),
      );

    const result = await listAllInferenceDeployments('proj-1');

    expect(result).toEqual([{ id: 'svc-1' }, { id: 'svc-2' }, { id: 'svc-3' }]);
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect((mockFetch as Mock).mock.calls[1][0]).toContain('page=2');
    expect((mockFetch as Mock).mock.calls[2][0]).toContain('page=3');
  });

  it('returns [] and does not throw on non-OK response (graceful degrade)', async () => {
    mockFetch.mockResolvedValueOnce(errJson(500));

    const result = await listAllInferenceDeployments('proj-1');

    expect(result).toEqual([]);
  });

  it('returns [] when a subsequent page fails (graceful degrade)', async () => {
    mockFetch
      .mockResolvedValueOnce(
        okJson({
          data: [{ id: 'svc-1' }],
          pagination: { page: 1, pageSize: 100, total: 250 },
        }),
      )
      .mockResolvedValueOnce(errJson(500));

    const result = await listAllInferenceDeployments('proj-1');

    expect(result).toEqual([]);
  });
});

describe('getInferenceDeployment', () => {
  it('GETs /api/projects/{project}/inference/{id}', async () => {
    mockFetch.mockResolvedValueOnce(okJson({ id: 'svc-1' }));

    await getInferenceDeployment('proj-1', 'svc-1');

    expect(lastCall()[0]).toBe('/api/projects/proj-1/inference/svc-1');
    expect(lastCall()[1].method).toBe('GET');
  });

  it('throws APIRequestError on non-OK response', async () => {
    mockFetch.mockResolvedValueOnce(errJson(404));

    await expect(getInferenceDeployment('proj-1', 'svc-1')).rejects.toThrow(
      /Failed to fetch inference deployment/,
    );
  });
});

describe('updateInferenceScaling', () => {
  it('PATCHes /api/projects/{project}/inference/{id} with full scaling payload', async () => {
    mockFetch.mockResolvedValueOnce(okJson({}));

    const payload = {
      minReplicas: 1,
      maxReplicas: 5,
      autoScaling: {
        metrics: [
          {
            type: 'PodMetric' as const,
            podmetric: {
              metric: {
                backend: 'opentelemetry' as const,
                metricNames: ['vllm:num_requests_running'],
                query: 'vllm:num_requests_running',
                operationOverTime: 'avg',
              },
              target: { type: 'Value', value: '10' },
            },
          },
        ],
      },
    };

    await updateInferenceScaling('proj-1', 'svc-1', payload);

    const [url, init] = lastCall();
    expect(url).toBe('/api/projects/proj-1/inference/svc-1');
    expect(init.method).toBe('PATCH');
    expect(JSON.parse(init.body as string)).toEqual(payload);
  });
});

describe('deleteInferenceDeployment', () => {
  it('DELETEs /api/projects/{project}/inference/{id}', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: () => Promise.resolve({}),
    });

    await deleteInferenceDeployment('proj-1', 'svc-1');

    expect(lastCall()[0]).toBe('/api/projects/proj-1/inference/svc-1');
    expect(lastCall()[1].method).toBe('DELETE');
  });

  it('rejects when project or id is missing', async () => {
    await expect(deleteInferenceDeployment('', 'svc-1')).rejects.toThrow(
      /No project provided/,
    );
    await expect(deleteInferenceDeployment('proj-1', '')).rejects.toThrow(
      /No deployment ID provided/,
    );
  });
});
