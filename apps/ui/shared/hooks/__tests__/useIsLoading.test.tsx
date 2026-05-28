// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';

import { useIsLoading } from '@amdenterpriseai/hooks';

function createQueryClientWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

describe('useIsLoading', () => {
  it('is false when no matching query is loading', () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(() => useIsLoading(['prefix']), {
      wrapper: createQueryClientWrapper(client),
    });
    expect(result.current).toBe(false);
  });

  it('is false when matching query is disabled and idle', () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => {
        useQuery({
          queryKey: ['prefix', 'a'],
          queryFn: () => new Promise<string>(() => {}),
          enabled: false,
        });
        return useIsLoading(['prefix']);
      },
      { wrapper: createQueryClientWrapper(client) },
    );
    expect(result.current).toBe(false);
  });

  it('is true while a matching query is in initial pending+fetching state', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result, rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => {
        useQuery({
          queryKey: ['prefix', 'a'],
          queryFn: () => new Promise<string>(() => {}),
          enabled,
        });
        return useIsLoading(['prefix']);
      },
      {
        wrapper: createQueryClientWrapper(client),
        initialProps: { enabled: false },
      },
    );

    expect(result.current).toBe(false);

    act(() => {
      rerender({ enabled: true });
    });

    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  it('is false after a matching query succeeds (not pending)', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(
      () => {
        useQuery({
          queryKey: ['prefix', 'b'],
          queryFn: async () => 'done',
        });
        return useIsLoading(['prefix']);
      },
      { wrapper: createQueryClientWrapper(client) },
    );

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });

  it('ignores loading queries that do not match the prefix', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result, rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => {
        useQuery({
          queryKey: ['other', 'x'],
          queryFn: () => new Promise<string>(() => {}),
          enabled,
        });
        return useIsLoading(['prefix']);
      },
      {
        wrapper: createQueryClientWrapper(client),
        initialProps: { enabled: false },
      },
    );

    act(() => {
      rerender({ enabled: true });
    });

    await waitFor(() => {
      expect(client.isFetching()).toBeGreaterThan(0);
    });
    expect(result.current).toBe(false);
  });
});
