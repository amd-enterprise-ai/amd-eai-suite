// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { QueryClient } from '@tanstack/react-query';
import { vi } from 'vitest';

// Shared spy that records every `invalidateQueries` call routed through a
// proxy created by `wrapQueryClientWithInvalidateSpy`. Each consuming test
// file imports its own copy of this module (Vitest's per-file module graph),
// so the spy is effectively file-scoped — reset it in `beforeEach`.
export const invalidateQueriesSpy = vi.fn();

/**
 * Wrap a real `QueryClient` so that calls to `invalidateQueries` are
 * recorded on `invalidateQueriesSpy` AND forwarded to the underlying
 * client. Every other method and property is exposed unchanged.
 *
 * Why a Proxy rather than a bare stub: keeping the real `invalidateQueries`
 * running means cached queries actually re-fetch in the test environment.
 * That avoids the unrealistic state where assertions pass against a half-
 * mocked cache while production code paths silently diverge.
 */
export const wrapQueryClientWithInvalidateSpy = (
  real: QueryClient,
): QueryClient =>
  new Proxy(real, {
    get(target, prop, receiver) {
      if (prop === 'invalidateQueries') {
        return (...args: Parameters<QueryClient['invalidateQueries']>) => {
          invalidateQueriesSpy(...args);
          return target.invalidateQueries(...args);
        };
      }
      const value = Reflect.get(target, prop, receiver);
      return typeof value === 'function' ? value.bind(target) : value;
    },
  }) as QueryClient;
