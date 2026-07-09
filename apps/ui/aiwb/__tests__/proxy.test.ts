// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';
import { describe, expect, it, vi } from 'vitest';

import { config, proxy } from '@/proxy';

vi.mock('next-auth/jwt', () => ({
  getToken: vi.fn(),
}));

const mockGetToken = vi.mocked(getToken);

describe('auth middleware', () => {
  it('bypasses next-auth API routes to avoid redirect loops', async () => {
    mockGetToken.mockResolvedValue(null);

    const request = new NextRequest('http://localhost:3000/api/auth/signin');
    const response = await proxy(request);

    expect(response.headers.get('x-middleware-next')).toBe('1');
  });

  it('redirects unauthenticated users to sign in page', async () => {
    mockGetToken.mockResolvedValue(null);

    const request = new NextRequest('http://localhost:3000/project-1/models');
    const response = await proxy(request);

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe(
      'http://localhost:3000/api/auth/signin?callbackUrl=%2Fproject-1%2Fmodels',
    );
  });

  it('allows authenticated users through', async () => {
    mockGetToken.mockResolvedValue({
      email: 'test@example.com',
      accessToken: 'token',
    });

    const request = new NextRequest('http://localhost:3000/project-1/models');
    const response = await proxy(request);

    expect(response.headers.get('x-middleware-next')).toBe('1');
  });

  it('redirects users when access token is missing', async () => {
    mockGetToken.mockResolvedValue({
      email: 'test@example.com',
    });

    const request = new NextRequest('http://localhost:3000/');
    const response = await proxy(request);

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toContain('/api/auth/signin');
  });

  it('protects root and project routes by matcher', () => {
    expect(config).toEqual({
      matcher: ['/', '/((?!api|_next/static|_next/image|favicon.ico).*)'],
    });
  });
});
