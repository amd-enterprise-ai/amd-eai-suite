// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useQueries } from '@tanstack/react-query';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import { getInferenceModel } from '@/lib/app/inference';
import { AIMClusterModel } from '@/types/aims';

const FIVE_MINUTES_MS = 5 * 60_000;

export interface UseInferenceModelsByNameResult {
  /** Map of resource name -> AIMClusterModel for the names that resolved successfully. */
  byName: Map<string, AIMClusterModel>;
  /**
   * True while any underlying per-name query is performing its initial fetch
   * (no cached data yet). Stays false during background refetches so consumers
   * can gate full-table spinners on initial load only; track `isFetching`
   * separately if you need to show a subtle refresh indicator.
   */
  isLoading: boolean;
  /**
   * True while any underlying per-name query is fetching, including background
   * refetches after `invalidateQueries(['inferenceModel'])`. Use this to gate
   * refresh indicators that should reflect per-name refetches; use `isLoading`
   * for initial-load spinners.
   */
  isFetching: boolean;
  /** True when any underlying per-name query failed (e.g., 404 for an unknown name). */
  isError: boolean;
}

/**
 * Fetches AIM cluster models one-by-one by resource name and combines them into a single map.
 *
 * Replaces the previous "load entire catalog and pick what we need" pattern used by surfaces that
 * only need cluster-catalog data for a small set of deployed models. Each name is cached under
 * `['inferenceModel', name]` for 5 minutes so adjacent components / pages share the response.
 *
 * Names are de-duplicated before issuing requests, and empty / falsy values are dropped.
 *
 * @param {string[]} names - Resource names of cluster-scoped AIMClusterModels to fetch.
 * @returns {UseInferenceModelsByNameResult} Combined byName map + aggregated loading/error flags.
 */
export const useInferenceModelsByName = (
  names: string[],
): UseInferenceModelsByNameResult => {
  const uniqueNames = Array.from(new Set(names.filter(Boolean)));
  return useQueries({
    queries: uniqueNames.map((name) => ({
      queryKey: ['inferenceModel', name] as const,
      queryFn: () => getInferenceModel(name),
      staleTime: FIVE_MINUTES_MS,
      refetchOnWindowFocus: false,
      // 404 means the model name was renamed or removed from the cluster
      // catalog — retrying is pure waste. Other failures (network, 5xx) get
      // the standard 3-retry backoff used elsewhere in the codebase.
      retry: (failureCount: number, error: unknown) => {
        if (error instanceof APIRequestError && error.statusCode === 404) {
          return false;
        }
        return failureCount < 3;
      },
    })),
    combine: (results): UseInferenceModelsByNameResult => {
      const byName = new Map<string, AIMClusterModel>();
      results.forEach((r, i) => {
        if (r.data) {
          byName.set(uniqueNames[i], r.data);
        }
      });
      return {
        byName,
        isLoading: results.some((r) => r.isLoading),
        isFetching: results.some((r) => r.isFetching),
        isError: results.some((r) => r.isError),
      };
    },
  });
};
