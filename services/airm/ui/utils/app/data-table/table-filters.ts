// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { FilterParams } from '@/types/data-table/server-collection';
import {
  ClientSideDataFilter,
  FilterFieldMapping,
  FilterValueMap,
  ServerSideFilterOperatorMap,
} from '@/types/filters';

import { searchPatternInValue } from '../strings';

import { get } from 'lodash';

/**
 * Converts a map of filter values and corresponding operators into an array of server-side filter parameters.
 *
 * @template T - The type representing the fields available for filtering.
 * @param values - A partial map of filter field names to their filter values.
 * @param operators - A map of filter field names to their corresponding server-side filter operators.
 * @returns An array of filter parameter objects, each containing the field, operator, and values for server-side filtering.
 */
export const convertToServerSideFilterParams = <T>(
  values: Partial<FilterValueMap>,
  operators: ServerSideFilterOperatorMap,
  serverSideFieldMapping?: Partial<Record<string, (keyof T)[]>>,
): FilterParams<T>[] => {
  return Object.entries(values).map(([k, v]) => ({
    fields: serverSideFieldMapping?.[k] ?? [k as keyof T],
    operator: operators[k as keyof typeof operators],
    values: v ?? [],
  }));
};

/**
 * Filters an array of data objects based on provided filter conditions.
 *
 * Each filter condition can specify a field, composite fields, and values to match.
 * Supports exact matching and nested property access via paths.
 *
 * @template T - The type of the data objects in the array.
 * @param data - The array of data objects to filter.
 * @param filters - Optional array of filter conditions to apply.
 * @returns A filtered array of data objects that match all filter conditions.
 */
export const getFilteredData = <T>(
  data: T[],
  filters?: ClientSideDataFilter<T>[],
): T[] => {
  if (!data) return [];
  if (!filters) return data;

  return data.filter((item) => {
    return filters.every((filterCondition) => {
      const { values, field, compositeFields, showAllWhenEmpty } =
        filterCondition;
      if (values.length === 0) {
        if (showAllWhenEmpty) return true;
        return false;
      }

      // Helper to check if a value matches any of the filter values
      const matches = (val: unknown) =>
        values.some((search) => searchPatternInValue(val, search as string));

      if (field) {
        if ('path' in filterCondition && filterCondition.path) {
          const value = get(item[field], filterCondition.path as string);
          if (filterCondition.exact) {
            return values.some((search) => value === search);
          }
          return matches(value);
        }
        if (filterCondition.exact) {
          return values.some((search) => item[field] === search);
        }
        return matches(item[field]);
      } else if (compositeFields) {
        return compositeFields.some((f) => {
          let value;
          if ('path' in f && f.path) {
            value = get(item[f.field], f.path as string);
          } else {
            value = item[f.field];
          }
          return matches(value);
        });
      }
      return true;
    });
  });
};

/**
 * Returns an object containing the default filter values for the provided filter field mapping.
 *
 * Iterates over each filter in the mapping and, if the filter has default selected values,
 * adds them to the result object as strings keyed by the filter name.
 *
 * @param filters - The mapping of filter fields to their configurations.
 * @returns An object mapping filter keys to their default selected values as strings.
 */
export const getDefaultFilterValues = (
  filters: FilterFieldMapping,
): Partial<FilterValueMap> => {
  const initial: Partial<FilterValueMap> = {};

  Object.entries(filters).forEach(([key, filter]) => {
    if (
      filter.defaultSelectedValues &&
      filter.defaultSelectedValues.length > 0
    ) {
      initial[key] = filter.defaultSelectedValues.map(String);
    }
  });

  return initial;
};
