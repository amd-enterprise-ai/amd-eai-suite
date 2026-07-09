// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  clearAuthzCache,
  DEFAULT_AUTHZ_CACHE_TTL_MS,
  getCachedAccess,
  setCachedAccess,
} from '@/lib/server/authz-cache';

beforeEach(() => {
  clearAuthzCache();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe('authz-cache', () => {
  it('returns the cached entry within TTL', () => {
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
      internalUrl: 'http://internal.svc/v1',
      ttlMs: 60_000,
    });
    const result = getCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
    });
    expect(result).toEqual({ internalUrl: 'http://internal.svc/v1' });
  });

  it('returns undefined after TTL expires', () => {
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
      internalUrl: 'http://internal.svc/v1',
      ttlMs: 1_000,
    });
    vi.advanceTimersByTime(1_500);
    const result = getCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
    });
    expect(result).toBeUndefined();
  });

  it('keys entries by (userId, deploymentId) without collisions', () => {
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
      internalUrl: 'http://alice-dep1.svc/v1',
      ttlMs: 60_000,
    });
    setCachedAccess({
      userId: 'bob',
      deploymentId: 'dep-1',
      internalUrl: 'http://bob-dep1.svc/v1',
      ttlMs: 60_000,
    });
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-2',
      internalUrl: 'http://alice-dep2.svc/v1',
      ttlMs: 60_000,
    });
    expect(getCachedAccess({ userId: 'alice', deploymentId: 'dep-1' })).toEqual(
      { internalUrl: 'http://alice-dep1.svc/v1' },
    );
    expect(getCachedAccess({ userId: 'bob', deploymentId: 'dep-1' })).toEqual({
      internalUrl: 'http://bob-dep1.svc/v1',
    });
    expect(getCachedAccess({ userId: 'alice', deploymentId: 'dep-2' })).toEqual(
      { internalUrl: 'http://alice-dep2.svc/v1' },
    );
  });

  it('reads CHAT_AUTHZ_CACHE_TTL_MS env var at call time, not at module load', () => {
    vi.stubEnv('CHAT_AUTHZ_CACHE_TTL_MS', '5000');
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
      internalUrl: 'http://internal.svc/v1',
    });
    vi.advanceTimersByTime(4_000);
    expect(getCachedAccess({ userId: 'alice', deploymentId: 'dep-1' })).toEqual(
      { internalUrl: 'http://internal.svc/v1' },
    );
    vi.advanceTimersByTime(2_000);
    expect(
      getCachedAccess({ userId: 'alice', deploymentId: 'dep-1' }),
    ).toBeUndefined();
  });

  it('falls back to the default TTL when env var is unset', () => {
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
      internalUrl: 'http://internal.svc/v1',
    });
    vi.advanceTimersByTime(DEFAULT_AUTHZ_CACHE_TTL_MS - 1);
    expect(getCachedAccess({ userId: 'alice', deploymentId: 'dep-1' })).toEqual(
      { internalUrl: 'http://internal.svc/v1' },
    );
    vi.advanceTimersByTime(2);
    expect(
      getCachedAccess({ userId: 'alice', deploymentId: 'dep-1' }),
    ).toBeUndefined();
  });

  it('explicit ttlMs arg overrides the env var', () => {
    vi.stubEnv('CHAT_AUTHZ_CACHE_TTL_MS', '60000');
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
      internalUrl: 'http://internal.svc/v1',
      ttlMs: 1_000,
    });
    vi.advanceTimersByTime(1_500);
    expect(
      getCachedAccess({ userId: 'alice', deploymentId: 'dep-1' }),
    ).toBeUndefined();
  });

  it('evicts expired entries on the next write', () => {
    setCachedAccess({
      userId: 'alice',
      deploymentId: 'dep-1',
      internalUrl: 'http://alice-dep1.svc/v1',
      ttlMs: 1_000,
    });
    setCachedAccess({
      userId: 'carol',
      deploymentId: 'dep-9',
      internalUrl: 'http://carol-dep9.svc/v1',
      ttlMs: 1_000,
    });
    vi.advanceTimersByTime(1_500);
    setCachedAccess({
      userId: 'bob',
      deploymentId: 'dep-2',
      internalUrl: 'http://bob-dep2.svc/v1',
      ttlMs: 60_000,
    });
    // Expired entries should no longer be reachable, even before their own get-time check.
    expect(
      getCachedAccess({ userId: 'alice', deploymentId: 'dep-1' }),
    ).toBeUndefined();
    expect(
      getCachedAccess({ userId: 'carol', deploymentId: 'dep-9' }),
    ).toBeUndefined();
    expect(getCachedAccess({ userId: 'bob', deploymentId: 'dep-2' })).toEqual({
      internalUrl: 'http://bob-dep2.svc/v1',
    });
  });
});
