// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  RouteError,
  handleError,
  authenticateRoute,
  proxyRequest,
} from '@amdenterpriseai/utils/server';
import { getServerSession } from 'next-auth';

vi.mock('next-auth', () => ({
  getServerSession: vi.fn(),
}));

// Single shared logger instance so tests can assert on the same vi.fn() that
// route.ts captured at module load via `const logger = getLogger()`.
// Hoisted because vi.mock is hoisted above top-level declarations.
const { mockLogger } = vi.hoisted(() => ({
  mockLogger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
}));
vi.mock('@/src/server/logger', () => ({
  default: () => mockLogger,
}));

describe('RouteError', () => {
  it('should create a RouteError with status and message', () => {
    const error = new RouteError(404, 'Not found');

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(RouteError);
    expect(error.status).toBe(404);
    expect(error.message).toBe('Not found');
    expect(error.userMessage).toBeUndefined();
  });

  it('should create a RouteError with status, message and userMessage', () => {
    const error = new RouteError(
      500,
      'Internal server error details',
      'Something went wrong',
    );

    expect(error.status).toBe(500);
    expect(error.message).toBe('Internal server error details');
    expect(error.userMessage).toBe('Something went wrong');
  });

  it('should have proper error name', () => {
    const error = new RouteError(403, 'Forbidden');

    expect(error.name).toBe('Error');
  });

  it('should be throwable', () => {
    expect(() => {
      throw new RouteError(400, 'Bad request');
    }).toThrow(RouteError);
  });

  it('should preserve stack trace', () => {
    const error = new RouteError(500, 'Internal error');

    expect(error.stack).toBeDefined();
    expect(error.stack).toContain('route.test.ts');
  });

  it('should handle various HTTP status codes', () => {
    const statuses = [400, 401, 403, 404, 500, 502, 503];

    statuses.forEach((status) => {
      const error = new RouteError(status, `Error ${status}`);
      expect(error.status).toBe(status);
      expect(error.message).toBe(`Error ${status}`);
    });
  });
});

describe('authenticateRoute', () => {
  const mockGetServerSession = vi.mocked(getServerSession);

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should throw 401 when no session', async () => {
    mockGetServerSession.mockResolvedValueOnce(null as any);

    await expect(authenticateRoute()).rejects.toMatchObject({ status: 401 });
  });

  it('should throw 401 when session has no access token', async () => {
    mockGetServerSession.mockResolvedValueOnce({
      user: { roles: [] },
      accessToken: undefined,
    } as any);

    await expect(authenticateRoute()).rejects.toMatchObject({ status: 401 });
  });

  it('should throw 403 when user role is missing', async () => {
    mockGetServerSession.mockResolvedValueOnce({
      user: { roles: ['user'] },
      accessToken: 'token',
    } as any);

    await expect(authenticateRoute('admin')).rejects.toMatchObject({
      status: 403,
    });
  });

  it('should return session when authorized', async () => {
    const session = {
      user: { roles: ['admin'] },
      accessToken: 'token',
    } as any;
    mockGetServerSession.mockResolvedValueOnce(session);

    await expect(authenticateRoute('admin')).resolves.toBe(session);
  });
});

describe('proxyRequest', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.clearAllMocks();
  });

  it('should proxy GET requests with query params', async () => {
    const mockFetch = vi.mocked(global.fetch);
    const responseBody = { camelCase: 'value' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify(responseBody)),
    } as any);

    const req = {
      method: 'GET',
      nextUrl: new URL('http://localhost/api?foo=1&bar=2'),
    } as any;

    const result = await proxyRequest(req, 'http://service/api', 'token');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://service/api?foo=1&bar=2',
      expect.objectContaining({
        method: 'GET',
        redirect: 'manual',
        headers: expect.objectContaining({ Authorization: 'Bearer token' }),
      }),
    );
    expect(result).toEqual(responseBody);
  });

  it('should preserve existing query string on target url', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify({ ok: true })),
    } as any);

    const req = {
      method: 'GET',
      nextUrl: new URL('http://localhost/api?foo=1'),
    } as any;

    await proxyRequest(req, 'http://service/api?existing=1', 'token');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://service/api?existing=1&foo=1',
      expect.objectContaining({ method: 'GET', redirect: 'manual' }),
    );
  });

  it('should include JSON body for POST requests', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(JSON.stringify({ ok: true })),
    } as any);

    const req = {
      method: 'POST',
      nextUrl: new URL('http://localhost/api'),
      json: vi.fn().mockResolvedValue({ foo: 'bar' }),
    } as any;

    await proxyRequest(req, 'http://service/api', 'token');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://service/api?',
      expect.objectContaining({
        method: 'POST',
        redirect: 'manual',
        body: JSON.stringify({ foo: 'bar' }),
      }),
    );
  });

  it('should return status 204 for no-content responses', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    } as any);

    const req = {
      method: 'DELETE',
      nextUrl: new URL('http://localhost/api'),
      json: vi.fn().mockResolvedValue({}),
    } as any;

    const result = await proxyRequest(req, 'http://service/api', 'token');

    expect(result).toEqual({ status: 204 });
  });

  it('should return empty object for ok responses with an empty body', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue(''),
    } as any);

    const req = {
      method: 'PATCH',
      nextUrl: new URL('http://localhost/api'),
      json: vi.fn().mockResolvedValue({}),
    } as any;

    const result = await proxyRequest(req, 'http://service/api', 'token');

    expect(result).toEqual({});
  });

  it('parses JSON with a leading UTF-8 BOM', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue('\uFEFF{"bom":true}'),
    } as any);

    const req = {
      method: 'GET',
      nextUrl: new URL('http://localhost/api'),
    } as any;

    await expect(
      proxyRequest(req, 'http://service/api', 'token'),
    ).resolves.toEqual({ bom: true });
  });

  it('throws a descriptive RouteError when upstream returns HTML with 200', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: vi
        .fn()
        .mockResolvedValue('<!DOCTYPE html><html><body>login</body></html>'),
    } as any);

    const req = {
      method: 'GET',
      nextUrl: new URL('http://localhost/api'),
    } as any;

    await expect(
      proxyRequest(req, 'http://service/api', 'token'),
    ).rejects.toMatchObject({
      status: 502,
      message: expect.stringContaining('HTML'),
    });
  });

  it('should throw RouteError on non-ok response', async () => {
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: vi.fn().mockResolvedValue('server error'),
    } as any);

    const req = {
      method: 'GET',
      nextUrl: new URL('http://localhost/api'),
    } as any;

    await expect(
      proxyRequest(req, 'http://service/api', 'token'),
    ).rejects.toMatchObject({ status: 500, message: 'server error' });
  });

  it('maps upstream 3xx to 502; Location stays on internal message, not userMessage', async () => {
    const mockFetch = vi.mocked(global.fetch);
    const headers = new Headers({
      Location: 'https://login.example/authorize',
    });
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 302,
      headers,
      text: vi.fn().mockResolvedValue(''),
    } as any);

    const req = {
      method: 'GET',
      nextUrl: new URL('http://localhost/api'),
    } as any;

    const err = (await proxyRequest(req, 'http://service/api', 'token').catch(
      (e) => e,
    )) as RouteError;

    expect(err).toMatchObject({
      status: 502,
      message: expect.stringContaining(
        'Location: https://login.example/authorize',
      ),
      userMessage: expect.not.stringContaining('login.example'),
    });
    expect(err.userMessage).toContain('302 (redirect)');

    const res = handleError(err);
    const body = await res.json();
    expect(body.error).toBe(err.userMessage);
    expect(body.error).not.toContain('login.example');
  });
});

describe('handleError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLogger.error.mockClear();
  });

  it('should return NextResponse with error message and status', () => {
    const error = new RouteError(404, 'Resource not found');

    const response = handleError(error);

    expect(response.status).toBe(404);
  });

  it('should use userMessage if provided', () => {
    const error = new RouteError(
      500,
      'Internal error details',
      'User-friendly error message',
    );

    const response = handleError(error);

    expect(response.status).toBe(500);
  });

  it('should default to status 500 if status is not provided', () => {
    const error = new Error('Generic error');

    const response = handleError(error);

    expect(response.status).toBe(500);
  });

  it('should handle JSON error messages with detail property', () => {
    const error = new Error(JSON.stringify({ detail: 'Detailed error info' }));

    const response = handleError(error);

    expect(response.status).toBe(500);
  });

  it('should use regular message if JSON parsing fails', () => {
    const error = new Error('Plain text error');

    const response = handleError(error);

    expect(response.status).toBe(500);
  });

  it('should handle error with custom status code', () => {
    const error = Object.assign(new Error('Custom error'), { status: 403 });

    const response = handleError(error);

    expect(response.status).toBe(403);
  });

  it('should prefer userMessage over JSON detail', () => {
    const error = Object.assign(
      new Error(JSON.stringify({ detail: 'JSON detail' })),
      { userMessage: 'User message', status: 400 },
    );

    const response = handleError(error);

    expect(response.status).toBe(400);
  });

  it('should handle error without message property', () => {
    const error = { status: 500 };

    const response = handleError(error);

    expect(response.status).toBe(500);
  });

  it('should handle various error types', () => {
    const errors = [
      new RouteError(400, 'Bad Request'),
      new RouteError(401, 'Unauthorized', 'Please log in'),
      new Error('Generic error'),
      { status: 403, message: 'Forbidden' },
      { message: 'No status' },
    ];

    errors.forEach((error) => {
      const response = handleError(error);
      expect(response).toBeDefined();
      expect(response.status).toBeGreaterThanOrEqual(400);
    });
  });

  it('should handle errors with complex JSON messages', () => {
    const complexError = new Error(
      JSON.stringify({
        detail: 'Complex error',
        code: 'ERR_001',
        context: { field: 'value' },
      }),
    );

    const response = handleError(complexError);

    expect(response.status).toBe(500);
  });

  it('should handle malformed JSON in error message', () => {
    const error = new Error('{ invalid json');

    const response = handleError(error);

    expect(response.status).toBe(500);
  });

  it('passes through structured JSON upstream errors and sets flattened error', async () => {
    const payload = {
      detail: 'Model blocked',
      additionalInfo: { blockingServices: ['aim-svc'] },
    };
    const response = handleError(new RouteError(409, JSON.stringify(payload)));
    expect(response.status).toBe(409);
    const body = await response.json();
    expect(body).toEqual({
      ...payload,
      error: 'Model blocked',
    });
  });

  it('uses generic flattened error when structured body has non-string detail', async () => {
    const payload = {
      detail: [{ type: 'validation_error', msg: 'invalid' }],
      extra: 'kept',
    };
    const response = handleError(new RouteError(422, JSON.stringify(payload)));
    expect(response.status).toBe(422);
    const body = await response.json();
    expect(body).toMatchObject({
      ...payload,
      error: 'Request failed',
    });
  });

  describe('logger.error gating', () => {
    it('does not log RouteError with 4xx status', () => {
      handleError(new RouteError(400, 'Bad request'));
      handleError(new RouteError(401, 'Unauthorized'));
      handleError(new RouteError(404, 'Not found'));
      handleError(new RouteError(499, 'Client closed'));

      expect(mockLogger.error).not.toHaveBeenCalled();
    });

    it('logs RouteError with 5xx status', () => {
      handleError(new RouteError(500, 'Internal'));
      handleError(new RouteError(502, 'Bad gateway'));

      expect(mockLogger.error).toHaveBeenCalledTimes(2);
    });

    it('logs non-RouteError errors regardless of status field', () => {
      handleError(new Error('Generic error'));
      handleError(Object.assign(new Error('With status'), { status: 400 }));

      expect(mockLogger.error).toHaveBeenCalledTimes(2);
    });
  });
});
