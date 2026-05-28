// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QueryClient } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useLastQueryUpdated } from '@amdenterpriseai/hooks';

describe('useLastQueryUpdated', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns undefined when no queries match the prefix', () => {
    const client = new QueryClient();
    const { result } = renderHook(() =>
      useLastQueryUpdated(['metrics'], client),
    );
    expect(result.current).toBeUndefined();
  });

  it('returns undefined when no queries exist in the cache', () => {
    const client = new QueryClient();
    const { result } = renderHook(() => useLastQueryUpdated(['any'], client));
    expect(result.current).toBeUndefined();
  });

  it('returns the latest dataUpdatedAt among matching queries', () => {
    vi.useFakeTimers();
    const client = new QueryClient();

    vi.setSystemTime(new Date('2020-01-01T00:00:00.000Z'));
    client.setQueryData(['namespace', 'ns-a', 'metrics', 'gpu'], { v: 1 });

    vi.setSystemTime(new Date('2020-01-01T00:00:05.000Z'));
    client.setQueryData(['namespace', 'ns-a', 'metrics', 'vram'], { v: 2 });

    const { result } = renderHook(() =>
      useLastQueryUpdated(['namespace', 'ns-a', 'metrics'], client),
    );
    expect(result.current).toEqual(new Date('2020-01-01T00:00:05.000Z'));
  });

  it('does not include queries outside the prefix', () => {
    vi.useFakeTimers();
    const client = new QueryClient();

    vi.setSystemTime(new Date('2020-06-01T12:00:00.000Z'));
    client.setQueryData(['namespace', 'ns-a', 'stats'], { total: 3 });

    vi.setSystemTime(new Date('2020-01-01T00:00:00.000Z'));
    client.setQueryData(['namespace', 'ns-a', 'metrics', 'gpu'], { v: 1 });

    const { result } = renderHook(() =>
      useLastQueryUpdated(['namespace', 'ns-a', 'metrics'], client),
    );
    expect(result.current).toEqual(new Date('2020-01-01T00:00:00.000Z'));
  });

  it('re-renders when a matching query is written after mount', async () => {
    const client = new QueryClient();

    const { result } = renderHook(() =>
      useLastQueryUpdated(['namespace', 'ns-a', 'metrics'], client),
    );
    expect(result.current).toBeUndefined();

    const before = Date.now();
    await act(async () => {
      client.setQueryData(['namespace', 'ns-a', 'metrics', 'gpu'], { v: 1 });
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current).toBeDefined();
    });
    expect(result.current!.getTime()).toBeGreaterThanOrEqual(before);
  });
});
