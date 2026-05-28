// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { notifyManager } from '@tanstack/query-core';
import { QueryClient, QueryKey, useQueryClient } from '@tanstack/react-query';
import { useCallback, useSyncExternalStore } from 'react';

function maxDataUpdatedAtMs(client: QueryClient, prefix: QueryKey): number {
  const queries = client.getQueryCache().findAll({ queryKey: prefix });
  return queries.reduce((max, q) => Math.max(max, q.state.dataUpdatedAt), 0);
}

/**
 * Latest `dataUpdatedAt` among queries matching `prefix`, or `undefined` if none.
 * Subscribes via `useSyncExternalStore` and `notifyManager.batchCalls` (same pattern as `useIsFetching`).
 * @see https://github.com/TanStack/query/blob/main/packages/react-query/src/useIsFetching.ts
 */
export const useLastQueryUpdated = (
  prefix: QueryKey,
  queryClient?: QueryClient,
) => {
  const client = useQueryClient(queryClient);
  const queryCache = client.getQueryCache();

  const subscribe = useCallback(
    (onStoreChange: () => void) =>
      queryCache.subscribe(notifyManager.batchCalls(onStoreChange)),
    [queryCache],
  );

  const getSnapshot = useCallback(
    () => maxDataUpdatedAtMs(client, prefix),
    [client, prefix],
  );

  const maxMs = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  return maxMs === 0 ? undefined : new Date(maxMs);
};

export default useLastQueryUpdated;
