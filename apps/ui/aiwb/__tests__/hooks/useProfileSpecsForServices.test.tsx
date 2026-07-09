// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { useProfileSpecsForServices } from '@/hooks/useProfileSpecsForServices';
import {
  getAimClusterProfilesByAimIds,
  getProjectAimProfilesByAimIds,
} from '@/lib/app/aims';
import type {
  AIMClusterProfile,
  AIMProfile,
  AIMProfileSpec,
} from '@/types/aims';

vi.mock('@/lib/app/aims', () => ({
  getAimClusterProfilesByAimIds: vi.fn(),
  getProjectAimProfilesByAimIds: vi.fn(),
}));

const wrapper =
  (client: QueryClient) =>
  ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );

const newClient = () =>
  new QueryClient({ defaultOptions: { queries: { retryDelay: 0 } } });

const buildClusterProfile = (
  name: string,
  spec: Partial<AIMProfileSpec> = {},
): AIMClusterProfile =>
  ({
    metadata: { name, labels: {} },
    spec: spec as AIMProfileSpec,
    status: { status: 'Ready' },
  }) as AIMClusterProfile;

const buildNamespaceProfile = (
  name: string,
  spec: Partial<AIMProfileSpec> = {},
): AIMProfile =>
  ({
    metadata: { name, labels: {} },
    spec: spec as AIMProfileSpec,
    status: { status: 'Ready' },
  }) as AIMProfile;

describe('useProfileSpecsForServices', () => {
  it('does not fetch when aimIds is empty', async () => {
    const client = newClient();
    const { result } = renderHook(
      () => useProfileSpecsForServices({ aimIds: [], project: 'p1' }),
      { wrapper: wrapper(client) },
    );
    // Both queries self-gate on `aimIds.length > 0`; neither fetcher should
    // fire and the returned map must be empty.
    expect(getAimClusterProfilesByAimIds).not.toHaveBeenCalled();
    expect(getProjectAimProfilesByAimIds).not.toHaveBeenCalled();
    expect(result.current.specByName.size).toBe(0);
  });

  it('lets namespace profiles override cluster profiles on name collision', async () => {
    const clusterSpec = {
      modelName: 'm',
      precision: 'fp16',
    } as AIMProfileSpec;
    const namespaceSpec = {
      modelName: 'm',
      precision: 'bf16',
    } as AIMProfileSpec;
    vi.mocked(getAimClusterProfilesByAimIds).mockResolvedValue([
      buildClusterProfile('profile-x', clusterSpec),
    ]);
    vi.mocked(getProjectAimProfilesByAimIds).mockResolvedValue([
      buildNamespaceProfile('profile-x', namespaceSpec),
    ]);

    const client = newClient();
    const { result } = renderHook(
      () => useProfileSpecsForServices({ aimIds: ['a1'], project: 'p1' }),
      { wrapper: wrapper(client) },
    );

    await waitFor(() => {
      expect(result.current.specByName.size).toBe(1);
    });
    // Merge order in the hook is cluster first, then namespace — so a
    // colliding name must end up with the namespace spec.
    expect(result.current.specByName.get('profile-x')).toEqual(namespaceSpec);
  });

  it('skips the namespace fetcher when project is null', async () => {
    vi.mocked(getAimClusterProfilesByAimIds).mockResolvedValue([]);
    vi.mocked(getProjectAimProfilesByAimIds).mockResolvedValue([]);

    const client = newClient();
    renderHook(
      () => useProfileSpecsForServices({ aimIds: ['a1'], project: null }),
      { wrapper: wrapper(client) },
    );

    await waitFor(() => {
      expect(getAimClusterProfilesByAimIds).toHaveBeenCalledTimes(1);
    });
    expect(getAimClusterProfilesByAimIds).toHaveBeenCalledWith(['a1']);
    expect(getProjectAimProfilesByAimIds).not.toHaveBeenCalled();
  });
});
