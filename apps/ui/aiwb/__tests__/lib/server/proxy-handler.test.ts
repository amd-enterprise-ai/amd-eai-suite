// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';

import {
  GET,
  POST,
  PUT,
  DELETE,
  PATCH,
  validatePathSegments,
} from '@/lib/server/proxy-handler';
import { RouteError } from '@amdenterpriseai/utils/server';

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
  mockAuthenticateRoute.mockResolvedValue({
    accessToken: MOCK_ACCESS_TOKEN,
  });
  mockProxyRequest.mockResolvedValue({ success: true });
  mockHandleError.mockImplementation((error: any) => {
    return Response.json(
      { error: error.message },
      { status: error.status || 500 },
    );
  });
});

function createNextRequest(path: string, method: string = 'GET'): NextRequest {
  return new NextRequest(new URL(path, 'http://localhost:3000'), { method });
}

describe('proxy-handler', () => {
  describe('HTTP method handlers', () => {
    it('GET forwards request to proxyHandler', async () => {
      const req = createNextRequest('/api/aims');
      const response = await GET(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/aims`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('POST forwards request to proxyHandler', async () => {
      const req = createNextRequest('/api/aims', 'POST');
      const response = await POST(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/aims`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('PUT forwards request to proxyHandler', async () => {
      const req = createNextRequest('/api/aims/123', 'PUT');
      const response = await PUT(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/aims/123`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('DELETE forwards request to proxyHandler', async () => {
      const req = createNextRequest('/api/aims/123', 'DELETE');
      const response = await DELETE(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/aims/123`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('PATCH forwards request to proxyHandler', async () => {
      const req = createNextRequest('/api/aims/123', 'PATCH');
      const response = await PATCH(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/aims/123`,
        MOCK_ACCESS_TOKEN,
      );
    });
  });

  describe('path extraction and proxying', () => {
    it('extracts multi-segment API paths correctly', async () => {
      const req = createNextRequest('/api/aims/232332/deploy');
      await GET(req);

      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/aims/232332/deploy`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('extracts single-segment API paths correctly', async () => {
      const req = createNextRequest('/api/clusters');
      await GET(req);

      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/clusters`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('handles paths with hyphens and underscores', async () => {
      const req = createNextRequest('/api/my-resource/sub_path');
      await GET(req);

      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/my-resource/sub_path`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('calls authenticateRoute before proxying', async () => {
      const req = createNextRequest('/api/aims');
      await GET(req);

      expect(mockAuthenticateRoute).toHaveBeenCalledTimes(1);
    });

    it('returns JSON response from proxied request', async () => {
      const mockData = { id: '123', name: 'test-aim', status: 'deployed' };
      mockProxyRequest.mockResolvedValue(mockData);

      const req = createNextRequest('/api/aims/123');
      const response = await GET(req);
      const body = await response.json();

      expect(body).toEqual(mockData);
    });
  });

  describe('path validation - SSRF prevention', () => {
    it('rejects protocol injection with colon', async () => {
      const req = createNextRequest('/api/http:evil.com');
      await GET(req);

      expect(mockHandleError).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 400,
          message: 'Invalid path: invalid characters',
        }),
      );
      expect(mockProxyRequest).not.toHaveBeenCalled();
    });

    it('rejects segments with special characters', async () => {
      const req = createNextRequest('/api/aims/test@evil');
      await GET(req);

      expect(mockHandleError).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 400,
          message:
            'Invalid path segment: only alphanumeric characters, dots, percents, hyphens, and underscores are allowed',
        }),
      );
      expect(mockProxyRequest).not.toHaveBeenCalled();
    });

    it('accepts segments with dots in names', async () => {
      const req = createNextRequest('/api/aims/file.json');
      const response = await GET(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/aims/file.json`,
        MOCK_ACCESS_TOKEN,
      );
    });

    it('rejects segments with spaces (encoded as %20)', async () => {
      const req = createNextRequest('/api/aims/bad%20path');
      await GET(req);

      expect(mockHandleError).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 400,
        }),
      );
      expect(mockProxyRequest).not.toHaveBeenCalled();
    });

    it('accepts encoded model ids with percent characters', async () => {
      const req = createNextRequest(
        '/api/namespaces/demo/models/Qwen%252FQwen2.5-0.5B-Instruct/finetune',
      );
      const response = await POST(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        `${MOCK_API_SERVICE_URL}/v1/namespaces/demo/models/Qwen%252FQwen2.5-0.5B-Instruct/finetune`,
        MOCK_ACCESS_TOKEN,
      );
    });
  });

  describe('invalid API paths', () => {
    it('rejects requests without /api/ prefix', async () => {
      const req = createNextRequest('/other/path');
      await GET(req);

      expect(mockHandleError).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 400,
          message: 'Invalid API path',
        }),
      );
      expect(mockProxyRequest).not.toHaveBeenCalled();
    });

    it('rejects request to bare /api/ with no subpath', async () => {
      const req = createNextRequest('/api/');
      await GET(req);

      expect(mockHandleError).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 400,
          message: 'Invalid API path',
        }),
      );
      expect(mockProxyRequest).not.toHaveBeenCalled();
    });
  });

  describe('error handling', () => {
    it('calls handleError when authentication fails', async () => {
      const authError = new Error('Unauthorized');
      (authError as any).status = 401;
      mockAuthenticateRoute.mockRejectedValue(authError);

      const req = createNextRequest('/api/aims');
      await GET(req);

      expect(mockHandleError).toHaveBeenCalledWith(authError);
      expect(mockProxyRequest).not.toHaveBeenCalled();
    });

    it('calls handleError when proxyRequest fails', async () => {
      const proxyError = new Error('Bad Gateway');
      (proxyError as any).status = 502;
      mockProxyRequest.mockRejectedValue(proxyError);

      const req = createNextRequest('/api/aims');
      await GET(req);

      expect(mockHandleError).toHaveBeenCalledWith(proxyError);
    });
  });

  describe('origin validation', () => {
    it('succeeds when constructed URL origin matches expected origin', async () => {
      const req = createNextRequest('/api/aims');
      const response = await GET(req);
      const body = await response.json();

      expect(body).toEqual({ success: true });
      expect(mockHandleError).not.toHaveBeenCalled();
    });
  });

  describe('validatePathSegments', () => {
    it('accepts valid alphanumeric segments', () => {
      expect(() =>
        validatePathSegments(['aims', '123', 'deploy']),
      ).not.toThrow();
    });

    it('accepts segments with hyphens and underscores', () => {
      expect(() =>
        validatePathSegments(['my-resource', 'sub_path']),
      ).not.toThrow();
    });

    it('accepts a single valid segment', () => {
      expect(() => validatePathSegments(['clusters'])).not.toThrow();
    });

    it('accepts an empty array', () => {
      expect(() => validatePathSegments([])).not.toThrow();
    });

    it('throws on empty string segment', () => {
      expect(() => validatePathSegments(['aims', '', 'deploy'])).toThrow(
        RouteError,
      );
      expect(() => validatePathSegments(['aims', '', 'deploy'])).toThrow(
        'Invalid path: empty segment',
      );
    });

    it('throws on whitespace-only segment', () => {
      expect(() => validatePathSegments(['aims', '  ', 'deploy'])).toThrow(
        RouteError,
      );
      expect(() => validatePathSegments(['aims', '  ', 'deploy'])).toThrow(
        'Invalid path: empty segment',
      );
    });

    it('throws on double-dot path traversal', () => {
      expect(() => validatePathSegments(['aims', '..', 'etc'])).toThrow(
        RouteError,
      );
      expect(() => validatePathSegments(['aims', '..', 'etc'])).toThrow(
        'Invalid path: path traversal not allowed',
      );
    });

    it('throws on single-dot path traversal', () => {
      expect(() => validatePathSegments(['.', 'aims'])).toThrow(RouteError);
      expect(() => validatePathSegments(['.', 'aims'])).toThrow(
        'Invalid path: path traversal not allowed',
      );
    });

    it('throws on segment containing colon (protocol injection)', () => {
      expect(() => validatePathSegments(['http:', 'evil.com'])).toThrow(
        RouteError,
      );
      expect(() => validatePathSegments(['http:', 'evil.com'])).toThrow(
        'Invalid path: invalid characters',
      );
    });

    it('throws on segment containing double slash', () => {
      expect(() => validatePathSegments(['http//evil'])).toThrow(RouteError);
      expect(() => validatePathSegments(['http//evil'])).toThrow(
        'Invalid path: invalid characters',
      );
    });

    it('throws on segment with special characters', () => {
      expect(() => validatePathSegments(['test@evil'])).toThrow(RouteError);
      expect(() => validatePathSegments(['test@evil'])).toThrow(
        'only alphanumeric characters, dots, percents, hyphens, and underscores are allowed',
      );
    });

    it('accepts segment with dots', () => {
      expect(() => validatePathSegments(['file.json'])).not.toThrow();
    });

    it('accepts segment with encoded percent characters', () => {
      expect(() =>
        validatePathSegments(['Qwen%252FQwen2.5-0.5B-Instruct']),
      ).not.toThrow();
    });

    it('throws on segment with spaces', () => {
      expect(() => validatePathSegments(['bad path'])).toThrow(RouteError);
      expect(() => validatePathSegments(['bad path'])).toThrow(
        'only alphanumeric characters, dots, percents, hyphens, and underscores are allowed',
      );
    });

    it('throws on segment with encoded spaces', () => {
      expect(() => validatePathSegments(['bad%20path'])).toThrow(RouteError);
      expect(() => validatePathSegments(['bad%20path'])).toThrow(
        'only alphanumeric characters, dots, percents, hyphens, and underscores are allowed',
      );
    });

    it('throws on segment with slashes', () => {
      expect(() => validatePathSegments(['a/b'])).toThrow(RouteError);
      expect(() => validatePathSegments(['a/b'])).toThrow(
        'only alphanumeric characters, dots, percents, hyphens, and underscores are allowed',
      );
    });

    it('throws on first invalid segment when multiple are invalid', () => {
      expect(() => validatePathSegments(['..', 'http:', 'test@evil'])).toThrow(
        'Invalid path: path traversal not allowed',
      );
    });
  });
});
