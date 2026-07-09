// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';

import { beforeEach, describe, expect, it, vi } from 'vitest';

import { POST } from '@/app/api/projects/[project]/models/onboard/route';

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

function createNextRequest(path: string): NextRequest {
  return new NextRequest(new URL(path, 'http://localhost:3000'), {
    method: 'POST',
  });
}

describe('POST /api/projects/{project}/models/onboard', () => {
  it('proxies to the project-scoped upstream onboard endpoint', async () => {
    const req = createNextRequest('/api/projects/my-project/models/onboard');
    const response = await POST(req);
    const body = await response.json();

    expect(body).toEqual({ success: true });
    expect(mockProxyRequest).toHaveBeenCalledWith(
      req,
      `${MOCK_API_SERVICE_URL}/v1/projects/my-project/models/onboard`,
      MOCK_ACCESS_TOKEN,
    );
  });
});
