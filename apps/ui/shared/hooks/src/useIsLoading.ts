// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QueryKey, useIsFetching } from '@tanstack/react-query';

export function useIsLoading(prefix: QueryKey): boolean {
  return (
    useIsFetching({
      predicate: (query) =>
        query.state.status === 'pending' &&
        query.state.fetchStatus === 'fetching',
      queryKey: prefix,
    }) > 0
  );
}
