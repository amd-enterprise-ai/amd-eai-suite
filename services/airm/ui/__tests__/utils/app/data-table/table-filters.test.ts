// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getFilteredData } from '@/utils/app/data-table/table-filters';
import { convertToServerSideFilterParams } from '@/utils/app/data-table/table-filters';

import { FilterOperator } from '@/types/enums/server-collection';

import { describe, expect, it } from 'vitest';

type TestData = {
  id: number;
  name: string;
  description?: string;
  info?: {
    city?: string;
    age?: number;
  };
};

describe('getFilteredData', () => {
  const data: TestData[] = [
    { id: 1, name: 'Alice', info: { city: 'London', age: 30 } },
    { id: 2, name: 'Bob', info: { city: 'Paris', age: 25 } },
    { id: 3, name: 'Charlie', info: { city: 'London', age: 35 } },
    { id: 4, name: 'David', info: { city: 'Berlin', age: 40 } },
  ];

  it('returns all data if no filters are provided', () => {
    expect(getFilteredData(data)).toEqual(data);
    expect(getFilteredData(data, [])).toEqual(data);
  });

  it('filters by simple field (partial match)', () => {
    const filters = [{ field: 'name', values: ['ali'] }];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([data[0]]);
  });

  it('filters by simple field (exact match)', () => {
    const filters = [{ field: 'name', values: ['Bob'], exact: true }];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([data[1]]);
  });

  it('filters by nested field using path', () => {
    const filters = [{ field: 'info', path: 'city', values: ['london'] }];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([data[0], data[2]]);
  });

  it('filters by nested field using path (exact match)', () => {
    const filters = [
      { field: 'info', path: 'city', values: ['Paris'], exact: true },
    ];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([data[1]]);
  });

  it('filters by compositeFields (partial match)', () => {
    const filters = [
      {
        compositeFields: [{ field: 'name' }, { field: 'info', path: 'city' }],
        values: ['berlin'],
      },
    ];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([data[3]]);
  });

  it('filters by compositeFields (matches any field)', () => {
    const filters = [
      {
        compositeFields: [{ field: 'name' }, { field: 'info', path: 'city' }],
        values: ['charlie'],
      },
    ];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([data[2]]);
  });

  it('returns no data if filter values are empty', () => {
    const filters = [{ field: 'name', values: [] }];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([]);
  });

  it('returns all data if filter values are empty is showAllWhenEmpty is set', () => {
    const filters = [{ field: 'name', values: [], showAllWhenEmpty: true }];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual(data);
  });

  it('applies multiple filters (AND logic)', () => {
    const filters = [
      { field: 'info', path: 'city', values: ['london'] },
      { field: 'info', path: 'age', values: ['3'] }, // matches 30 and 35
    ];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([data[0], data[2]]);
  });

  it('returns empty array if no items match', () => {
    const filters = [{ field: 'name', values: ['Zoe'] }];
    const result = getFilteredData(data, filters as any);
    expect(result).toEqual([]);
  });

  describe('convertToServerSideFilterParams', () => {
    it('converts values and operators to FilterParams', () => {
      const values = { name: ['Alice'], age: ['30'] };
      const operators = {
        name: FilterOperator.CONTAINS,
        age: FilterOperator.EQ,
      };
      const result = convertToServerSideFilterParams<TestData>(
        values,
        operators,
      );
      expect(result).toEqual([
        {
          fields: ['name'],
          operator: FilterOperator.CONTAINS,
          values: ['Alice'],
        },
        { fields: ['age'], operator: FilterOperator.EQ, values: ['30'] },
      ]);
    });

    it('converts values and operators to FilterParams with serverSideFieldMapping', () => {
      const values = { name: ['Alice'], age: ['30'] };
      const operators = {
        name: FilterOperator.CONTAINS,
        age: FilterOperator.EQ,
      };
      const serverSideFieldMapping: Partial<
        Record<string, (keyof TestData)[]>
      > = {
        name: ['name', 'description'],
        age: ['id'],
      };
      const result = convertToServerSideFilterParams<TestData>(
        values,
        operators,
        serverSideFieldMapping,
      );
      expect(result).toEqual([
        {
          fields: ['name', 'description'],
          operator: FilterOperator.CONTAINS,
          values: ['Alice'],
        },
        { fields: ['id'], operator: FilterOperator.EQ, values: ['30'] },
      ]);
    });

    it('handles missing values as empty array', () => {
      const values = { name: undefined, age: ['25'] };
      const operators = {
        name: FilterOperator.CONTAINS,
        age: FilterOperator.EQ,
      };
      const result = convertToServerSideFilterParams<TestData>(
        values,
        operators,
      );
      expect(result).toEqual([
        { fields: ['name'], operator: FilterOperator.CONTAINS, values: [] },
        { fields: ['age'], operator: FilterOperator.EQ, values: ['25'] },
      ]);
    });

    it('returns empty array if values is empty', () => {
      const values = {};
      const operators = {};
      const result = convertToServerSideFilterParams<TestData>(
        values,
        operators,
      );
      expect(result).toEqual([]);
    });

    it('handles extra keys in operators gracefully', () => {
      const values = { id: ['1'] };
      const operators = {
        id: FilterOperator.EQ,
      };
      const result = convertToServerSideFilterParams<TestData>(
        values,
        operators,
      );
      expect(result).toEqual([
        { fields: ['id'], operator: FilterOperator.EQ, values: ['1'] },
      ]);
    });
  });
});
