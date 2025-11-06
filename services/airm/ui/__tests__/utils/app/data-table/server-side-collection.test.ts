// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { buildQueryParams } from '@/utils/app/data-table/server-side-collection';

import { FilterParams, SortParams } from '@/types/data-table/server-collection';
import {
  FilterOperator,
  ServerSideSortDirection,
} from '@/types/enums/server-collection';
import { SortDirection } from '@/types/enums/sort-direction';

import { describe, expect, it } from 'vitest';

type TestType = { name: string; age: number };

describe('buildQueryParams', () => {
  it('should include page and page_size params', () => {
    const result = buildQueryParams<TestType>(2, 25);
    expect(result).toBe('page=2&page_size=25');
  });

  it('should include filter param when filter is provided', () => {
    const filter: FilterParams<TestType>[] = [
      { fields: ['name'], values: ['John'], operator: FilterOperator.EQ },
    ];
    const result = buildQueryParams<TestType>(1, 10, filter, undefined);
    expect(result).toContain('filter=');
    const params = new URLSearchParams(result);
    expect(params.get('filter')).toBe(JSON.stringify(filter));
  });

  it('should include sort param with mapped directions', () => {
    const sort: SortParams<TestType>[] = [
      { field: 'age', direction: SortDirection.ASC },
      { field: 'name', direction: SortDirection.DESC },
    ];
    const result = buildQueryParams<TestType>(1, 10, undefined, sort);
    expect(result).toContain('sort=');
    const params = new URLSearchParams(result);
    const parsedSort = JSON.parse(params.get('sort')!);
    expect(parsedSort[0].field).toBe('age');
    expect(parsedSort[1].field).toBe('name');
    expect(parsedSort[0].direction).toBe(ServerSideSortDirection.ASC);
    expect(parsedSort[1].direction).toBe(ServerSideSortDirection.DESC);
  });

  it('should include both filter and sort params', () => {
    const filter: FilterParams<TestType>[] = [
      { fields: ['name'], values: ['Alice'], operator: FilterOperator.EQ },
    ];
    const sort: SortParams<TestType>[] = [
      { field: 'age', direction: SortDirection.DESC },
    ];
    const result = buildQueryParams<TestType>(3, 5, filter, sort);
    const params = new URLSearchParams(result);
    expect(params.get('page')).toBe('3');
    expect(params.get('page_size')).toBe('5');
    expect(params.get('filter')).toBe(JSON.stringify(filter));
    const parsedSort = JSON.parse(params.get('sort')!);
    expect(parsedSort[0].direction).toBe(ServerSideSortDirection.DESC);
  });
});
