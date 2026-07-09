// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import { useInferenceModelsByName } from '@/hooks/useInferenceModelsByName';
import { getInferenceModel } from '@/lib/app/inference';

vi.mock('@/lib/app/inference', () => ({
  getInferenceModel: vi.fn(),
}));

const wrapper =
  (client: QueryClient) =>
  ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );

// The hook supplies its own `retry` predicate; the test client only needs to
// keep the retry backoff at zero so non-404 failures don't slow tests down.
const newClient = () =>
  new QueryClient({ defaultOptions: { queries: { retryDelay: 0 } } });

const buildModel = (name: string) =>
  ({
    metadata: { name, annotations: {}, labels: {} },
    spec: { image: `${name}:latest` },
    status: {
      status: 'Ready',
      imageMetadata: { model: { tags: [] }, oci: {} },
    },
  }) as unknown as Awaited<ReturnType<typeof getInferenceModel>>;

describe('useInferenceModelsByName', () => {
  it('de-duplicates names so each unique name is fetched once', async () => {
    vi.mocked(getInferenceModel).mockImplementation(async (name: string) =>
      buildModel(name),
    );
    const client = newClient();

    const { result } = renderHook(
      () => useInferenceModelsByName(['a', 'b', 'a', '', 'b']),
      { wrapper: wrapper(client) },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(getInferenceModel).toHaveBeenCalledTimes(2);
    expect(getInferenceModel).toHaveBeenCalledWith('a');
    expect(getInferenceModel).toHaveBeenCalledWith('b');
  });

  it('populates byName with successful results keyed by resource name', async () => {
    vi.mocked(getInferenceModel).mockImplementation(async (name: string) =>
      buildModel(name),
    );
    const client = newClient();

    const { result } = renderHook(
      () => useInferenceModelsByName(['llama', 'mistral']),
      { wrapper: wrapper(client) },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.byName.size).toBe(2);
    expect(result.current.byName.get('llama')?.metadata.name).toBe('llama');
    expect(result.current.byName.get('mistral')?.metadata.name).toBe('mistral');
    expect(result.current.isError).toBe(false);
  });

  it('flags isError when any per-name lookup fails but still surfaces successful ones', async () => {
    vi.mocked(getInferenceModel).mockImplementation(async (name: string) => {
      if (name === 'broken') throw new Error('boom');
      return buildModel(name);
    });
    const client = newClient();

    const { result } = renderHook(
      () => useInferenceModelsByName(['ok', 'broken']),
      { wrapper: wrapper(client) },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.isError).toBe(true);
    expect(result.current.byName.has('ok')).toBe(true);
    expect(result.current.byName.has('broken')).toBe(false);
  });

  it('exposes isFetching that mirrors isLoading on the initial fetch', async () => {
    vi.mocked(getInferenceModel).mockImplementation(async (name: string) =>
      buildModel(name),
    );
    const client = newClient();

    const { result } = renderHook(() => useInferenceModelsByName(['llama']), {
      wrapper: wrapper(client),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.isFetching).toBe(true);
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.isFetching).toBe(false);
  });

  it('reports isFetching=true (with isLoading=false) during background refetches', async () => {
    // After the cache has data, invalidateQueries triggers a background
    // refetch — `isLoading` stays false (we have cached data) but
    // `isFetching` flips true so refresh indicators can reflect the work.
    let resolveSecondFetch: (() => void) | undefined;
    let fetchCount = 0;
    vi.mocked(getInferenceModel).mockImplementation(async (name: string) => {
      fetchCount += 1;
      if (fetchCount > 1) {
        await new Promise<void>((resolve) => {
          resolveSecondFetch = resolve;
        });
      }
      return buildModel(name);
    });
    const client = newClient();

    const { result } = renderHook(() => useInferenceModelsByName(['llama']), {
      wrapper: wrapper(client),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.isFetching).toBe(false);
    expect(result.current.byName.size).toBe(1);

    // Trigger a background refetch.
    client.invalidateQueries({ queryKey: ['inferenceModel'] });

    await waitFor(() => {
      expect(result.current.isFetching).toBe(true);
    });
    // Cached data is still present, so isLoading remains false.
    expect(result.current.isLoading).toBe(false);
    expect(result.current.byName.size).toBe(1);

    resolveSecondFetch?.();
    await waitFor(() => {
      expect(result.current.isFetching).toBe(false);
    });
  });

  it('returns an empty map and false loading when given no names', async () => {
    const client = newClient();
    const { result } = renderHook(() => useInferenceModelsByName([]), {
      wrapper: wrapper(client),
    });

    expect(result.current.byName.size).toBe(0);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(getInferenceModel).not.toHaveBeenCalled();
  });

  it('does not retry 404s but retries generic errors up to 3 times', async () => {
    // A 404 means the model was renamed/removed — retrying is pure waste.
    // Other errors (network, 5xx) should retry 3 times for resilience.
    const callsByName: Record<string, number> = { missing: 0, flaky: 0 };
    vi.mocked(getInferenceModel).mockImplementation(async (name: string) => {
      callsByName[name] = (callsByName[name] ?? 0) + 1;
      if (name === 'missing') {
        throw new APIRequestError('not found', 404);
      }
      throw new Error('network blip');
    });
    const client = newClient();

    const { result } = renderHook(
      () => useInferenceModelsByName(['missing', 'flaky']),
      { wrapper: wrapper(client) },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    // 404: queryFn called exactly once (no retry).
    expect(callsByName.missing).toBe(1);
    // Generic error: queryFn called 4 times (1 initial + 3 retries).
    expect(callsByName.flaky).toBe(4);
    expect(result.current.isError).toBe(true);
  });
});
