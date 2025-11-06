// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { FilterParams, SortParams } from '@/types/data-table/server-collection';
import { ServerSideSortDirection } from '@/types/enums/server-collection';
import { SortDirection } from '@/types/enums/sort-direction';

export const buildQueryParams = <T>(
  page: number = 1,
  pageSize: number = 10,
  filter?: FilterParams<T>[] | undefined,
  sort?: SortParams<T>[] | undefined,
): string => {
  const availableParams: { [key: string]: string } = {
    page: page.toString(),
    page_size: pageSize.toString(),
  };

  if (sort) {
    const mappedSort = sort.map((s) => ({
      ...s,
      direction:
        s.direction === SortDirection.ASC
          ? ServerSideSortDirection.ASC
          : ServerSideSortDirection.DESC,
    }));
    availableParams.sort = JSON.stringify(mappedSort);
  }

  if (filter) {
    availableParams.filter = JSON.stringify(filter);
  }

  const params = new URLSearchParams(availableParams);
  return params.toString();
};
