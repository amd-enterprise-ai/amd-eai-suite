// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';

import { extractApiPath } from '@/lib/server/route-utils';
import { RouteError } from '@amdenterpriseai/utils/server';

function createNextRequest(path: string): NextRequest {
  return new NextRequest(new URL(path, 'http://localhost:3000'));
}

describe('extractApiPath', () => {
  it('extracts single-segment path after /api/', () => {
    const req = createNextRequest('/api/aims');
    expect(extractApiPath(req)).toBe('aims');
  });

  it('extracts multi-segment path after /api/', () => {
    const req = createNextRequest('/api/aims/232332/deploy');
    expect(extractApiPath(req)).toBe('aims/232332/deploy');
  });

  it('extracts namespace-style paths', () => {
    const req = createNextRequest('/api/namespaces/ns1/aims/services/123/chat');
    expect(extractApiPath(req)).toBe('namespaces/ns1/aims/services/123/chat');
  });

  it('extracts paths with hyphens and underscores', () => {
    const req = createNextRequest('/api/my-resource/sub_path');
    expect(extractApiPath(req)).toBe('my-resource/sub_path');
  });

  it('throws RouteError for paths without /api/ prefix', () => {
    const req = createNextRequest('/other/path');
    expect(() => extractApiPath(req)).toThrow(RouteError);
    expect(() => extractApiPath(req)).toThrow('Invalid API path');
  });

  it('throws RouteError for bare /api/ with no subpath', () => {
    const req = createNextRequest('/api/');
    expect(() => extractApiPath(req)).toThrow(RouteError);
    expect(() => extractApiPath(req)).toThrow('Invalid API path');
  });

  it('throws RouteError for root path', () => {
    const req = createNextRequest('/');
    expect(() => extractApiPath(req)).toThrow(RouteError);
    expect(() => extractApiPath(req)).toThrow('Invalid API path');
  });

  it('throws RouteError for /api without trailing slash', () => {
    const req = createNextRequest('/api');
    expect(() => extractApiPath(req)).toThrow(RouteError);
    expect(() => extractApiPath(req)).toThrow('Invalid API path');
  });
});
