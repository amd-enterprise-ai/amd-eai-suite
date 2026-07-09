// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';

import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  GET,
  PATCH,
  DELETE,
} from '@/app/api/projects/[project]/models/[modelId]/route';

const mockAuthenticateRoute = vi.fn();
const mockHandleError = vi.fn();
const mockProxyRequest = vi.fn();

vi.mock('@amdenterpriseai/utils/server', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/utils/server')>();
  return {
    ...actual,
    authenticateRoute: (...args: unknown[]) => mockAuthenticateRoute(...args),
    handleError: (...args: unknown[]) => mockHandleError(...args),
    proxyRequest: (...args: unknown[]) => mockProxyRequest(...args),
  };
});

const MOCK_API_SERVICE_URL = 'https://api.example.com';
const MOCK_ACCESS_TOKEN = 'mock-access-token';

beforeEach(() => {
  vi.stubEnv('AIRM_API_SERVICE_URL', MOCK_API_SERVICE_URL);
  mockAuthenticateRoute.mockResolvedValue({ accessToken: MOCK_ACCESS_TOKEN });
  mockProxyRequest.mockResolvedValue({ success: true });
  mockHandleError.mockImplementation((error: any) =>
    Response.json({ error: error.message }, { status: error.status || 500 }),
  );
});

describe('/api/projects/{project}/models/{modelId}', () => {
  it('GET proxies to upstream single-model endpoint', async () => {
    const req = new NextRequest(
      new URL(
        '/api/projects/workbench/models/my-model-id',
        'http://localhost:3000',
      ),
      { method: 'GET' },
    );
    const response = await GET(req);
    const body = await response.json();

    expect(body).toEqual({ success: true });
    expect(mockProxyRequest).toHaveBeenCalledWith(
      req,
      `${MOCK_API_SERVICE_URL}/v1/projects/workbench/models/my-model-id`,
      MOCK_ACCESS_TOKEN,
    );
  });

  it('PATCH proxies with body to upstream patch endpoint', async () => {
    const payload = { displayName: 'Updated' };
    const req = new NextRequest(
      new URL(
        '/api/projects/workbench/models/my-model-id',
        'http://localhost:3000',
      ),
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    );
    const response = await PATCH(req);
    const body = await response.json();

    expect(body).toEqual({ success: true });
    expect(mockProxyRequest).toHaveBeenCalledWith(
      req,
      `${MOCK_API_SERVICE_URL}/v1/projects/workbench/models/my-model-id`,
      MOCK_ACCESS_TOKEN,
    );
  });

  it('DELETE returns 204 with empty body when upstream has no content', async () => {
    mockProxyRequest.mockResolvedValueOnce({ status: 204 });
    const req = new NextRequest(
      new URL(
        '/api/projects/workbench/models/my-model-id',
        'http://localhost:3000',
      ),
      { method: 'DELETE' },
    );
    const response = await DELETE(req);

    expect(response.status).toBe(204);
    expect(await response.text()).toBe('');
    expect(mockProxyRequest).toHaveBeenCalledWith(
      req,
      `${MOCK_API_SERVICE_URL}/v1/projects/workbench/models/my-model-id`,
      MOCK_ACCESS_TOKEN,
    );
  });
});
